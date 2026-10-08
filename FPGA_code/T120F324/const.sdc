# =============================================================================
# Timing Constraints for T120F324 — Inverted MAML SoC
# =============================================================================

# Primary system clock: 50 MHz from external oscillator (20.0 ns)
create_clock -name T120_GCLK -period 20.000 [get_ports {T120_GCLK}]

# Ethernet TSE MAC reference clock: always 125 MHz (RGMII 100M TXC is divided by 5 inside the MAC)
create_clock -name PLL_125MHZ -period 8.000 [get_ports {PLL_125MHZ}]
# 90-degree shifted 125 MHz clock for the RGMII TXC DDIO pad
create_clock -name PLL_125MHZ_90DEG -waveform {2.000 6.000} -period 8.000 [get_ports {PLL_125MHZ_90DEG}]
create_clock -name pll_clk_25Mhz_ext -period 40.000 [get_ports {pll_clk_25Mhz_ext}]
create_clock -name F2_RXC -period 40.000 [get_ports {F2_RXC}]

# Declare asynchronous clock domains
set_clock_groups -asynchronous \
    -group [get_clocks {T120_GCLK}] \
    -group [get_clocks {PLL_125MHZ}] \
    -group [get_clocks {PLL_125MHZ_90DEG}] \
    -group [get_clocks {pll_clk_25Mhz_ext}] \
    -group [get_clocks {F2_RXC}]
