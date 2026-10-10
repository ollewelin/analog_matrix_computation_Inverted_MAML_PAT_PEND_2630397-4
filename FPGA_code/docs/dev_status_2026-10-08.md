# Development Status Report: 2026-10-08

Project: Inverted MAML analog matrix computation (T120 master + T20 compute node).
Scope of this session: T120 Ethernet ping, T120 side of the inter-FPGA bridge, start of the T20 design.

---

## 1. Summary

| Area | Status |
|:---|:---|
| T120 Ethernet (RGMII 100M) ping | **Worked at the 19:17 build. Currently broken on the board** (see 2.3). Rebuild with the fix is running. |
| T120 inter-FPGA bridge RTL (H-bus + S-bus + CRESET) | **Implemented, simulation passes.** CRESET pulse and Hadamard sequencer verified on hardware. |
| Bridge spec / docs / C register header | Done |
| T20 design | **Started** (4 RTL modules written, not simulated, no top level / peri / SoC yet) |
| T20 golden image `.hex` for JTAG swap | **Not ready** |

---

## 2. T120 Ethernet

### 2.1 Ping fixed (19:17 build)
Root cause of "no ping" (TX counter stayed 0): the Efinix TSE MAC needs `tx_mac_aclk = 125 MHz` in all speed modes (UG), the project fed 25 MHz. Changes (committed in HEAD):
* `pll_inst2`: `PLL_125MHZ` (125 MHz) and `PLL_125MHZ_90DEG` (125 MHz, 90 degree shift).
* TXD0-3 / TXCTL registered DDIO pads on `PLL_125MHZ`; `F2_TXC` driven by the MAC TXC output via the 90 degree clock (as in the Efinix reference design).
* TX engine in `tsemac_axis_packet_fifo.sv` rewritten (correct valid/ready handshake).
* `const.sdc`: clocks for the 125 MHz domain.
* Result: `ping 192.168.1.50` 6/6, 0.3 ms. (Firmware IP is **192.168.1.50**, not .10.)
* Link stays 100M full duplex (forced by `BMCR=0x2100`). The 125 MHz clock does not by itself enable 1000M.

### 2.2 Known timing item (accepted)
`PLL_125MHZ -> PLL_125MHZ` setup slack is negative inside the encrypted TSE IP: -0.326 ns (19:17), -0.168 ns, then -0.763 ns (latest build). Accepted by the user, but it is growing; suspect if Ethernet misbehaves again.

### 2.3 Regression after the bridge was added (open issue)
After the bridge build, Ethernet stopped working:
* Build 2 (bridge, plain RX pins): RX frames with bit errors (`C4.AC.01.FF` instead of `C0.A8.01.FF`), RX/TX counters 0. The self-test left `T20_CLK9` running (pin `GPIOL_72`, adjacent to `F2_RXC` `GPIOL_73`).
* Build 3 (RX pins changed to registered DDIO like the reference): MAC delivers 1-byte all-zero frames. Wrong direction. A PHY RXDLY change (`0xd08` reg `0x15` bit 3) did not help.
* Diagnostics added to firmware: `[RXDUMP]` of the first received frames and the TSE FCS counter.
* **Action taken:** RX pins reverted to plain inputs (the config that worked at 19:17), firmware leaves `T20_CLK9` off after the self-test. Rebuild (build 4) was still in progress at the time of this report; **not yet flashed or tested.**
* Hypotheses to check next, in order: (1) crosstalk from `T20_CLK9` onto `F2_RXC`, (2) placement-dependent RX timing (no input-delay constraint on the RX pins), (3) another effect of the bridge build. Fallback: rebuild without the bridge to bisect.

---

## 3. T120 inter-FPGA bridge (done)

Spec: `FPGA_code/docs/t120_t20_bridge_spec.md`. Pins: `FPGA_code/docs/pinout_T120_T20.md`. Register header: `FPGA_code/sw/t120_master/include/t120_bridge_regs.h`.

**Requirements decided with the user**
1. The Hadamard path is **100 % hardware-synchronous** from T120 to T20. No processor code, no CRC, no handshake wait in the timing path. A 1-bit ACK is only a timing proof.
2. SoC debug, SPI flash update, trace and table loading are software (C) and may be jittery. They use a separate bus.
3. T20-side logic must be light (it also hosts a minimal Sapphire SoC).
4. The wires are split into two independent buses sharing one clock `T20_CLK9`.

**Implemented RTL** (`FPGA_code/T120F324/`)
| File | Function |
|:---|:---|
| `t120_inter_fpga_bridge.sv` | APB3 register map (base `0xF810_3000`), RAMs, glue |
| `t120_bridge_clkgen.sv` | `CLK9` generator (1.25-10 MHz) with launch/sample strobes |
| `t120_hbus_seq.sv` | Hadamard hardware sequencer: table BRAM, exact word spacing, ACK latency last/min/max monitor |
| `t120_sbus_tx.sv`, `t120_sbus_rx.sv`, `t120_sbus_xact.sv` | S-bus serialiser/receiver (CRC8) and command/ACK FSM with timeout |
| `t120_creset_controller.sv` | T20 `CRESET_N` level and pulse (default 12 ms) on pin `T120_LED1` |
| `top_level.sv`, `T120_MALM.xml` | integration; LED1 heartbeat removed; old `t120_t20_bus_apb3.sv` removed |

**Verification**
* Simulation `FPGA_code/T120F324/sim/run_sim.sh` (iverilog, behavioural T20): all tests pass. Hadamard word spacing exact at 10 MHz and 2 MHz, ACK latency constant (`W+3`), unaffected by concurrent S-bus traffic, S-bus request/response, CRC error, timeout with auto CRESET pulse.
* Hardware (T120 only, no T20 connected): bridge ID read OK, Hadamard run completes (`H_STATUS=02`), CRESET pulse OK (after fixing a bug where the pulse write cleared the level bit).
* T20 CRESET patch wire to `T120_LED1` is **not yet soldered/wired** (stated by the user).

**Pin allocation**
`TX11_P/N` = H_SYNC/H_DATA, `RX00_P` = H_ACK, `TX12_P/N` = S-bus TX (2 bit), `RX02/RX03_P/N` = S-bus RX (4 bit), `RX00_N`/`RX01_*` reserved.

---

## 4. T20 (started)

Findings
* The T20 `T20F256.peri.xml` was generated with directions guessed from net-name prefixes (T120 point of view). It must be corrected: `TX11/TX12` inputs, `RX00..RX03` outputs, `T20_CLK9` (`GPIOR_126_CLK9`) clock input.
* Hadamard output pins already exist: `H_M3_P1..8 / N1..8` (matrix M3, 8 rows) and `H_M8_P1..7 / N1..7` (matrix M8, 7 rows). Planned mapping: row k = word bit k-1; per row P/N independent (P: +1, N: -1, both 0: off).
* Sapphire SoC IP supports "Trion T20F256 Development Board" (DEVKIT option).

Written, **not yet simulated or built** (`FPGA_code/T20F256/`)
* `t20_hbus_rx.sv`: H-bus receiver, pad registers (apply at `R(S+W)`), ACK at `R(S+W+1)`.
* `t20_sbus_rx.sv`, `t20_sbus_tx.sv`: S-bus slave engines.
* `t20_hw_responder.sv`: hardware responder (status, Hadamard enable mask, static pattern) so the T20 can be brought up without a CPU.

---

## 5. Next steps

1. Flash build 4, check `[RXDUMP]`, TSE counters, ping. If still broken: bisect (build without bridge).
2. Finish T20: top level, peri/SDC fixes, joint T120+T20 simulation, build, golden `.hex`.
3. Then the user swaps JTAG to the T20, programs the golden image, swaps back to the T120.
4. Add the minimal Sapphire SoC on T20 (flash writer, `CONFIG_CTRL0` jump, trace) and the T120 C drivers.
5. Small doc fixes owed in the bridge spec: T20 ACK timing (pads at `R(S+W)`, ACK at `R(S+W+1)`), SEQ/OP byte layout (sequence `[7:4]`, opcode `[3:0]`), hardware-responder opcodes.

## 6. Repository state
Nothing from the bridge work is committed. The changes are in the working tree (modified: `top_level.sv`, `T120_MALM.xml`, `main.c`, docs, skill note; new: bridge RTL, sim, T20 RTL, spec, register header).
