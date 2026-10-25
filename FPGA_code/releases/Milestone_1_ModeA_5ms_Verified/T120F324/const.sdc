# =============================================================================
# Timing Constraints for T120F324 — Inverted MAML SoC
# =============================================================================

# Primary system clock: 50 MHz from external oscillator (20.0 ns)
create_clock -name T120_GCLK -period 20.000 [get_ports {T120_GCLK}]

# The reference design transmits at 100 Mbit/s from the PLL's 25 MHz output.
# The 125 MHz output clocks remain constrained for the target board's PLL.
create_clock -name PLL_125MHZ -period 8.000 [get_ports {PLL_125MHZ}]
# 90-degree shifted 125 MHz clock for the RGMII TXC DDIO pad
create_clock -name PLL_125MHZ_90DEG -waveform {2.000 6.000} -period 8.000 [get_ports {PLL_125MHZ_90DEG}]
create_clock -name pll_clk_25Mhz_ext -period 40.000 [get_ports {pll_clk_25Mhz_ext}]
create_clock -name pll_clk_100Mhz -period 10.000 [get_ports {pll_clk_100Mhz}]
create_clock -name pll_clk_75Mhz -period 13.333 [get_ports {pll_clk_75Mhz}]
create_clock -name pll_clk_50Mhz -period 20.000 [get_ports {pll_clk_50Mhz}]
create_clock -name pll_clk_80Mhz -period 12.500 [get_ports {pll_clk_80Mhz}]

# PHY-generated RGMII receive clock.  Constrain for the 1-Gbit worst case;
# lower PHY link speeds use a divided clock and are less restrictive.
create_clock -name F2_RXC -period 8.000 [get_ports {F2_RXC}]

# Declare asynchronous clock domains
set_clock_groups -asynchronous \
    -group [get_clocks {T120_GCLK}] \
    -group [get_clocks {PLL_125MHZ}] \
    -group [get_clocks {PLL_125MHZ_90DEG}] \
    -group [get_clocks {pll_clk_25Mhz_ext}] \
    -group [get_clocks {pll_clk_100Mhz}] \
    -group [get_clocks {pll_clk_75Mhz}] \
    -group [get_clocks {pll_clk_50Mhz}] \
    -group [get_clocks {pll_clk_80Mhz}] \
    -group [get_clocks {F2_RXC}]

# The separate MDIO master synchronizes the asynchronous PHY management input.
set_false_path -from [get_ports {F2_MDIO_IN}]
