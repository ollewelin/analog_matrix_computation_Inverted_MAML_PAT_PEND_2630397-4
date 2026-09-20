# =============================================================================
# Timing Constraints for T120F324 — LED clock-divider test
# =============================================================================
# Primary system clock: 50 MHz from external oscillator
# Clock period: 1 / 50 MHz = 20 ns
# =============================================================================

create_clock -name T120_GCLK -period 20.0 [get_ports {T120_GCLK}]
