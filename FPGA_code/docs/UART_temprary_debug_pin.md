# UART Temporary Debug Pin Configuration

> [!WARNING]
> **TEMPORARY DEBUG PIN NOTICE**
> The signal `SCLR_DAC_W_34` (Pin **F13**, `GPIOT_RXN07`) is temporarily borrowed as **UART TX Debug Output** (`115200` baud, 8N1).
> **This MUST be removed and restored to DAC control once TCP/IP is fully up and running!**

---

## Hardware Pin Mapping
- **Function:** UART Mini APB3 TX Output
- **FPGA Pin:** `F13` (`GPIOT_RXN07`)
- **Top Level Port:** `output SCLR_DAC_W_34`
- **Host Device:** `/dev/ttyACM0` (115200 baud)
- **APB3 Base Address:** `0xF8100000` (UART Mini)

## Removal Checklist (When TCP/IP is verified)
1. In `T120_MALM.peri.xml`:
   - Change `SCLR_DAC_W_34` mode back to original DAC configuration.
2. In `top_level.sv`:
   - Disconnect `uart_mini_txd` from `SCLR_DAC_W_34`.
   - Restore `SCLR_DAC_W_34` to its DAC reset role or default tie-off.
3. In firmware `main.c`:
   - Disable verbose UART logging if no longer needed.

