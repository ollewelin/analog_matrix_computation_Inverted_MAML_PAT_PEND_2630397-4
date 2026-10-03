#!/bin/bash
# =============================================================================
# run_sim.sh - MDIO Master Simulation Runner
# =============================================================================
# Usage:
#   ./run_sim.sh               # Default: compile and run with iverilog
#   ./run_sim.sh --view        # Run and open waveforms in GTKWave
#   ./run_sim.sh --clean       # Clean generated files
#   ./run_sim.sh --verilator   # Compile/run with Verilator instead
# =============================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$SCRIPT_DIR/sim"
TOOL="${1:-iverilog}"  # Default tool

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

echo -e "${YELLOW}=== MDIO Master Simulation ===${NC}"
echo "Directory: $SCRIPT_DIR"
echo "Tool: $TOOL"

# =============================================================================
# Function: Clean simulation files
# =============================================================================
clean_sim() {
    echo -e "${YELLOW}Cleaning simulation artifacts...${NC}"
    rm -rf "$SIM_DIR" *.vvp *.vcd obj_dir waveforms.vcd *.o
    echo -e "${GREEN}Clean complete.${NC}"
    exit 0
}

# =============================================================================
# Function: Compile and run with iverilog
# =============================================================================
run_iverilog() {
    echo -e "${YELLOW}Compiling with iverilog...${NC}"
    
    if ! command -v iverilog &> /dev/null; then
        echo -e "${RED}ERROR: iverilog not found!${NC}"
        echo "Install with: sudo apt-get install iverilog gtkwave"
        exit 1
    fi
    
    mkdir -p "$SIM_DIR"
    
    # Compile SystemVerilog files
    iverilog -g2009 -o "$SIM_DIR/mdio_sim.vvp" \
        "$SCRIPT_DIR/tb_mdio_master.sv" \
        "$SCRIPT_DIR/mdio_master.sv"
    
    echo -e "${GREEN}Compilation successful!${NC}"
    echo -e "${YELLOW}Running simulation...${NC}"
    
    # Run simulation with VCD output
    cd "$SIM_DIR"
    vvp mdio_sim.vvp -vcd waveforms.vcd
    
    echo -e "${GREEN}Simulation complete!${NC}"
    echo -e "Waveforms saved to: $SIM_DIR/waveforms.vcd"
    
    cd "$SCRIPT_DIR"
}

# =============================================================================
# Function: Compile and run with Verilator
# =============================================================================
run_verilator() {
    echo -e "${YELLOW}Compiling with Verilator...${NC}"
    
    if ! command -v verilator &> /dev/null; then
        echo -e "${RED}ERROR: Verilator not found!${NC}"
        echo "Install with: sudo apt-get install verilator"
        exit 1
    fi
    
    mkdir -p "$SIM_DIR"
    cd "$SIM_DIR"
    
    # Generate Verilator C++ testbench wrapper
    cat > tb_wrapper.cpp << 'VERILOG_EOF'
#include "Vmdio_master.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

int main(int argc, char** argv) {
    VerilatedContext* contextp = new VerilatedContext;
    contextp->commandArgs(argc, argv);
    
    Vmdio_master* top = new Vmdio_master(contextp);
    VerilatedVcdC* tfp = new VerilatedVcdC;
    top->trace(tfp, 99);
    tfp->open("waveforms.vcd");
    
    top->clk = 0;
    top->rst_n = 0;
    
    // Reset sequence
    for (int i = 0; i < 10; i++) {
        contextp->timeunit(-9);
        top->clk = !top->clk;
        top->eval();
        tfp->dump(contextp->time());
    }
    
    top->rst_n = 1;
    
    // Run simulation for 100k clock cycles
    for (int i = 0; i < 200000; i++) {
        if ((i % 2) == 0) top->clk = !top->clk;
        top->eval();
        if (contextp->time() % 100000 == 0) {
            printf("Time: %lu\n", contextp->time());
        }
        tfp->dump(contextp->time());
        contextp->timeInc(5);
    }
    
    tfp->close();
    top->final();
    delete top;
    delete tfp;
    return 0;
}
VERILOG_EOF
    
    verilator -sv --trace --exe tb_wrapper.cpp \
        "$SCRIPT_DIR/tb_mdio_master.sv" \
        "$SCRIPT_DIR/mdio_master.sv"
    
    cd obj_dir
    make -f Vmdio_master.mk
    ./Vmdio_master
    
    cd "$SCRIPT_DIR"
    echo -e "${GREEN}Verilator simulation complete!${NC}"
    echo "Waveforms saved to: $SIM_DIR/obj_dir/waveforms.vcd"
}

# =============================================================================
# Function: View waveforms
# =============================================================================
view_waveforms() {
    VCD_FILE="$SIM_DIR/waveforms.vcd"
    
    if [ ! -f "$VCD_FILE" ]; then
        echo -e "${RED}ERROR: Waveform file not found: $VCD_FILE${NC}"
        echo "Run simulation first without --view flag"
        exit 1
    fi
    
    if ! command -v gtkwave &> /dev/null; then
        echo -e "${RED}ERROR: gtkwave not found!${NC}"
        echo "Install with: sudo apt-get install gtkwave"
        exit 1
    fi
    
    echo -e "${YELLOW}Opening waveforms in GTKWave...${NC}"
    gtkwave "$VCD_FILE" &
}

# =============================================================================
# Main Logic
# =============================================================================

case "$1" in
    --clean)
        clean_sim
        ;;
    --view)
        TOOL="iverilog"
        run_iverilog
        view_waveforms
        echo -e "${GREEN}Done!${NC}"
        ;;
    --verilator)
        run_verilator
        ;;
    *)
        run_iverilog
        echo ""
        echo -e "${YELLOW}To view waveforms, run:${NC}"
        echo "  gtkwave $SIM_DIR/waveforms.vcd"
        echo ""
        echo -e "${YELLOW}Or use:${NC}"
        echo "  ./run_sim.sh --view"
        ;;
esac
