# UART Temporary Debug Pin Configuration

> [!WARNING]
> **TEMPORARY DEBUG PIN NOTICE**
> We have two distinct debug UART channels available for hardware bringup:
> 1. **UART Mini (APB3 Logic UART):** Borrowed on `SCLR_DAC_W_34` (Pin **F13**, `GPIOT_RXN07`).
> 2. **SoC UART 0 (Sapphire Internal UART):** Can be routed to `SCK_DAC8_W_34` (Pin **E13**, `GPIOT_RXP07`, adjacent to F13 on header) or `SCK_DAC8_W_15` (Pin **E16**).
> **Both pins MUST be restored to their DAC control roles once Ethernet/TCP-IP is verified!**

---

## Channel 1: APB3 Logic UART (`uart_mini`)
- **Controller:** Standalone APB3 peripheral (`uart_mini_apb3.sv`)
- **APB3 Base Address:** `0xF8100000`
- **Driver:** `uart_mini_driver.h` (`uart_mini_tx_string`)
- **Default Baud Rate:** 9600 baud (50 MHz sys_clk)
- **FPGA Pin:** `F13` (`GPIOT_RXN07`)
- **Top Level Port:** `output SCLR_DAC_W_34`
- **Pacing Rule:** Requires inter-character delay (`~1 ms`) to prevent USB bridge overrun.

---

## Channel 2: Sapphire SoC Native UART 0 (`system_uart_0`)
- **Controller:** Hardened Sapphire SoC UART core (`system_uart_0_io_txd`)
- **Base Address:** `0xF8001000` (`SYSTEM_UART_0_IO_CTRL`)
- **Driver:** Efinix BSP `bsp.h` / `uart.h` (`bsp_printf`, `bsp_putChar`)
- **Default Baud Rate:** 115200 baud (SoC internal divider)
- **FPGA Pin Option A:** `E13` (`SCK_DAC8_W_34`, `GPIOT_RXP07`) - Right next to F13 (differential pair partner).
  - *Note:* In `T120_MALM.peri.xml`, change `SCK_DAC8_W_34` mode from `input` to `output`.
- **FPGA Pin Option B:** `E16` (`SCK_DAC8_W_15`, `GPIOT_RXP09_CLKP0`) - Already configured as `output`.

---

## Dual UART Comparison

| Feature | Channel 1: APB3 `uart_mini` | Channel 2: SoC `uart_0` |
| :--- | :--- | :--- |
| **Source** | Custom Verilog IP on APB3 | Efinix Sapphire IP block |
| **Address** | `0xF8100000` | `0xF8001000` |
| **Baud** | 9600 baud | 115200 baud |
| **Target Pin** | Pin `F13` (`SCLR_DAC_W_34`) | Pin `E13` (`SCK_DAC8_W_34`) |
| **Primary Use** | Landmark logging with pacing | Standard BSP `printf` terminal |

---

## Removal Checklist (When TCP/IP is verified)
1. In `T120_MALM.peri.xml`:
   - Restore `SCLR_DAC_W_34` and `SCK_DAC8_W_34` modes to original DAC SPI clock/clear roles.
2. In `top_level.sv`:
   - Disconnect `uart_mini_txd` and `sapphire_uart_txd` from the DAC ports.
   - Restore default tie-offs or DAC controller logic.
3. In firmware `main.c`:
   - Disable verbose UART debug streams.
