RES      = 64        
FEE_DEN  = 10**9     # fee numerator denominator

def ceildiv(a: int, b: int) -> int:
    return -(-a // b)

def _walk_curve(
    amt_in:         int,
    cur_sqrt:       int,
    curve:          list[tuple[int,int]],
    base_for_quote: bool
) -> tuple[int,int]:

    left      = amt_in
    total_out = 0
    sqrt      = cur_sqrt
    shift     = RES * 2

    if base_for_quote:
        # SELL base → quote: walk bins descending
        for lower, liq in reversed(curve):
            if liq == 0 or lower >= sqrt:
                continue
            # max quote in this bin:
            max_q = (liq * (sqrt - lower)) >> shift
            max_b = (liq * (sqrt - lower)) // (sqrt * lower)
            if left < max_b:
                nxt = (liq * sqrt) // (liq + left * sqrt)
                total_out += (liq * (sqrt - nxt)) >> shift
                sqrt       = nxt
                left       = 0
                break
            total_out += max_q
            left       -= max_b
            sqrt        = lower

        # if still left, drain into lowest bin
        if left:
            lower0, liq0 = curve[0]
            nxt = (liq0 * sqrt) // (liq0 + left * sqrt)
            total_out += (liq0 * (sqrt - nxt)) >> shift
            sqrt = nxt

    else:
        # BUY base with quote: walk bins ascending
        for upper, liq in curve:
            if liq == 0 or upper <= sqrt:
                continue
            max_q = (liq * (upper - sqrt)) >> shift
            max_b = (liq * (upper - sqrt)) // (upper * sqrt)
            if left < max_q:
                nxt = sqrt + (left << shift) // liq
                total_out += (liq * (nxt - sqrt)) // (sqrt * nxt)
                sqrt       = nxt
                left       = 0
                break
            total_out += max_b
            left       -= max_q
            sqrt        = upper

        if left:
            upper0, liq0 = curve[-1]
            nxt = sqrt + (left << shift) // liq0
            total_out += (liq0 * (nxt - sqrt)) // (sqrt * nxt)
            sqrt = nxt

    return total_out, sqrt

def swap_base_to_quote(
    amount_in:         int,
    cliff_fee_num:     int,
    protocol_fee_pct:  int,
    referral_fee_pct:  int,
    cur_sqrt:          int,
    curve:             list[tuple[int,int]]
) -> dict:
    raw_q, nxt = _walk_curve(amount_in, cur_sqrt, curve, True)
    gross_fee    = ceildiv(raw_q * cliff_fee_num, FEE_DEN)
    proto_gross  = gross_fee * protocol_fee_pct // 100
    referral     = proto_gross * referral_fee_pct // 100
    proto_net    = proto_gross - referral
    trading_net  = gross_fee - proto_gross

    return {
        "actualInputAmount": str(amount_in),
        "outputAmount":      str(raw_q - gross_fee),
        "nextSqrtPrice":     str(nxt),
        "tradingFee":        str(trading_net),
        "protocolFee":       str(proto_net),
        "referralFee":       str(referral),
    }

def swap_quote_to_base(
    amount_in:         int,
    cliff_fee_num:     int,
    protocol_fee_pct:  int,
    referral_fee_pct:  int,
    cur_sqrt:          int,
    curve:             list[tuple[int,int]]
) -> dict:
    gross_fee   = ceildiv(amount_in * cliff_fee_num, FEE_DEN)
    net_q       = amount_in - gross_fee
    proto_gross = gross_fee * protocol_fee_pct // 100
    referral    = proto_gross * referral_fee_pct // 100
    proto_net   = proto_gross - referral
    trading_net = gross_fee - proto_gross

    raw_b, nxt = _walk_curve(net_q, cur_sqrt, curve, False)
    return {
        "actualInputAmount": str(net_q),
        "outputAmount":      str(raw_b),
        "nextSqrtPrice":     str(nxt),
        "tradingFee":        str(trading_net),
        "protocolFee":       str(proto_net),
        "referralFee":       str(referral),
    }
