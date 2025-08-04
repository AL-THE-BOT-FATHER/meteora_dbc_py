import base64
import os
import struct

from solana.rpc.api import Client
from solana.rpc.commitment import Processed
from solana.rpc.types import TokenAccountOpts, TxOpts

from spl.token.client import Token
from spl.token.instructions import (
    CloseAccountParams,
    InitializeAccountParams,
    close_account,
    create_associated_token_account,
    get_associated_token_address,
    initialize_account,
)

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore
from solders.instruction import AccountMeta, Instruction  # type: ignore
from solders.keypair import Keypair  # type: ignore
from solders.message import MessageV0  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.system_program import CreateAccountWithSeedParams, create_account_with_seed  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore

from common_utils import confirm_txn, get_token_balance
from constants import *
from pool_config import PoolConfig
from pool_state import PoolState
from pool_utils import fetch_pool_config, fetch_pool_state
from swap_estimate import swap_base_to_quote, swap_quote_to_base


def buy(
    client: Client,
    payer_keypair: Keypair,
    pool_str: str,
    quote_in: float = 0.1,
    slippage: int = 5, 
    unit_budget: int = 100_000,
    unit_price: int = 1_000_000,
) -> bool:
    try:
        print(f"Starting buy transaction for pool: {pool_str}")

        print("Fetching pool state...")
        pool_state: PoolState = fetch_pool_state(client, pool_str)
        print("Fetching pool config...")
        pool_config: PoolConfig = fetch_pool_config(client, pool_state.config)

        quote_token_decimals = pool_config.token_decimal
        quote_amount_in = int(quote_in * 10 ** quote_token_decimals)
        min_base_amount_out = 0

        curve: list[tuple[int, int]] = [
            (pt.sqrt_price, pt.liquidity)
            for pt in pool_config.curve
            if pt.sqrt_price != 0
        ]
        cliff_fee_num    = pool_config.pool_fees.base_fee.cliff_fee_numerator
        protocol_fee_pct = pool_config.pool_fees.protocol_fee_percent
        referral_fee_pct = pool_config.pool_fees.referral_fee_percent

        estimate = swap_quote_to_base(
            amount_in=quote_amount_in,
            cliff_fee_num=cliff_fee_num,
            protocol_fee_pct=protocol_fee_pct,
            referral_fee_pct=referral_fee_pct,
            cur_sqrt=pool_state.sqrt_price,
            curve=curve
        )

        print(f"Quote→Base estimate: {estimate}")

        print("Checking for existing base token account...")
        base_account_check = client.get_token_accounts_by_owner(
            payer_keypair.pubkey(),
            TokenAccountOpts(pool_state.base_mint),
            Processed,
        )
        if base_account_check.value:
            base_token_account = base_account_check.value[0].pubkey
            base_account_ix = None
            print("Existing base token account found:", base_token_account)
        else:
            base_token_account = get_associated_token_address(
                payer_keypair.pubkey(),
                pool_state.base_mint,
            )
            base_account_ix = create_associated_token_account(
                payer_keypair.pubkey(),
                payer_keypair.pubkey(),
                pool_state.base_mint,
            )
            print("Will create base token ATA:", base_token_account)

        print("Generating seed for quote token account...")
        seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
        quote_token_account = Pubkey.create_with_seed(
            payer_keypair.pubkey(),
            seed,
            TOKEN_PROGRAM_ID,
        )
        quote_rent = Token.get_min_balance_rent_for_exempt_for_account(client)

        print("Creating and initializing quote token account...")
        create_quote_token_account_ix = create_account_with_seed(
            CreateAccountWithSeedParams(
                from_pubkey=payer_keypair.pubkey(),
                to_pubkey=quote_token_account,
                base=payer_keypair.pubkey(),
                seed=seed,
                lamports=int(quote_rent + quote_amount_in),
                space=ACCOUNT_SPACE,
                owner=TOKEN_PROGRAM_ID,
            )
        )
        init_quote_token_account_ix = initialize_account(
            InitializeAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=quote_token_account,
                mint=pool_config.quote_mint,
                owner=payer_keypair.pubkey(),
            )
        )

        print("Creating swap instruction...")
        accounts = [
            AccountMeta(POOL_AUTHORITY, False, False),
            AccountMeta(pool_state.config, False, False),
            AccountMeta(pool_state.pool, False, True),
            AccountMeta(quote_token_account, False, True),
            AccountMeta(base_token_account, False, True),
            AccountMeta(pool_state.base_vault, False, True),
            AccountMeta(pool_state.quote_vault, False, True),
            AccountMeta(pool_state.base_mint, False, False),
            AccountMeta(pool_config.quote_mint, False, False),
            AccountMeta(payer_keypair.pubkey(), True, True),
            AccountMeta(TOKEN_PROGRAM_ID, False, False),
            AccountMeta(TOKEN_PROGRAM_ID, False, False),
            AccountMeta(REFERRAL_TOKEN_ACC, False, False),
            AccountMeta(EVENT_AUTH, False, False),
            AccountMeta(METEORA_DBC_PROGRAM, False, False),
        ]
        data = bytearray.fromhex("f8c69e91e17587c8")
        data.extend(struct.pack("<Q", quote_amount_in))
        data.extend(struct.pack("<Q", min_base_amount_out))
        swap_instr = Instruction(METEORA_DBC_PROGRAM, bytes(data), accounts)

        print("Preparing to close quote token account after swap...")
        close_quote_token_account_ix = close_account(
            CloseAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=quote_token_account,
                dest=payer_keypair.pubkey(),
                owner=payer_keypair.pubkey(),
            )
        )

        instructions = [
            set_compute_unit_limit(unit_budget),
            set_compute_unit_price(unit_price),
            create_quote_token_account_ix,
            init_quote_token_account_ix,
        ]
        if base_account_ix:
            instructions.append(base_account_ix)
        instructions.extend([swap_instr, close_quote_token_account_ix])

        print("Compiling transaction message...")
        compiled_message = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            client.get_latest_blockhash().value.blockhash,
        )
        print("Sending transaction...")
        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [payer_keypair]),
            opts=TxOpts(skip_preflight=False),
        ).value
        print("Transaction Signature:", txn_sig)

        print("Confirming transaction...")
        confirmed = confirm_txn(client, txn_sig)
        print("Transaction confirmed:", confirmed)
        return confirmed

    except Exception as e:
        print("Error occurred during transaction:", e)
        return False

def sell(
    client: Client,
    payer_keypair: Keypair,
    pool_str: str,
    percentage: int = 100,
    slippage: int = 5, 
    unit_budget: int = 100_000,
    unit_price: int = 1_000_000,
) -> bool:
    try:
        print(f"Starting sell transaction for pool: {pool_str}")

        if not (1 <= percentage <= 100):
            print("Percentage must be between 1 and 100.")
            return False

        print("Fetching pool state...")
        pool_state: PoolState = fetch_pool_state(client, pool_str)
        print("Fetching pool config...")
        pool_config: PoolConfig = fetch_pool_config(client, pool_state.config)

        curve: list[tuple[int, int]] = [
            (pt.sqrt_price, pt.liquidity)
            for pt in pool_config.curve
            if pt.sqrt_price != 0
        ]
        cliff_fee_num    = pool_config.pool_fees.base_fee.cliff_fee_numerator
        protocol_fee_pct = pool_config.pool_fees.protocol_fee_percent
        referral_fee_pct = pool_config.pool_fees.referral_fee_percent

        print("Retrieving base token balance...")
        base_balance = get_token_balance(
            client, payer_keypair.pubkey(), pool_state.base_mint
        )
        if not base_balance:
            print("Base token balance is zero. Nothing to sell.")
            return False

        base_amount_in = int(base_balance * (percentage / 100))
        min_quote_amount_out = 0

        estimate = swap_base_to_quote(
            amount_in=base_amount_in,
            cliff_fee_num=cliff_fee_num,
            protocol_fee_pct=protocol_fee_pct,
            referral_fee_pct=referral_fee_pct,
            cur_sqrt=pool_state.sqrt_price,
            curve=curve,
        )
        
        print(f"Base→Quote estimate: {estimate}")

        print("Getting associated base token account address...")
        base_token_account = get_associated_token_address(
            payer_keypair.pubkey(), pool_state.base_mint
        )

        print("Generating seed for quote token account...")
        seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
        quote_token_account = Pubkey.create_with_seed(
            payer_keypair.pubkey(), seed, TOKEN_PROGRAM_ID
        )
        quote_rent = Token.get_min_balance_rent_for_exempt_for_account(client)

        print("Creating and initializing quote token account...")
        create_quote_token_account_ix = create_account_with_seed(
            CreateAccountWithSeedParams(
                from_pubkey=payer_keypair.pubkey(),
                to_pubkey=quote_token_account,
                base=payer_keypair.pubkey(),
                seed=seed,
                lamports=int(quote_rent),
                space=ACCOUNT_SPACE,
                owner=TOKEN_PROGRAM_ID,
            )
        )
        
        init_quote_token_account_ix = initialize_account(
            InitializeAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=quote_token_account,
                mint=pool_config.quote_mint,
                owner=payer_keypair.pubkey(),
            )
        )

        print("Creating swap instruction...")
        accounts = [
            AccountMeta(POOL_AUTHORITY, False, False),
            AccountMeta(pool_state.config, False, False),
            AccountMeta(pool_state.pool, False, True),
            AccountMeta(base_token_account, False, True),
            AccountMeta(quote_token_account, False, True),
            AccountMeta(pool_state.base_vault, False, True),
            AccountMeta(pool_state.quote_vault, False, True),
            AccountMeta(pool_state.base_mint, False, False),
            AccountMeta(pool_config.quote_mint, False, False),
            AccountMeta(payer_keypair.pubkey(), True, True),
            AccountMeta(TOKEN_PROGRAM_ID, False, False),
            AccountMeta(TOKEN_PROGRAM_ID, False, False),
            AccountMeta(REFERRAL_TOKEN_ACC, False, False),
            AccountMeta(EVENT_AUTH, False, False),
            AccountMeta(METEORA_DBC_PROGRAM, False, False),
        ]
        data = bytearray.fromhex("f8c69e91e17587c8")
        data.extend(struct.pack("<Q", base_amount_in))
        data.extend(struct.pack("<Q", min_quote_amount_out))
        swap_ix = Instruction(METEORA_DBC_PROGRAM, bytes(data), accounts)

        print("Preparing to close quote token account after swap...")
        close_quote_token_account_ix = close_account(
            CloseAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=quote_token_account,
                dest=payer_keypair.pubkey(),
                owner=payer_keypair.pubkey(),
            )
        )

        instructions = [
            set_compute_unit_limit(unit_budget),
            set_compute_unit_price(unit_price),
            create_quote_token_account_ix,
            init_quote_token_account_ix,
            swap_ix,
            close_quote_token_account_ix,
        ]

        if percentage == 100:
            print("Preparing to close base token account (100% sell)...")
            close_base_token_account_ix = close_account(
                CloseAccountParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=base_token_account,
                    dest=payer_keypair.pubkey(),
                    owner=payer_keypair.pubkey(),
                )
            )
            instructions.append(close_base_token_account_ix)

        print("Compiling transaction message...")
        blockhash = client.get_latest_blockhash().value.blockhash
        compiled_msg = MessageV0.try_compile(
            payer_keypair.pubkey(),
            instructions,
            [],
            blockhash,
        )
        print("Sending transaction...")
        sig = client.send_transaction(
            txn=VersionedTransaction(compiled_msg, [payer_keypair]),
            opts=TxOpts(skip_preflight=False),
        ).value
        print("Transaction Signature:", sig)

        print("Confirming transaction...")
        confirmed = confirm_txn(client, sig)
        print("Transaction confirmed:", confirmed)
        return confirmed

    except Exception as e:
        print("Error occurred during transaction:", e)
        return False
