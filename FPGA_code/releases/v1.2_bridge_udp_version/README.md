# T120 FPGA Bitstream & Hex Release: v1.2

- **Version Tag:** `v1.2`
- **Release Date:** 2026-10-10
- **Ethernet Version String:** `T120_SOC_ETH_FW v1.2 (Bridge OK, LED2_UART, Build 2026-10-10)`
- **Board Target:** Efinix Trion T120F324
- **IP Address:** `192.168.1.50`
- **MAC Address:** `00:12:34:56:78:9A`
- **UDP Version Query Port:** UDP Port `5000`

---

## Files in this Directory

| File | Type | Size | Description |
| :--- | :--- | :--- | :--- |
| **`T120_MALM_v1.2.bit`** | SRAM Bitstream | ~10.6 MB | Temporary bitstream loaded directly to FPGA SRAM via JTAG. |
| **`T120_MALM_v1.2.hex`** | Flash Image | ~10.6 MB | Active SPI flash image for non-volatile board booting. |
| **`README.md`** | Documentation | — | This specification and operation guide. |

---

## Programming Instructions

### 1. Temporary JTAG Load (.bit)
```bash
python3 FPGA_code/scripts/program_t120.py FPGA_code/releases/v1.2_bridge_udp_version/T120_MALM_v1.2.bit
```

### 2. Manual SPI Flash (.hex)
Use the Efinity Programmer GUI or manual SPI programmer targeting the SPI NOR Flash connected to the Trion T120 using:
`FPGA_code/releases/v1.2_bridge_udp_version/T120_MALM_v1.2.hex`

---

## Ethernet Testing & Verification

### Ping Verification
```bash
ping -c 4 192.168.1.50
```
*Expected Result:* Zero packet loss, ~0.29 ms round-trip time.

### Version Query over Ethernet (UDP)
```bash
echo "VERSION" | nc -u -w2 192.168.1.50 5000
```
*Expected Response:*
```text
T120_SOC_ETH_FW v1.2 (Bridge OK, LED2_UART, Build 2026-10-10)
```

---

## Hardware Pin Allocation & Changes

1. **`SCLR_DAC_W_34` (Pin F13):**
   - Disconnected from debug UART.
   - Restored and safely tied low (`1'b0`) in top level.
2. **`SCK_DAC8_W_15` (Pin E16):**
   - Kept in Interface Specification and tied low (`1'b0`).
3. **`T120_LED2` (Pin B17):**
   - Assigned to Sapphire SoC `uart_txd` (115200 baud).
4. **`T120_LED1`:**
   - Dedicated as patch wire to T20 `CRESET_N` (hardware reset line).
5. **T120 <-> T20 Bridge:**
   - H-bus (Hadamard synchronous sequencer) and S-bus (service bus) fully operational on APB3 `0xF810_3000`.
