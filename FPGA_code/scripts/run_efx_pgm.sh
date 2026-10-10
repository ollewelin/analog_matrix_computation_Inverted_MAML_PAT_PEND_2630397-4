#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
export EFINITY_HOME="/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2"

cd "$BASE_DIR/FPGA_code/T120F324"
$EFINITY_HOME/bin/efx_pgm \
  --interface_designer_settings outflow/T120_MALM_or.ini \
  --periph outflow/T120_MALM.lpf \
  --family Trion \
  --device T120F324 \
  --source work_pnr/T120_MALM.lbf \
  --dest outflow/T120_MALM.hex \
  --mode=active --width=1 --enable_roms=smart \
  --spi_low_power_mode=on --io_weak_pullup=on \
  --oscillator_clock_divider=DIV8 --bitstream_compression=on \
  --enable_external_master_clock=off --active_capture_clk_edge=posedge \
  --jtag_usercode=0xFFFFFFFF --release_tri_then_reset=on
