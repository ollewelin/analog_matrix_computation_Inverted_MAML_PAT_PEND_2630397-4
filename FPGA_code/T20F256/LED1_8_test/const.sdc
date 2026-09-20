# =============================================================================
# Timing Constraints for T20F256 — LED binary clock-divider test
# =============================================================================
# Primary system clock: 50 MHz from external oscillator
# Clock period: 1 / 50 MHz = 20 ns
# LED8 full period: 10 s
# LED7 full period: 5 s
# Each lower LED has half the period of the previous LED.
# =============================================================================

create_clock -name CLK_50MHZ -period 20.0 [get_ports {CLK_50MHZ}]
