---
name: t120-soc-debug-strategy
description: Hierarchical debugging protocol and decision ladder for Trion T120 Sapphire SoC. Enforces priority ordering from Ethernet/TCP-IP to UART landmark sniffing (/dev/ttyACM0), LED observation, down to OpenOCD/ILA as a last resort.
---

# T120 SoC Hierarchical Debugging Strategy & Runbook

This guide specifies the strict priority ladder and diagnostic protocol for the Trion T120 Sapphire SoC development flow.

---

## 1. Strict Priority Hierarchy

When diagnosing or verifying the target board, ALWAYS follow this 4-tier decision ladder:

```
+------------------------------------------------------------------+
|  Priority 1: Ethernet / TCP/IP Debugging                         |
|  - Active once the TCP/IP stack is alive.                        |
|  - ICMP Ping (192.168.1.10), TCP Socket (port 8080), Wireshark.  |
+------------------------------------------------------------------+
                               | (If network is down / not yet up)
                               v
+------------------------------------------------------------------+
|  Priority 2: Passive UART Landmark Sniffing (/dev/ttyACM0)       |
|  - Mandatory autonomous observability until TCP/IP ping works.   |
|  - Read landmark strings from APB3 uart_mini (Pin F13 @ 9600b).  |
|  - ALWAYS verify UART trace via flash_and_listen.py after flash. |
|  - MANDATORY RULE: If UART trace capability is LOST, STOP and   |
|    report immediately to the user before attempting more changes!|
+------------------------------------------------------------------+
                               | (If UART data is missing / ambiguous)
                               v
+------------------------------------------------------------------+
|  Priority 3: Physical LED Observation (User Query)              |
|  - Ask user about LED status:                                    |
|    * LED1 = T20 CRESET_N patch wire (high = T20 released; no blink)|
|    * LED2 = Firmware-driven GPIO (landmark pulse count or 500ms).|
+------------------------------------------------------------------+
                               | (Only as an absolute last resort)
                               v
+------------------------------------------------------------------+
|  Priority 4: OpenOCD / GDB or Efinix Logic Analyzer (ILA)       |
|  - Use ONLY when all higher layers fail.                         |
|  - OpenOCD: Inspect register crash dumps (`mepc`, `mcause`, `sp`)|
|  - Logic Analyzer (ILA): Reserved for external PHY/HDL timing.   |
+------------------------------------------------------------------+
```

---

## 2. Priority 1: Ethernet & TCP/IP Debugging

Once the lwIP network interface is initialized and links at physical speed:
1. **Physical Link Status:**
   ```bash
   ethtool enp2s0
   ```
2. **ARP & ICMP Ping:**
   ```bash
   ping -c 3 -W 1 192.168.1.10
   ip neigh show dev enp2s0
   ```
3. **TCP Server Connectivity:**
   ```bash
   nc -zv -w 2 192.168.1.10 8080
   echo "STATUS" | nc 192.168.1.10 8080
   ```
4. **Packet Capture:**
   Monitor ARP/TCP packets using `tcpdump -i enp2s0 -nn host 192.168.1.10`.

---

## 3. Priority 2: Passive UART Landmark Sniffing (`/dev/ttyACM0`)

The firmware embeds landmark print calls (`dbg_print()`) at each critical initialization stage:
- `[Stage 1] Entered main(), GPIO configured`
- `[Stage 2] PHY config complete`
- `[Stage 3] lwIP init complete`
- `[Stage 4] Netif up`
- `[Stage 5] TCP Server listening`
- `[Heartbeat] T120 loop alive`

### Autonomous Sniffing Protocol:
1. **Passive Read Only:**
   - The hardware electrical line is strictly **FPGA TX $\rightarrow$ Sniffer / `/dev/ttyACM0` RX**.
   - Do NOT attempt to write or send data back to the FPGA over `/dev/ttyACM0`.
2. **Sniffing Script:**
   ```python
   import os, termios, select, time

   fd = os.open('/dev/ttyACM0', os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
   attrs = termios.tcgetattr(fd)
   attrs[4] = termios.B115200
   attrs[5] = termios.B115200
   attrs[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG)
   attrs[0] = attrs[1] = 0
   termios.tcsetattr(fd, termios.TCSANOW, attrs)
   termios.tcflush(fd, termios.TCIFLUSH)

   buf = bytearray()
   start = time.time()
   while time.time() - start < 3.0:
       r, _, _ = select.select([fd], [], [], 0.2)
       if r:
           b = os.read(fd, 256)
           if b: buf.extend(b)

   print(bytes(buf).decode('latin1', errors='replace'))
   os.close(fd)
   ```
3. **Inter-Character Pacing Delay (Crucial Lesson & Trap):**
   - When the RISC-V SoC runs at 50 MHz, transmitting bytes back-to-back without pause easily overruns USB bridges (like the Arduino ATmega16U2 on `/dev/ttyACM0`).
   - Symptoms of missing inter-character delay:
     * Terminal displays infinite repeating characters (e.g. `PPPPPPPPPPPP...`).
     * Host serial drivers miss stop bits and report framing errors.
   - Remedy: `uart_mini_tx_byte_blocking()` in `uart_mini_driver.h` includes a pacing delay:
     ```c
     for (volatile int i = 0; i < 50000; i++); // ~1 ms pause between characters
     ```

4. **Autonomous Execution:**
   - If UART landmarks are actively received, **do NOT query the user** about LEDs or CPU status. Continue autonomously using the landmarks to guide changes.

---

## 4. Priority 3: Physical LED Observation

If UART sniffing is silent or not yet connected:
- **T120_LED1:** Heartbeat removed. The pin is the patch wire to T20 `CRESET_N` (high = T20 released, low = T20 held in reset).
- **T120_LED2:** Driven by Sapphire SoC `gpio_out[0]` (`0xF800D004`).
  - Pulses corresponding to stage number during boot, then toggles at 500 ms in the main loop.
- **Rule:** Ask the user specifically about LED2 blink count or steady state only when UART telemetries are missing.

---

## 5. Priority 4: OpenOCD & Logic Analyzer (ILA)

Reserved strictly for deadlocks where no telemetry or network response is obtainable:
1. **OpenOCD / GDB:**
   - Run in batch non-interactive mode.
   - Halt briefly to extract `pc`, `mepc`, `mcause`, `sp`.
   - Never micro-step in loops.
2. **Efinix Logic Analyzer (ILA):**
   - Strictly mutually exclusive with OpenOCD (same physical FTDI chip).
   - Reserved for complex external peripheral timing (e.g. RGMII DDR, external SPI/MAML bus) in later project phases outside the SoC core.
