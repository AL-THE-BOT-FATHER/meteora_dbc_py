from dataclasses import dataclass
from typing import List
from construct import Container, Struct, Int8ul, Int16ul, Int32ul, Int64ul, Array, Bytes, Padding
from construct.core import Construct
from solders.pubkey import Pubkey #type: ignore

class Int128ul(Construct):
    def _parse(self, stream, context, path):
        data = stream.read(16)
        return int.from_bytes(data, byteorder="little")
    def _build(self, obj, stream, context, path):
        stream.write(obj.to_bytes(16, byteorder="little"))
        return obj
    def _sizeof(self, context, path):
        return 16

BASE_FEE_CONFIG_LAYOUT = Struct(
    "cliff_fee_numerator" / Int64ul,
    "second_factor"       / Int64ul,
    "third_factor"        / Int64ul,
    "first_factor"        / Int16ul,
    "base_fee_mode"       / Int8ul,
    "padding_0"           / Array(5, Int8ul),
)

DYNAMIC_FEE_CONFIG_LAYOUT = Struct(
    "initialized"              / Int8ul,
    "padding"                  / Array(7, Int8ul),
    "max_volatility_accumulator"/ Int32ul,
    "variable_fee_control"     / Int32ul,
    "bin_step"                 / Int16ul,
    "filter_period"            / Int16ul,
    "decay_period"             / Int16ul,
    "reduction_factor"         / Int16ul,
    "padding2"                 / Array(8, Int8ul),
    "bin_step_u128"            / Int128ul(),
)

POOL_FEES_CONFIG_LAYOUT = Struct(
    "base_fee"             / BASE_FEE_CONFIG_LAYOUT,
    "dynamic_fee"          / DYNAMIC_FEE_CONFIG_LAYOUT,
    "padding_0"            / Array(5, Int64ul),
    "padding_1"            / Array(6, Int8ul),
    "protocol_fee_percent" / Int8ul,
    "referral_fee_percent" / Int8ul,
)

LOCKED_VESTING_CONFIG_LAYOUT = Struct(
    "amount_per_period"                  / Int64ul,
    "cliff_duration_from_migration_time" / Int64ul,
    "frequency"                         / Int64ul,
    "number_of_period"                  / Int64ul,
    "cliff_unlock_amount"               / Int64ul,
    "_padding"                          / Int64ul,
)

LIQUIDITY_DISTRIBUTION_CONFIG_LAYOUT = Struct(
    "sqrt_price" / Int128ul(),
    "liquidity"  / Int128ul(),
)

POOL_CONFIG_LAYOUT = Struct(
    Padding(8),
    "quote_mint"                    / Bytes(32),
    "fee_claimer"                   / Bytes(32),
    "leftover_receiver"             / Bytes(32),
    "pool_fees"                     / POOL_FEES_CONFIG_LAYOUT,
    "collect_fee_mode"              / Int8ul,
    "migration_option"              / Int8ul,
    "activation_type"               / Int8ul,
    "token_decimal"                 / Int8ul,
    "version"                       / Int8ul,
    "token_type"                    / Int8ul,
    "quote_token_flag"              / Int8ul,
    "partner_locked_lp_percentage"  / Int8ul,
    "partner_lp_percentage"         / Int8ul,
    "creator_locked_lp_percentage"  / Int8ul,
    "creator_lp_percentage"         / Int8ul,
    "migration_fee_option"          / Int8ul,
    "fixed_token_supply_flag"       / Int8ul,
    "creator_trading_fee_percentage"/ Int8ul,
    "token_update_authority"        / Int8ul,
    "migration_fee_percentage"      / Int8ul,
    "creator_migration_fee_percentage"/ Int8ul,
    "_padding_1"                    / Array(7, Int8ul),
    "swap_base_amount"              / Int64ul,
    "migration_quote_threshold"     / Int64ul,
    "migration_base_threshold"      / Int64ul,
    "migration_sqrt_price"          / Int128ul(),
    "locked_vesting_config"         / LOCKED_VESTING_CONFIG_LAYOUT,
    "pre_migration_token_supply"    / Int64ul,
    "post_migration_token_supply"   / Int64ul,
    "_padding_2"                    / Array(2, Int128ul()),
    "sqrt_start_price"              / Int128ul(),
    "curve"                         / Array(20, LIQUIDITY_DISTRIBUTION_CONFIG_LAYOUT),
)

@dataclass
class BaseFeeConfig:
    cliff_fee_numerator: int
    second_factor: int
    third_factor: int
    first_factor: int
    base_fee_mode: int

@dataclass
class DynamicFeeConfig:
    initialized: int
    max_volatility_accumulator: int
    variable_fee_control: int
    bin_step: int
    filter_period: int
    decay_period: int
    reduction_factor: int
    bin_step_u128: int

@dataclass
class PoolFeesConfig:
    base_fee: BaseFeeConfig
    dynamic_fee: DynamicFeeConfig
    protocol_fee_percent: int
    referral_fee_percent: int

@dataclass
class LockedVestingConfig:
    amount_per_period: int
    cliff_duration_from_migration_time: int
    frequency: int
    number_of_period: int
    cliff_unlock_amount: int

@dataclass
class LiquidityDistributionConfig:
    sqrt_price: int
    liquidity: int

@dataclass
class PoolConfig:
    quote_mint: Pubkey
    fee_claimer: Pubkey
    leftover_receiver: Pubkey
    pool_fees: PoolFeesConfig
    collect_fee_mode: int
    migration_option: int
    activation_type: int
    token_decimal: int
    version: int
    token_type: int
    quote_token_flag: int
    partner_locked_lp_percentage: int
    partner_lp_percentage: int
    creator_locked_lp_percentage: int
    creator_lp_percentage: int
    migration_fee_option: int
    fixed_token_supply_flag: int
    creator_trading_fee_percentage: int
    token_update_authority: int
    migration_fee_percentage: int
    creator_migration_fee_percentage: int
    swap_base_amount: int
    migration_quote_threshold: int
    migration_base_threshold: int
    migration_sqrt_price: int
    locked_vesting_config: LockedVestingConfig
    pre_migration_token_supply: int
    post_migration_token_supply: int
    sqrt_start_price: int
    curve: List[LiquidityDistributionConfig]

def parse_pool_config(c: Container) -> PoolConfig:
    return PoolConfig(
        quote_mint=Pubkey.from_bytes(c.quote_mint),
        fee_claimer=Pubkey.from_bytes(c.fee_claimer),
        leftover_receiver=Pubkey.from_bytes(c.leftover_receiver),
        pool_fees=PoolFeesConfig(
            base_fee=BaseFeeConfig(
                cliff_fee_numerator=c.pool_fees.base_fee.cliff_fee_numerator,
                second_factor=c.pool_fees.base_fee.second_factor,
                third_factor=c.pool_fees.base_fee.third_factor,
                first_factor=c.pool_fees.base_fee.first_factor,
                base_fee_mode=c.pool_fees.base_fee.base_fee_mode,
            ),
            dynamic_fee=DynamicFeeConfig(
                initialized=c.pool_fees.dynamic_fee.initialized,
                max_volatility_accumulator=c.pool_fees.dynamic_fee.max_volatility_accumulator,
                variable_fee_control=c.pool_fees.dynamic_fee.variable_fee_control,
                bin_step=c.pool_fees.dynamic_fee.bin_step,
                filter_period=c.pool_fees.dynamic_fee.filter_period,
                decay_period=c.pool_fees.dynamic_fee.decay_period,
                reduction_factor=c.pool_fees.dynamic_fee.reduction_factor,
                bin_step_u128=c.pool_fees.dynamic_fee.bin_step_u128,
            ),
            protocol_fee_percent=c.pool_fees.protocol_fee_percent,
            referral_fee_percent=c.pool_fees.referral_fee_percent,
        ),
        collect_fee_mode=c.collect_fee_mode,
        migration_option=c.migration_option,
        activation_type=c.activation_type,
        token_decimal=c.token_decimal,
        version=c.version,
        token_type=c.token_type,
        quote_token_flag=c.quote_token_flag,
        partner_locked_lp_percentage=c.partner_locked_lp_percentage,
        partner_lp_percentage=c.partner_lp_percentage,
        creator_locked_lp_percentage=c.creator_locked_lp_percentage,
        creator_lp_percentage=c.creator_lp_percentage,
        migration_fee_option=c.migration_fee_option,
        fixed_token_supply_flag=c.fixed_token_supply_flag,
        creator_trading_fee_percentage=c.creator_trading_fee_percentage,
        token_update_authority=c.token_update_authority,
        migration_fee_percentage=c.migration_fee_percentage,
        creator_migration_fee_percentage=c.creator_migration_fee_percentage,
        swap_base_amount=c.swap_base_amount,
        migration_quote_threshold=c.migration_quote_threshold,
        migration_base_threshold=c.migration_base_threshold,
        migration_sqrt_price=c.migration_sqrt_price,
        locked_vesting_config=LockedVestingConfig(
            amount_per_period=c.locked_vesting_config.amount_per_period,
            cliff_duration_from_migration_time=c.locked_vesting_config.cliff_duration_from_migration_time,
            frequency=c.locked_vesting_config.frequency,
            number_of_period=c.locked_vesting_config.number_of_period,
            cliff_unlock_amount=c.locked_vesting_config.cliff_unlock_amount,
        ),
        pre_migration_token_supply=c.pre_migration_token_supply,
        post_migration_token_supply=c.post_migration_token_supply,
        sqrt_start_price=c.sqrt_start_price,
        curve=[
            LiquidityDistributionConfig(pt.sqrt_price, pt.liquidity)
            for pt in c.curve
            if pt.sqrt_price != 0
        ],
    )
