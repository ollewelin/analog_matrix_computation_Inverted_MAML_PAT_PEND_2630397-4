# Inter-FPGA Interface Specification (T120 Master <-> T20 Compute)

Source definition: `FPGA_code/T120F324/T120_MALM.peri.xml`. Protocol: [t120_t20_bridge_spec.md](./t120_t20_bridge_spec.md).

## Bus Topology Summary
- **Clock:** `T20_CLK9` (GPIOL_72) driven by T120 as bus master, shared by both buses.
- **H-bus (Hadamard, hardware-synchronous):** `TX11_P/N` (T120 -> T20) and `RX00_P` (ACK, T20 -> T120).
- **S-bus (service / SoC / SPI flash / trace):** `TX12_P/N` (2 bit) and `RX02_P/N`, `RX03_P/N` (4 bit).
- **Reset:** T20 `CRESET_N` is driven by the T120 pin `T120_LED1` (GPIOL_75) via patch wire.
- **IO Standard:** 3.3 V LVTTL / LVCMOS, all pins single-ended.

## Signal Pinout Mapping

| Net Name | Efinix GPIO Def | Dir (T120 POV) | Bus | Function |
|:---|:---|:---|:---|:---|
| `T20_CLK9` | `GPIOL_72` | Output | both | Bus clock (T120 launches TX on falling edge, T20 launches RX on rising edge) |
| `TX11_T20_P1` | `GPIOT_RXP01` | Output | H | `H_SYNC` |
| `TX11_T20_N1` | `GPIOT_RXN01` | Output | H | `H_DATA` |
| `TX12_T20_P1` | `GPIOT_RXP02` | Output | S | `S_TX[0]` |
| `TX12_T20_N1` | `GPIOT_RXN02` | Output | S | `S_TX[1]` |
| `RX00_T20_P1` | `GPIOB_TXP00` | Input | H | `H_ACK` (1-bit) |
| `RX00_T20_N1` | `GPIOB_TXN00` | Input | H | spare (`H_STATUS`) |
| `RX01_T20_P1` | `GPIOB_TXP01` | Input | - | reserved |
| `RX01_T20_N1` | `GPIOB_TXN01` | Input | - | reserved |
| `RX02_T20_P1` | `GPIOB_TXP02` | Input | S | `S_RX[0]` |
| `RX02_T20_N1` | `GPIOB_TXN02` | Input | S | `S_RX[1]` |
| `RX03_T20_P1` | `GPIOB_TXP03` | Input | S | `S_RX[2]` |
| `RX03_T20_N1` | `GPIOB_TXN03` | Input | S | `S_RX[3]` |
| `T120_LED1` | `GPIOL_75` | Output | - | `T20_CRESET_N` (active low, released = high) |

## Operating Mode
All differential pins (`_P1` / `_N1`) are routed and configured as individual single-ended GPIOs running at 3.3 V.
