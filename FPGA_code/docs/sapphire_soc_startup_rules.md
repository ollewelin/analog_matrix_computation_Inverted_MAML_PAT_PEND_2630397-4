# Sapphire RISC-V SoC Architecture & Startup Rules (Trion T120)

> **MANDATORY REFERENCE FOR FUTURE SESSIONS / AGENTS**  
> Do **NOT** modify or replace startup files or BRAM update procedures without reading this document.

---

## 1. Golden Architecture Rules

### Rule 1: Reset Wiring (`top_level.sv`)
- **`io_asyncReset` must be tied to `1'b0`**:
  ```verilog
  RISC_mini u_sapphire_soc (
      .io_systemClk   (sys_clk),
      .io_systemReset (sys_rst_n),
      .io_asyncReset  (1'b0), // ALWAYS 1'b0 in logic!
  ```
  *Why:* `io_asyncReset` is an **active-high** reset. Sapphire SoC has an internal 64-cycle auto power-on reset sequencer (`systemCd_logic_holdingLogic_resetCounter`). Tying it to an external counter on a dead clock (like unclocked `T120_GCLK`) holds the entire CPU in permanent reset.

### Rule 2: Startup Sequence (`start_minimal.S`)
- Every bare-metal entry point **MUST** start with:
  ```assembly
  fence.i
  fence
  la   t0, default_trap_handler
  csrw mtvec, t0
  la   sp, _sp
  ```
  *Why:*
  1. **Instruction Cache Coherency**: Sapphire SoC has an enabled I-Cache. On power-up or memory update, `fence.i` invalidates stale cache tags. Without `fence.i`, instruction prefetch triggers an **Instruction Access Fault (mcause=0x1)** before reaching `main`.
  2. **Trap Vector**: `mtvec` defaults to `0x00000000`. Any unhandled trap or interrupt vectors into unmapped memory, hanging the CPU. Pointing `mtvec` to a parking loop prevents wild execution.
  3. **Stack Pointer**: Use `la sp, _sp` from the linker script rather than hardcoding arbitrary addresses to avoid misaligned stores (`mcause=0x6`).

### Rule 3: Fast Firmware Updates (3-Second Turnaround)
You do **NOT** need to run an 11-minute full place-and-route compile just to update firmware!
1. Compile C code: `make -C FPGA_code/sw/t120_master`
2. Generate memory symbols: `python3 tool/binGen.py -b build/t120_master.bin -s 131072`
3. Patch existing bitstream LBF: `python3 FPGA_code/scripts/test_bram_update_all.py`
4. Regenerate bit file: `efx_pgm` (takes 3.5 seconds)
5. Program FPGA: `python3 FPGA_code/scripts/program_t120.py`

### Rule 4: Synthesis RAM Image Locations
If you *do* run a full compile (`efx_run`), synthesis runs with `--dir ip/RISC_mini`. Therefore, `$readmemb` looks for the four symbol files in **`FPGA_code/T120F324/ip/RISC_mini/`** as well as `FPGA_code/T120F324/`. [`build_t120_fpga.sh`](file:///home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/scripts/build_t120_fpga.sh) has been updated to copy them to all required directories automatically.

---

## 2. GPIO Memory Map
- Base: `0xF800D000`
- `GPIO_INPUT`: `0x00`
- `GPIO_OUTPUT`: `0x04`
- `GPIO_OUTPUT_ENABLE`: `0x08`
- `T120_LED2` is wired to `gpio_out[0]` (bit 0).
- `T120_LED1` (patch wire) | out | — | `T20_CRESET_N` | T20 hardware reset, active low (see §6). LED1 heartbeat removed |