#!/bin/bash
# Simulates the T120 bridge against a behavioural T20 (iverilog).
set -e
cd "$(dirname "$0")"
SRC=..
iverilog -g2012 -o /tmp/tb_t120_bridge.vvp tb_t120_bridge.sv \
  $SRC/t120_bridge_clkgen.sv $SRC/t120_sbus_tx.sv $SRC/t120_sbus_rx.sv $SRC/t120_sbus_xact.sv \
  $SRC/t120_hbus_seq.sv $SRC/t120_creset_controller.sv $SRC/t120_inter_fpga_bridge.sv
vvp /tmp/tb_t120_bridge.vvp | head -60
rm -f tb_t120_bridge.vcd
