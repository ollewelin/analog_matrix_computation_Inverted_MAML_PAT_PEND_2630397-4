# T120 Ethernet ping debug journal (handover)

Status date: 2026-10-09 (evening). Goal: `ping 192.168.1.50` from the host (`enp2s0`, 192.168.1.129)
to the T120 board running the Sapphire SoC with the reference-style 100-Mbit APB MAC.

## 1. Current state in one paragraph

The design builds and meets timing (build with the reference MAC: `F2_RXC` 139.6 MHz vs 125 target,
`T120_GCLK` 52.2 MHz vs 50 target). PHY (RTL8211F, PHYAD 0x05) autonegotiates **100M full duplex**,
MDIO from C works, the CPU/UART/bridge self-test work. **Ping still fails**: the host never gets an ARP
reply for 192.168.1.50 and the MAC RX valid-frame counter stays 0. The MAC sees frame starts
(sticky status bit 3 / "CRCFLAG" set) but every received frame fails the length/CRC check, so the
RX data path is corrupted or mis-sampled. TX: the MAC TX counter increments, but the host has never
seen a frame from the board (not verified on the wire, host `tcpdump` needs sudo).

## 2. What was changed (all uncommitted in the working tree)

| File | Change |
|---|---|
| `T120F324/top_level.sv` | APB map: MDIO master `0xF8101000`, 100M MAC `0xF8102000`, T20 bridge `0xF8103000`. TSE + packet FIFO removed. Direct Sapphire UART kept. |
| `T120F324/T120_MALM.xml` | Source list: `eth_mac_100m.sv`, `ip/mdio_master/mdio_master.sv`; TSE/APB-to-AXI removed. |
| `T120F324/T120_MALM.peri.xml` | TX pins F2_TXC/TXCTL/TXD0-3 are now plain single-ended outputs (were DDIO). Pin locations unchanged. |
| `T120F324/const.sdc` | Clocks: T120_GCLK 50, pll_clk_25Mhz_ext 25 (TX), F2_RXC 125 MHz (worst-case constraint). |
| `T120F324/eth_mac_100m.sv` | Reference MAC **plus a diagnostic block at the end** (see section 4). The earlier locally modified MAC (extra partial-word RX write) failed timing (F2_RXC 88 MHz) and was replaced by the reference version; the diagnostic block is separate logic. |
| `sw/t120_master/include/mdio_apb_master.h` | New driver for the APB MDIO master (shared TSE `mdio_driver.h` left untouched). |
| `sw/t120_master/src/main.c` | Reference-style MAC register map, ARP/ICMP responder, PHY init (autoneg 10/100, GBCR=0, ANAR=0x01E1, green ethernet off), RGMII delay sweep, RX diagnostics, bridge self-test. |
| `scripts/build_t120_fpga.sh` | Timing guard now gets `top_level.sv` as second argument. |

Not changed on purpose: TSE-related shared BSP driver, UART mapping, T20 bridge RTL.

## 3. Findings and experiments (in order)

1. Efinity full compile works (`bash FPGA_code/scripts/build_t120_fpga.sh`, ~25 min).
   * Run 1 (locally modified MAC): setup slack -0.204 ns (50 MHz), -3.323 ns (RXC). Failed.
   * Run 2 (reference MAC): +0.832 ns, +0.839 ns. Passed. Warnings "No clocks matched pll_clk_100Mhz/75/50/80,
     PLL_125MHZ*" in the SDC are harmless (those clocks are not used by the design).
2. Fast firmware flow works without resynthesis: `python3 FPGA_code/scripts/flash_soc.py`
   (needs the compiler `riscv-none-embed-gcc` in `/home/olle/efinity/efinity-riscv-ide-2025.1/toolchain/bin`,
   patches BRAM into the existing bitstream from `outflow/`, programs via JTAG). It needs the files
   in `T120F324/outflow` and `T120F324/work_pnr/T120_MALM.lbf` of the LAST full build.
3. Original firmware forced `BMCR=0x2100` (autoneg off): PHY reported 10M HD, no traffic. Fixed to match the
   reference (autoneg, 10/100 only): now `PHYSR=0x311C 100M FD`, `ANLPAR=C5E1`.
4. A one-time ARP probe from the FPGA incremented the MAC TX counter (TX=1) but the host did not learn the
   board MAC (`ip neigh show` stayed INCOMPLETE/FAILED). Probe code was removed again.
5. Host side: wired link 1000M full to the switch, host pings to 192.168.1.1 work. The IP of the firmware is
   **192.168.1.50** (not .10 from old docs; the old log line `ping 192.168.1.10` is wrong).
6. `docs/dev_status_2026-10-08.md` says ping worked with the TSE MAC build (19:17) and broke when the T20
   bridge was added: RX frames with bit errors (`C4.AC.01.FF` instead of `C0.A8.01.FF`, RXD2 looks wrong),
   suspected crosstalk from `T20_CLK9` (GPIOL_72, next to `F2_RXC` GPIOL_73). Current firmware leaves CLK9 off
   after the self-test, so this is not the whole explanation here.
7. RTL8211F delays: TX delay = page 0xd08 reg 0x11 bit 8, RX delay = page 0xd08 reg 0x15 bit 3 (Linux driver
   convention). The reference firmware only writes reg 0x11 bits 8 and 3. Board strap values read back:
   `TXCR(0x11)=0x018B`, `RXCR(0x15)=0x0000`.
8. **MDIO delay sweep (C only, no resynthesis)**: `rgmii_delay_sweep()` in `main.c` tries TXDLY/RXDLY in
   {1,1},{1,0},{0,1},{0,0}, each with a PHY loopback test (BMCR=0x6100, 8 frames) and 2 s of live LAN traffic.
   Result: **every combination gave LOOPBACK_RX=0 and LIVE_RX=0**; the sticky CRC flag was set (and stays
   set until a valid frame arrives, so it is not per-combination). Conclusion: delay settings alone do
   not fix it. The loopback result also means either MAC TX -> PHY or PHY -> MAC RX is broken.
9. UART output lines `[ETH] BMSR=... RX=.. TX=.. FCS=.. FIFO_ST=0004` show the counters once per second
   (FIFO_ST=0004 means only link_up; `FCS` now shows the frames-ended counter of the diagnostic block).

## 4. Diagnostic hardware just added (build was running when this was written)

`eth_mac_100m.sv` (end of the module, own logic, RX engine untouched) adds read-only APB registers:

| Offset | Read | Write |
|---|---|---|
| 0x20 | [0] armed, [1] capture done | [0] arm (write 0 then 1 to re-arm) |
| 0x24 | capture sample at index (10 bit) | capture read index [7:0] |
| 0x28 | [31:16] RXC tick counter, [15:0] RXCTL rising edges | |
| 0x2C | [31:16] SFD hits, [15:0] frames ended | |
| 0x30 | CRC register of last ended frame (good frame = 0xDEBB20E3) | |
| 0x34 | byte count of last ended frame | |

Capture: 256 samples starting at the first RXCTL high after arming. Sample word =
`{neg_ctl, neg_d[3:0], pos_ctl, pos_d[3:0]}` (falling-edge sample half a clock before the rising-edge sample).

`eth_rx_diag()` in `main.c` (called after PHY init, before the sweep) prints:
`RXC/100us=` (expect about 0x09C4 for 25 MHz), `CTLEDGES`, `SFD`, `ENDED`, `LASTLEN`, `LASTCRC`, then three
captures of 128 samples as `NN:PP` (hex of `{ctl,d}` at falling : rising edge).

## 5. Next steps (what the next agent should do)

1. Wait for / check the diagnostic build: `tail /tmp/build_diag.log` (or `T120F324/outflow/T120_MALM.timing.rpt`).
   If the log is gone, rerun `bash FPGA_code/scripts/build_t120_fpga.sh` (~25 min) from `FPGA_code`.
   Check the timing guard output: the added `negedge` capture adds a half-cycle path in the `F2_RXC` domain.
   If it fails, reduce the diagnostic (drop the negedge sample) instead of touching the RX engine.
2. Start the UART capture BEFORE flashing so the boot output is not missed, e.g. run
   `python3 FPGA_code/scripts/flash_and_listen.py` (18 s only: the new firmware prints diagnostics early, but the
   sweep takes about 30 s; use a longer capture of `/dev/ttyACM0` at 115200 8N1, passive read only).
3. Interpret:
   * `RXC/100us` about 0x09C4 -> `F2_RXC` alive. 0 -> RXC pin/PHY clock problem.
   * Preamble should show `15:15` (or `1x`) repeated and then a `1D`-type SFD; compare falling vs rising sample
     (RGMII 10/100 should carry the nibble on the rising edge; check whether the falling sample differs).
   * If the nibble stream looks right but `LASTCRC != DEBBnnE3`: look at nibble order / CRC / sampling edge.
   * If bits are flipped (like RXD2): check RXD pin mapping/placement and crosstalk, try other pin assignments.
4. Candidate fixes after the capture: sample RX on the falling edge or with a PLL phase-shifted clock, register
   RX pins in IO cells (DDIO/`is_register`), different `F2_RXD*` pin mapping, TXC phase (TX side is still unverified:
   run a host `sudo tcpdump -ni enp2s0 -e 'ether src 00:12:34:56:78:9a'`).
5. Do not run synthesis while using `flash_soc.py`: both use `T120F324/outflow` and `work_pnr`.

## 6. Handy commands

```bash
cd /home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4
python3 FPGA_code/scripts/program_t120.py --scan          # JTAG check (IDCODE 0x00220A79)
python3 FPGA_code/scripts/flash_soc.py                    # firmware only: compile + patch BRAM + JTAG program
ping -c 5 -W 1 -I enp2s0 192.168.1.50                     # host side test
ip neigh show to 192.168.1.50 dev enp2s0                  # ARP state of the board
sudo tcpdump -ni enp2s0 -e 'arp or ether host 00:12:34:56:78:9a'   # needs sudo (user must run it)
```

UART: `/dev/ttyACM0`, 115200 8N1, passive read only (FPGA TX to host). Efinity: `/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2`.
Rules: see `.agents/skills/t120-soc-debug-strategy` and `t120-systematic-debug-protocol` (change one variable at a time).
