# EDITABLE INPUTS: monetary amounts in USD millions; shares in millions.
STARTING_FCFF = 100
GROWTH_RATES = [0.08, 0.06, 0.05, 0.04, 0.03]
WACC = 0.10
TERMINAL_GROWTH = 0.03
CASH = 50
DEBT = 300
DILUTED_SHARES = 50

# Editable sensitivity and reverse-DCF settings. Shifts are decimal rates:
# 0.01 means ONE percentage point added to EACH annual growth rate.
WACC_VALUES = [0.09, 0.10, 0.11]
TERMINAL_GROWTH_VALUES = [0.02, 0.03, 0.04]
TARGET_SHARE_PRICE = 30.00
SHIFT_LOWER = -0.05
SHIFT_UPPER = 0.10
RUN_COMPANY = True

# Robinhood classroom estimates, prepared September 10, 2026.
# Exact sources, assumptions, dates, and limitations: HOOD-research/Robinhood_DCF_checkout.md
# Annual FCFF uses FY2025; bridge uses June 30, 2026. Not normalized FCFF.
COMPANY_STARTING_FCFF = 1638 + 31 * (1 - 0.21) - 15 - 39
COMPANY_GROWTH_RATES = [0.30, 0.25, 0.20, 0.15, 0.10]  # analyst forecast
COMPANY_CASH = 5362  # gross corporate cash; excess-cash adjustment unresolved
COMPANY_DEBT = 2200 + 959  # face-value notes + Trust debt incl. interest
COMPANY_DILUTED_SHARES = 912
COMPANY_TARGET_PRICE = 113.33  # Sep 10, 2026, 4:00 PM EDT close
COMPANY_EQUITY_MARKET_VALUE = 101810  # market value for WACC weights only
COMPANY_COST_OF_EQUITY = 0.0483 + 2.34 * 0.05
# Classroom coupon proxy: zero-coupon convertibles + Trust rate, after tax.
# Debt face value approximates market value; coupon is not economic debt yield.
COMPANY_WACC = (
    COMPANY_EQUITY_MARKET_VALUE * COMPANY_COST_OF_EQUITY
    + 959 * 0.0506 * (1 - 0.21)
) / (COMPANY_EQUITY_MARKET_VALUE + COMPANY_DEBT)
COMPANY_TERMINAL_GROWTH = 0.03  # long-run nominal growth assumption
COMPANY_WACC_VALUES = [COMPANY_WACC - 0.01, COMPANY_WACC, COMPANY_WACC + 0.01]
COMPANY_TERMINAL_GROWTH_VALUES = [0.02, 0.03, 0.04]
COMPANY_SHIFT_LOWER = -0.05
COMPANY_SHIFT_UPPER = 0.10  # report no solution if this bracket cannot reach price
# Explicit second experiment; never silently widen the initial bracket.
COMPANY_EXTENDED_SHIFT_UPPER = 0.60

import math


def discounted_share_value(starting_fcff, growth_rates, wacc, terminal_growth,
                    cash, debt, shares, shift=0.0):
    values = [starting_fcff, wacc, terminal_growth, cash, debt, shares,
              shift, *growth_rates]
    if not all(math.isfinite(x) for x in values):
        raise ValueError("All inputs must be finite numbers.")
    if len(growth_rates) != 5 or shares <= 0:
        raise ValueError("Provide five growth rates and positive diluted shares.")
    if wacc <= -1 or terminal_growth <= -1 or terminal_growth >= wacc:
        raise ValueError("Require -100% < terminal growth < WACC.")
    if any(g + shift <= -1 for g in growth_rates):
        raise ValueError("An annual growth rate is -100% or below.")
    flow, pv = starting_fcff, 0.0
    for year, growth in enumerate(growth_rates, 1):
        flow *= 1 + growth + shift
        pv += flow / (1 + wacc) ** year
    pv += flow * (1 + terminal_growth) / (wacc - terminal_growth) / (1 + wacc) ** 5
    result = (pv + cash - debt) / shares
    if not math.isfinite(result):
        raise ValueError("Valuation overflowed; revise the inputs.")
    return result


def solve_shift(target, lower, upper, starting_fcff, growth_rates,
                wacc, terminal_growth, cash, debt, shares):
    if not all(math.isfinite(x) for x in [target, lower, upper]) or lower >= upper:
        raise ValueError("Require finite target and finite lower < upper bounds.")
    if starting_fcff <= 0:
        raise ValueError("Nonpositive FCFF requires an explicit cash-flow path, not a growth-shift solve.")
    if any(g + lower <= -1 or g + upper <= -1 for g in growth_rates):
        raise ValueError("Bracket refused: an annual growth rate reaches -100% or below.")
    def price(shift):
        return discounted_share_value(starting_fcff, growth_rates, wacc,
                               terminal_growth, cash, debt, shares, shift)
    low_price, high_price = price(lower), price(upper)
    if not low_price <= target <= high_price:
        return None
    for _ in range(200):
        midpoint = (lower + upper) / 2
        result = price(midpoint)
        if abs(result - target) <= 1e-9:
            return midpoint
        if result < target:
            lower = midpoint
        else:
            upper = midpoint
    raise ValueError("Bisection did not converge to the required price tolerance.")


def print_analysis(starting_fcff, growth_rates, wacc, terminal_growth,
                   cash, debt, shares, wacc_values, terminal_values,
                   target, lower, upper, label):
    print(f"\nSensitivity grid - {label} (USD per diluted share; * = base)")
    print("WACC / g".ljust(13) + "".join(f"{g:>12.2%}" for g in terminal_values))
    for rate in wacc_values:
        cells = []
        for growth in terminal_values:
            try:
                value = discounted_share_value(starting_fcff, growth_rates, rate,
                                        growth, cash, debt, shares)
                mark = "*" if math.isclose(rate, wacc) and math.isclose(growth, terminal_growth) else ""
                cells.append(f"{value:.2f}{mark}".rjust(12))
            except ValueError:
                cells.append("INVALID".rjust(12))
        print(f"{rate:<13.4%}" + "".join(cells))
    print(f"\nReverse DCF - {label}")
    print(f"Target price: ${target:.2f}; uniform-shift bracket: {lower*100:+.2f} to {upper*100:+.2f} percentage points")
    print(f"Held fixed: starting FCFF={starting_fcff:.4f} USD millions; WACC={wacc:.8%}; "
          f"terminal growth={terminal_growth:.2%}; cash={cash} USD millions; "
          f"debt={debt} USD millions; diluted shares={shares} million; "
          "five-year horizon; year-end discounting; annual growth-path shape.")
    print("Unshifted growth path: " + ", ".join(f"{g:.2%}" for g in growth_rates))
    try:
        shift = solve_shift(target, lower, upper, starting_fcff, growth_rates,
                            wacc, terminal_growth, cash, debt, shares)
        if shift is None:
            endpoints = [discounted_share_value(starting_fcff, growth_rates, wacc,
                         terminal_growth, cash, debt, shares, s) for s in (lower, upper)]
            print(f"No solution in that bracket. Endpoint prices: ${endpoints[0]:.4f} to ${endpoints[1]:.4f}.")
        else:
            print(f"Solved uniform shift: {shift*100:+.6f} percentage points")
            print("Implied growth path: " + ", ".join(f"{g+shift:.4%}" for g in growth_rates))
            matched = discounted_share_value(starting_fcff, growth_rates, wacc,
                                      terminal_growth, cash, debt, shares, shift)
            print(f"Matched value per share: ${matched:.6f}")
    except ValueError as error:
        print(f"Reverse DCF refused: {error}")
    print("One set of assumptions consistent with the price; not proof of mispricing.")


def main(STARTING_FCFF=STARTING_FCFF, GROWTH_RATES=GROWTH_RATES, WACC=WACC,
         TERMINAL_GROWTH=TERMINAL_GROWTH, CASH=CASH, DEBT=DEBT,
         DILUTED_SHARES=DILUTED_SHARES, wacc_values=WACC_VALUES,
         terminal_values=TERMINAL_GROWTH_VALUES, target=TARGET_SHARE_PRICE,
         lower=SHIFT_LOWER, upper=SHIFT_UPPER, label="TRAINING"):
    discounted_share_value(STARTING_FCFF, GROWTH_RATES, WACC, TERMINAL_GROWTH,
                    CASH, DEBT, DILUTED_SHARES)
    if TERMINAL_GROWTH >= WACC:
        raise SystemExit("Error: terminal growth must be less than WACC.")
    if len(GROWTH_RATES) != 5:
        raise SystemExit("Error: provide exactly five annual growth rates.")
    if WACC <= -1:
        raise SystemExit("Error: WACC must be greater than -1.")
    if DILUTED_SHARES <= 0:
        raise SystemExit("Error: diluted shares must be positive.")

    cash_flows = []
    fcff = STARTING_FCFF
    for growth in GROWTH_RATES:
        fcff *= 1 + growth
        cash_flows.append(fcff)

    pv_explicit = sum(
        flow / (1 + WACC) ** year
        for year, flow in enumerate(cash_flows, start=1)
    )
    terminal_value = cash_flows[-1] * (1 + TERMINAL_GROWTH) / (WACC - TERMINAL_GROWTH)
    pv_terminal = terminal_value / (1 + WACC) ** len(cash_flows)
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value + CASH - DEBT
    value_per_share = equity_value / DILUTED_SHARES
    if enterprise_value == 0:
        raise SystemExit("Error: terminal value share is undefined when enterprise value is zero.")
    terminal_share = pv_terminal / enterprise_value

    for year, flow in enumerate(cash_flows, start=1):
        print(f"FCFF Year {year} (USD millions): {flow:.4f}")
    print(f"PV of five explicit FCFF (USD millions): {pv_explicit:.4f}")
    print(f"Terminal value at Year 5 (USD millions): {terminal_value:.4f}")
    print(f"PV of terminal value (USD millions): {pv_terminal:.4f}")
    print(f"Enterprise value (USD millions): {enterprise_value:.4f}")
    print(f"Equity value (USD millions): {equity_value:.4f}")
    print(f"Value per diluted share (USD): {value_per_share:.4f}")
    print(f"PV of terminal value / enterprise value (fraction): {terminal_share:.4f}")
    print_analysis(STARTING_FCFF, GROWTH_RATES, WACC, TERMINAL_GROWTH,
                   CASH, DEBT, DILUTED_SHARES, wacc_values, terminal_values,
                   target, lower, upper, label)


if __name__ == "__main__":
    main()
    if RUN_COMPANY:
        print("\nROBINHOOD - PROVISIONAL CLASSROOM ESTIMATE; see sourced checkout for limitations")
        main(COMPANY_STARTING_FCFF, COMPANY_GROWTH_RATES, COMPANY_WACC,
             COMPANY_TERMINAL_GROWTH, COMPANY_CASH, COMPANY_DEBT,
             COMPANY_DILUTED_SHARES, COMPANY_WACC_VALUES,
             COMPANY_TERMINAL_GROWTH_VALUES, COMPANY_TARGET_PRICE,
             COMPANY_SHIFT_LOWER, COMPANY_SHIFT_UPPER, "HOOD ESTIMATE")
        print("\nSeparate, explicitly wider reverse-DCF experiment:")
        print(f"Bracket: {COMPANY_SHIFT_LOWER*100:+.2f} to {COMPANY_EXTENDED_SHIFT_UPPER*100:+.2f} percentage points; "
              f"target=${COMPANY_TARGET_PRICE:.2f}; held fixed: all HOOD inputs listed above.")
        try:
            shift = solve_shift(COMPANY_TARGET_PRICE, COMPANY_SHIFT_LOWER,
                                COMPANY_EXTENDED_SHIFT_UPPER, COMPANY_STARTING_FCFF,
                                COMPANY_GROWTH_RATES, COMPANY_WACC,
                                COMPANY_TERMINAL_GROWTH, COMPANY_CASH,
                                COMPANY_DEBT, COMPANY_DILUTED_SHARES)
            if shift is None:
                print("No solution in that bracket.")
            else:
                print(f"Solved uniform shift: {shift*100:+.6f} percentage points")
                print("Implied growth path: " + ", ".join(f"{g+shift:.4%}" for g in COMPANY_GROWTH_RATES))
                matched = discounted_share_value(COMPANY_STARTING_FCFF,
                    COMPANY_GROWTH_RATES, COMPANY_WACC, COMPANY_TERMINAL_GROWTH,
                    COMPANY_CASH, COMPANY_DEBT, COMPANY_DILUTED_SHARES, shift)
                print(f"Matched value per share: ${matched:.6f}")
        except ValueError as error:
            print(f"Reverse DCF refused: {error}")
