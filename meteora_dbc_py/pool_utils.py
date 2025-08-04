from solana.rpc.api import Client
from solders.pubkey import Pubkey  # type: ignore

from solana.rpc.commitment import Processed
from solana.rpc.types import MemcmpOpts

from constants import METEORA_DBC_PROGRAM
from pool_config import POOL_CONFIG_LAYOUT, parse_pool_config
from pool_state import POOL_STATE_LAYOUT, parse_pool_state

def fetch_pool_state(client: Client, pool_str: str):
    pool_pubkey = Pubkey.from_string(pool_str)
    account_info = client.get_account_info_json_parsed(pool_pubkey)
    account_data = account_info.value.data
    decoded_data = POOL_STATE_LAYOUT.parse(account_data)
    pool_state = parse_pool_state(pool_pubkey, decoded_data)
    return pool_state

def fetch_pool_config(client: Client, pool_config: Pubkey):
    account_info = client.get_account_info_json_parsed(pool_config)
    account_data = account_info.value.data
    decoded_data = POOL_CONFIG_LAYOUT.parse(account_data)
    pool_config = parse_pool_config(decoded_data)
    return pool_config

def fetch_pool_from_rpc(client: Client, base_mint: str) -> str | None:
    memcmp_filter_base = MemcmpOpts(offset=136, bytes=base_mint)

    try:
        response = client.get_program_accounts(
            METEORA_DBC_PROGRAM,
            commitment=Processed,
            filters=[memcmp_filter_base],
        )
        accounts = response.value
        if accounts:
            return str(accounts[0].pubkey)
    except:
        return None
    
    return None
