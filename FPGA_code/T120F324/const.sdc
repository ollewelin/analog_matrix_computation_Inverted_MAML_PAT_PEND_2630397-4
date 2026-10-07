# =============================================================================
# Timing Constraints for T120F324 — Inverted MAML SoC
# =============================================================================

# Primary system clock: 50 MHz from external oscillator (20.0 ns)
create_clock -name T120_GCLK -period 20.000 [get_ports {T120_GCLK}]

# Ethernet 25 MHz clocks for 100M RGMII mode (40.0 ns)
create_clock -name PLL_25MHZ -period 40.000 [get_ports {PLL_25MHZ}]
create_clock -name pll_clk_25Mhz_ext -period 40.000 [get_ports {pll_clk_25Mhz_ext}]
create_clock -name F2_RXC -period 40.000 [get_ports {F2_RXC}]

# Declare asynchronous clock domains
set_clock_groups -asynchronous \
    -group [get_clocks {T120_GCLK}] \
    -group [get_clocks {PLL_25MHZ}] \
    -group [get_clocks {pll_clk_25Mhz_ext}] \
    -group [get_clocks {F2_RXC}]
