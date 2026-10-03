cat << 'EOF' > FPGA_code/docs/pinout_T120_T20.md
# Inter-FPGA Interface Specification (T120 Master <-> T20 Compute)

Source definition: `FPGA_code/T120F324/T120_MALM.peri.xml`

## Bus Topology Summary
- **Clock:** `T20_CLK9` (GPIOL_72) driven by T120 as bus master.
- **TX Bus (T120 -> T20):** 4 single-ended lines (TX11_P/N, TX12_P/N).
- **RX Bus (T20 -> T120):** 8 single-ended lines (RX00_P/N through RX03_P/N).
- **IO Standard:** 3.3 V LVTTL / LVCMOS.

## Signal Pinout Mapping

| Net Name | Efinix GPIO Def | Direction (T120 POV) | IO Standard | Notes |
|:---|:---|:---|:---|:---|
| `T20_CLK9` | `GPIOL_72` | Output | 3.3 V LVCMOS | Bus Synchronization Clock |
| `TX11_T20_P1` | `GPIOT_RXP01` | Output | 3.3 V LVCMOS | Master TX Lane 0 (Positive pin) |
| `TX11_T20_N1` | `GPIOT_RXN01` | Output | 3.3 V LVCMOS | Master TX Lane 1 (Negative pin) |
| `TX12_T20_P1` | `GPIOT_RXP02` | Output | 3.3 V LVCMOS | Master TX Lane 2 (Positive pin) |
| `TX12_T20_N1` | `GPIOT_RXN02` | Output | 3.3 V LVCMOS | Master TX Lane 3 (Negative pin) |
| `RX00_T20_P1` | `GPIOB_TXP00` | Input | 3.3 V LVCMOS | Compute RX Lane 0 |
| `RX00_T20_N1` | `GPIOB_TXN00` | Input | 3.3 V LVCMOS | Compute RX Lane 1 |
| `RX01_T20_P1` | `GPIOB_TXP01` | Input | 3.3 V LVCMOS | Compute RX Lane 2 |
| `RX01_T20_N1` | `GPIOB_TXN01` | Input | 3.3 V LVCMOS | Compute RX Lane 3 |
| `RX02_T20_P1` | `GPIOB_TXP02` | Input | 3.3 V LVCMOS | Compute RX Lane 4 |
| `RX02_T20_N1` | `GPIOB_TXN02` | Input | 3.3 V LVCMOS | Compute RX Lane 5 |
| `RX03_T20_P1` | `GPIOB_TXP03` | Input | 3.3 V LVCMOS | Compute RX Lane 6 |
| `RX03_T20_N1` | `GPIOB_TXN03` | Input | 3.3 V LVCMOS | Compute RX Lane 7 |

## Operating Mode
All differential pins (`_P1` / `_N1`) are routed and configured as individual single-ended GPIOs running at 3.3 V.
EOF