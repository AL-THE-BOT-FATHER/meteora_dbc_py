from solana.rpc.api import Client
from solders.keypair import Keypair  # type: ignore

from pool_utils import fetch_pool_from_rpc
from meteora_dbc import buy

# Configuration
priv_key = "base58_priv_str_here"
rpc = "rpc_url_here"
mint_str = "meteora_dbc_address"
sol_in = 0.01
unit_budget = 100_000
unit_price = 1_000_000

# Initialize client and keypair
client = Client(rpc)
payer_keypair = Keypair.from_base58_string(priv_key)

# Fetch pool and execute buy
pool_str = fetch_pool_from_rpc(client, mint_str)

if pool_str:
    buy(client, payer_keypair, pool_str, sol_in, unit_budget, unit_price)
else:
    print("No pool address found...")

