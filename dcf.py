# EDITABLE INPUTS: monetary amounts in USD millions; shares in millions.
STARTING_FCFF = 100
GROWTH_RATES = [0.08, 0.06, 0.05, 0.04, 0.03]
WACC = 0.10
TERMINAL_GROWTH = 0.03
CASH = 50
DEBT = 300
DILUTED_SHARES = 50


def main():
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


if __name__ == "__main__":
    main()
