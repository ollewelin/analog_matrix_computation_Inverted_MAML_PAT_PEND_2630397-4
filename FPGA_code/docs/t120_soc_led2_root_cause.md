# T120 Sapphire SoC – Why T120_LED2 Never Blinked (Root Cause Report)

Date: 2026-10-03
Board: Trion T120F324, Sapphire RISC-V SoC (`RISC_mini`), firmware `FPGA_code/sw/t120_master`

## Symptom
- `T120_LED1` (hardware counter on `pll_clk_50Mhz`) blinked fine, so the PLL and bitstream were OK.
- `T120_LED2` (driven by SoC `gpio_out[0]`) stayed constant HIGH or constant LOW. Which one depended on the build. It never blinked.

## Root cause 1 (main): the bitstream had the wrong program in SoC RAM
`ip/RISC_mini/RISC_mini.v` fills the 128 KB on-chip RAM at synthesis time:

```verilog
$readmemb("EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol0.bin", ram_symbol0);
... symbol1..3
```

The path is **relative**. Efinity synthesis (`efx_run_map.py`) runs with
`--dir .../FPGA_code/T120F324/ip/RISC_mini`, so the files are read from
**`FPGA_code/T120F324/ip/RISC_mini/`**.

We only copied the compiled firmware into `FPGA_code/T120F324/` and `work_syn/`:

| Location | First byte of symbol0 | Content |
|---|---|---|
| `T120F324/`, `work_syn/` | `00110111` (0x37, `lui sp,0xF9020`) | our LED-blink firmware |
| **`ip/RISC_mini/`** (actually used) | `10010111` (0x97, `auipc`) | old image, not our firmware |

So every bitstream ran some old program, never our `main.c`. The CPU ran that code and
left `gpio[0]` at a fixed level, which is why LED2 changed between builds but never toggled.

**Fix:** [`FPGA_code/scripts/build_t120_fpga.sh`](../scripts/build_t120_fpga.sh) now copies
`sw/t120_master/rom/*ram_symbol*.bin` into `T120F324/`, `work_syn/` **and `ip/RISC_mini/`**
before every compile. It then prints the first firmware word, which must be:

```
11111001 00000010 00000001 00110111   (= 0xF9020137, lui sp,0xF9020)
```

## Root cause 2: SoC held in reset by a dead clock
Old `top_level.sv`:

```verilog
logic [28:0] major_reset_cnt = '0;
always_ff @(posedge T120_GCLK) ...          // no clock was arriving on this net
.io_asyncReset (~major_reset_cnt[28]),      // held at 1 forever, so the SoC stayed in reset
```

From the Sapphire datasheet (`riscv-sapphire-ds-v6.1.pdf`, "Resets"): `io_asyncReset` is an
**active-high** asynchronous reset for the whole SoC. Code only runs after `io_systemReset` goes low.

**Fix (now in `top_level.sv`):**
```verilog
.io_asyncReset (1'b0),        // SoC releases its own reset internally, as in the Efinix reference design
assign T120_LED1 = led1_hw_toggle;   // 2 Hz hardware counter on sys_clk
assign T120_LED2 = gpio_out[0];      // driven by firmware
```

## Root cause 3 (process): edits to top_level.sv got overwritten
`top_level.sv` was open in the editor. An older copy in the editor was saved over the agent's
edits, so the `io_asyncReset` fix disappeared and a build ran with the old reset logic.
**Rule:** after the agent edits a file, reload it in the editor. Don't save an older copy over it.

## Note: reset naming in top_level.sv (works, but the names are misleading)
- `sys_rst_n` is connected to `io_systemReset`, which is **active-high** (1 = in reset). The `_n` suffix is wrong.
- `sys_rst_n_inv = ~sys_rst_n` is therefore an **active-low** reset, which is what the APB slaves'
  `presetn` expects. The behavior is correct; only the name is misleading.

## Verification checklist after flashing
1. Build log prints `0xF9020137` as the first firmware word (bits shown above).
2. `T120_LED1` blinks at 2 Hz.
3. `T120_LED2` blinks (~1–2 Hz, set by the C loop `for (i < 2500000)`).

## Rebuild + flash
```bash
make -C FPGA_code/sw/t120_master
(cd FPGA_code/sw/t120_master && EFINITY_HOME=/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2 python3 tool/binGen.py -b build/t120_master.bin -s 131072)
FPGA_code/scripts/build_t120_fpga.sh
python3 FPGA_code/scripts/program_t120.py
```

