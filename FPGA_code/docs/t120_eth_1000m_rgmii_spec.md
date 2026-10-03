# T120 Ethernet PHY Hardware Architecture: 1000M RGMII via MDIO

**Document Reference:** `T120-ETH-1000M-RGMII-SPEC`  
**Target Hardware:** Efinix Trion T120F324 FPGA  
**Ethernet PHY:** Realtek RTL8211F-CG (Gigabit Ethernet Transceiver)  
**Management Interface:** Clause-22 MDIO via Dedicated APB3 Master

---

## 1. Operating Mode & Default Speed

- **Default Operational Speed:** **1000 Mbit/s (Gigabit Ethernet, 1000BASE-T Full-Duplex)**.
- **Legacy Fallback Note:** The reference design (`top_level.sv` in `BRAM/T120F324_A`) initially instantiated `eth_mac_100m.sv` operating at 100 Mbps SDR (25 MHz clocking). However, the board hardware mapping and the RTL8211F-CG PHY on the T120 board are fully capable of **1000M RGMII** operation.
- **Hardware Verification Status:** Verified in hardware diagnostic testing:
  - PHY JEDEC IDs: `PHYID1 = 0x001C`, `PHYID2 = 0xC916` (RTL8211F-CG).
  - 1G Loopback & 1000M Full Duplex Auto-Negotiation verified (`BMSR = 0x79AD`, `PHSR = 0x312E 1000M FD`, `** LINK OK **`).

---

## 2. Pin Mapping & Signal Interface (`T120_MALM.peri.xml`)

| Net Name | Efinix GPIO Def | Direction | Standard | Function |
|:---|:---|:---|:---|:---|
| `F2_MDC` | `GPIOB_TXP10` | Output | 3.3 V LVCMOS | MDIO Management Clock (up to 2.5 MHz) |
| `F2_MDIO` | `GPIOB_TXN10` | In/Out/OE | 3.3 V LVCMOS | MDIO Bidirectional Management Data |
| `F2_RSTB` | `GPIOB_TXN11` | Output | 3.3 V LVCMOS | Active-Low Hardware Reset to RTL8211F |
| `F2_INTB` | `GPIOB_TXP11` | Input | 3.3 V LVCMOS | PHY Interrupt Output |
| `F2_RXC` | `GPIOL_73` | Input | 3.3 V LVCMOS (GCLK) | RGMII 125 MHz RX Clock from PHY |
| `F2_RXCTL` | `GPIOL_13` | Input | 3.3 V LVCMOS | RGMII RX Control / Data Valid |
| `F2_RXD[3:0]` | `GPIOL_12, 11, 04, 05` | Input | 3.3 V LVCMOS | RGMII RX Data Nibbles |
| `F2_TXC` | `GPIOL_17` | Output | 3.3 V LVCMOS | RGMII 125 MHz TX Clock to PHY |
| `F2_TXCTL` | `GPIOL_15` | Output | 3.3 V LVCMOS | RGMII TX Control / Enable |
| `F2_TXD[3:0]` | `GPIOL_18, 20, 22, 24` | Output | 3.3 V LVCMOS | RGMII TX Data Nibbles |

---

## 3. MDIO Register Configuration Sequence for 1000M Mode

To configure the RTL8211F PHY for 1000M operation, the RISC-V SoC must execute the following sequence via the MDIO APB Master (`0x80010000` or SoC mapped APB address):

```c
// 1. Hardware Reset Pulse
mdio_phy_reset_assert();
bsp_uDelay(50000);   // >= 50 ms in reset
mdio_phy_reset_release();
bsp_uDelay(300000);  // >= 300 ms for PHY internal boot & PLL lock

// 2. Configure 1000BASE-T Advertisement (Reg 0x09: GBCR)
// Set Bit 9 (1000BASE-T Full Duplex advertisement)
mdio_write(PHY_ADDR, 0x09, 0x0200);

// 3. Configure Auto-Negotiation Advertisement (Reg 0x04: ANAR)
// Advertise 100M FD/HD, 10M FD/HD, and 802.3 selector
mdio_write(PHY_ADDR, 0x04, 0x01E1);

// 4. Set RGMII TX/RX Clock Timing Delays (Page 0xd08, Reg 0x11)
mdio_write(PHY_ADDR, 0x1F, 0x0d08); // Switch to Page 0xd08
mdio_write(PHY_ADDR, 0x11, 0x018A); // Apply calibrated RGMII delay parameters
mdio_write(PHY_ADDR, 0x1F, 0x0000); // Return to Page 0x0000

// 5. Restart Auto-Negotiation with 1000M Full Duplex preference (Reg 0x00: BMCR)
// Bit 12 = Auto-neg enable, Bit 9 = Restart auto-neg, Bit 8 = Full Duplex, Bit 6 = 1000M speed MSB
mdio_write(PHY_ADDR, 0x00, 0x1340);
```

---

## 4. MAC Layer Architecture in T120

- **Clock Domains:**
  - System / SoC Core Clock: 50 MHz (`T120_GCLK`).
  - Gigabit TX / RX Clock: 125 MHz (`F2_RXC` and PLL 125 MHz for `F2_TXC`).
- **DDR Double Data Rate Serialization:**
  - In 1000M RGMII mode, 8-bit octets are split into two 4-bit nibbles transferred on both the rising and falling edges of the 125 MHz clock.
  - The Efx TSE MAC IP core (`rgmii_eth_efx_tsemac`) or soft RGMII DDR bridge handles the 8-bit GMII \(\leftrightarrow\) 4-bit RGMII conversion.
