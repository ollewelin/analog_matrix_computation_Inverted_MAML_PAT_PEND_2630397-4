1. Watch Overall Compilation Log

To see the main Efinity compilation stages (Synthesis, Placement, Routing, Bitstream generation):

tail -f /home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324/outflow/T120_MALM.log

2. Watch Place & Route Details

While the P&R engine is working on the logic cells and timing:
tail -f /home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324/work_pnr/T120_MALM.pnr.log

3. Read the Live Debug UART Output (/dev/ttyACM0)

picocom -b 115200 /dev/ttyACM0
# or with screen:
screen /dev/ttyACM0 115200
# or with python/cat:
stty -F /dev/ttyACM0 115200 raw -echo && cat /dev/ttyACM0