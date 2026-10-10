Hardware Bring-Up and Known Issues
Board Version: v1.3.2 (Released: 2026-09-04)
For hardware board version 1.3.2, the following hardware fixes must be applied first before testing or programming:

Hardware Bug Fixes
2026-09-30 (Critical): RDX2 goes to the CSI pin on the T120. If set to a pull-down, it forces JTAG into daisy-chain mode. Change this to a pull-up instead for single-mode JTAG.
2026-09-30 (Critical): LED1 resistor connects to the CSI pin on the T20. If set to a pull-down, it forces JTAG into daisy-chain mode. Change this to a pull-up instead for single-mode JTAG.
2026-09-30: Missing input net: T120_CRESET_N.
2026-10-07: Ethernet PHY magnetics center-tap: The 0-ohm resistor to GND should be replaced with a 10 nF capacitor to GND.

Current Firmware Status (Bring-Up Phase)

NOTICE:
This 
T120_MALM.bin
T120_MALM.hex
files

The current binary and hex files (T120_MALM.bin and T120_MALM.hex) are strictly intended for the initial bring-up TCP/IP ping test. They do not have the final, required timing closure yet, and the rest of the target system functionality is not fully implemented at this stage.

Initial Ping Test Verification

Successful response from the initial bring-up build (192.168.1.50):

ping 192.168.1.50
PING 192.168.1.50 (192.168.1.50) 56(84) bytes of data.
64 bytes from 192.168.1.50: icmp_seq=1 ttl=64 time=0.288 ms
64 bytes from 192.168.1.50: icmp_seq=2 ttl=64 time=0.327 ms
64 bytes from 192.168.1.50: icmp_seq=3 ttl=64 time=0.319 ms
^C
--- 192.168.1.50 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2083ms
rtt min/avg/max/mdev = 0.288/0.311/0.327/0.016 ms

