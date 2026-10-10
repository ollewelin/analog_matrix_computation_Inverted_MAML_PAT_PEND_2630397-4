# T20 <-> T120 Bus Wires

Superseded by [pinout_T120_T20.md](./pinout_T120_T20.md) (wire allocation) and [t120_t20_bridge_spec.md](./t120_t20_bridge_spec.md) (protocol).

Summary: one shared clock `T20_CLK9`, split into an **H-bus** (hardware-synchronous Hadamard, 1-bit ACK, no CRC) and an **S-bus** (software-driven service bus: SoC, SPI flash, trace; CRC8).
