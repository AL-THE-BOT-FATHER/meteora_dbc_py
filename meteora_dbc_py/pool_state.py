from dataclasses import dataclass
from typing import List
from construct import Container, Struct, Int64ul, Int8ul, Array, Bytes, Padding
from construct.core import Construct
from solders.pubkey import Pubkey # type: ignore

class Int128ul(Construct):
    def _parse(self, stream, context, path):
        data = stream.read(16)
        return int.from_bytes(data, byteorder="little")
    def _build(self, obj, stream, context, path):
        stream.write(obj.to_bytes(16, byteorder="little"))
        return obj
    def _sizeof(self, context, path):
        return 16

POOL_STATE_LAYOUT = Struct(
    Padding(8),
    "volatility_tracker" / Struct(
        "last_update_timestamp" / Int64ul,
        "padding" / Array(8, Int8ul),
        "sqrt_price_reference" / Int128ul(),
        "volatility_accumulator" / Int128ul(),
        "volatility_reference" / Int128ul(),
    ),
    "config" / Bytes(32),
    "creator" / Bytes(32),
    "base_mint" / Bytes(32),
    "base_vault" / Bytes(32),
    "quote_vault" / Bytes(32),
    "base_reserve" / Int64ul,
    "quote_reserve" / Int64ul,
    "protocol_base_fee" / Int64ul,
    "protocol_quote_fee" / Int64ul,
    "partner_base_fee" / Int64ul,
    "partner_quote_fee" / Int64ul,
    "sqrt_price" / Int128ul(),
    "activation_point" / Int64ul,
    "pool_type" / Int8ul,
    "is_migrated" / Int8ul,
    "is_partner_withdraw_surplus" / Int8ul,
    "is_protocol_withdraw_surplus" / Int8ul,
    "migration_progress" / Int8ul,
    "is_withdraw_leftover" / Int8ul,
    "is_creator_withdraw_surplus" / Int8ul,
    "migration_fee_withdraw_status" / Int8ul,
    "metrics" / Struct(
        "total_protocol_base_fee" / Int64ul,
        "total_protocol_quote_fee" / Int64ul,
        "total_trading_base_fee" / Int64ul,
        "total_trading_quote_fee" / Int64ul,
    ),
    "finish_curve_timestamp" / Int64ul,
    "creator_base_fee" / Int64ul,
    "creator_quote_fee" / Int64ul,
    "_padding_1" / Array(7, Int64ul),
)


@dataclass
class VolatilityTracker:
    last_update_timestamp: int
    sqrt_price_reference: int
    volatility_accumulator: int
    volatility_reference: int


@dataclass
class PoolMetrics:
    total_protocol_base_fee: int
    total_protocol_quote_fee: int
    total_trading_base_fee: int
    total_trading_quote_fee: int


@dataclass
class PoolState:
    pool: Pubkey
    volatility_tracker: VolatilityTracker
    config: Pubkey
    creator: Pubkey
    base_mint: Pubkey
    base_vault: Pubkey
    quote_vault: Pubkey
    base_reserve: int
    quote_reserve: int
    protocol_base_fee: int
    protocol_quote_fee: int
    partner_base_fee: int
    partner_quote_fee: int
    sqrt_price: int
    activation_point: int
    pool_type: int
    is_migrated: int
    is_partner_withdraw_surplus: int
    is_protocol_withdraw_surplus: int
    migration_progress: int
    is_withdraw_leftover: int
    is_creator_withdraw_surplus: int
    migration_fee_withdraw_status: int
    metrics: PoolMetrics
    finish_curve_timestamp: int
    creator_base_fee: int
    creator_quote_fee: int
    _padding_1: List[int]

def parse_pool_state(pool_pubkey: Pubkey, c: Container) -> PoolState:
    return PoolState(
        pool=pool_pubkey,
        volatility_tracker=VolatilityTracker(
            last_update_timestamp=c.volatility_tracker.last_update_timestamp,
            sqrt_price_reference=c.volatility_tracker.sqrt_price_reference,
            volatility_accumulator= c.volatility_tracker.volatility_accumulator,
            volatility_reference=c.volatility_tracker.volatility_reference
        ),
        config=Pubkey.from_bytes(c.config),
        creator=Pubkey.from_bytes(c.creator),
        base_mint=Pubkey.from_bytes(c.base_mint),
        base_vault=Pubkey.from_bytes(c.base_vault),
        quote_vault=Pubkey.from_bytes(c.quote_vault),
        base_reserve=c.base_reserve,
        quote_reserve=c.quote_reserve,
        protocol_base_fee=c.protocol_base_fee,
        protocol_quote_fee=c.protocol_quote_fee,
        partner_base_fee=c.partner_base_fee,
        partner_quote_fee=c.partner_quote_fee,
        sqrt_price=c.sqrt_price,
        activation_point=c.activation_point,
        pool_type=c.pool_type,
        is_migrated=c.is_migrated,
        is_partner_withdraw_surplus=c.is_partner_withdraw_surplus,
        is_protocol_withdraw_surplus=c.is_protocol_withdraw_surplus,
        migration_progress=c.migration_progress,
        is_withdraw_leftover=c.is_withdraw_leftover,
        is_creator_withdraw_surplus=c.is_creator_withdraw_surplus,
        migration_fee_withdraw_status=c.migration_fee_withdraw_status,
        metrics=PoolMetrics(
            total_protocol_base_fee=c.metrics.total_protocol_base_fee,
            total_protocol_quote_fee=c.metrics.total_protocol_quote_fee,
            total_trading_base_fee=c.metrics.total_trading_base_fee,
            total_trading_quote_fee=c.metrics.total_trading_quote_fee,
        ),
        finish_curve_timestamp=c.finish_curve_timestamp,
        creator_base_fee=c.creator_base_fee,
        creator_quote_fee=c.creator_quote_fee,
        _padding_1=list(c._padding_1),
    )