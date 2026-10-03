# Instruction for AI Agent: Remote Update & Boot System (T120 Master / T20 Slave)

## 1. System Overview
This project establishes an automated CI/CD flow for two Efinix FPGAs (T120 and T20). The T120 acts as a network gateway and Master. The T20 acts as a slave and compute node (Analog Matrix Computation). 
The objective is to enable the generation and deployment of new bitstreams for the T20 over the network (TCP/IP) to the T120, which will forward them to the T20 for asynchronous reprogramming using the Efinix "Internal Reconfiguration" (Remote Update) feature.

### Physical Constraints
* **JTAG:** Permanently connected to the T120 only. The T20 is programmed manually via JTAG exactly once with a "Golden Image" located at flash address `0x000000`.
* **Custom Bus:** Used for communication between the T120 (Master) and T20 (Slave). It consists of GPIOs defined in `T120_MALM.peri.xml` (e.g., `TX11_T20_N1`, `RX00_T20_N1`, `T20_CLK9`, etc.).
* **Patch Wire (Reset):** One GPIO from the T120 is physically wired to the T20's `CRESET_N` pin to allow hardware resets.

---

## 2. Architecture: T120 (Master)
The T120 contains a Sapphire SoC responsible for handling network traffic and acting as a bridge to the T20.
* **Network:** Configure a lightweight TCP/IP stack (e.g., lwIP) utilizing the designated Ethernet pins (`F2_MDC`, `F2_MDIO`, `F2_RXD0-3`, `F2_TXD0-3`).
* **Server Endpoint:** Open a TCP port (e.g., 8080) to receive two types of payloads/commands from the development environment:
  1. `CMD_JUMP`: Command the T20 to boot the Application Image.
  2. `CMD_UPDATE`: Receive a `.hex` bitstream payload for the T20.
* **Bus Communication:** Implement software drivers to send commands and stream bitstream data over the custom bus to the T20.
* **Failsafe Control:** The T120 must be able to pull the T20's `CRESET_N` pin low for at least 10 ms and then release it high to force the T20 to fall back to its Golden Image in case of failure.

---

## 3. Architecture: T20 (Slave / Golden Image)
This code resides permanently in the T20's SPI flash at address `0x000000`. It contains a minimal Sapphire SoC with no analog payload logic to maximize available space for the analog matrix and Hadamard encoding.

* **Standby Mode:** Upon boot, the Golden Image starts and *always* waits for instructions from the T120 via the custom bus.
* **Bitstream Reception:** Upon receiving `CMD_UPDATE`, the T20 reads the data over the bus and writes it to its local SPI flash at the designated "Application Image 1" address (e.g., `0x100000`).
* **Internal Reconfiguration:** 
  The project must instantiate the Efinix hardware block `CONFIG_CTRL0` within the T20. In `T120_MALM.peri.xml`, these signals are defined as:
  - `cfg_CBSEL` (Selects the target flash address for reconfiguration).
  - `cfg_ENA` (Enable signal for the reconfiguration interface).
  - `cfg_CONFIG` (Triggers the reconfiguration sequence).
  - `cfg_ERROR` (Status flag indicating a configuration error).

When the T20 receives the `CMD_JUMP` command from the T120, the SoC must drive `cfg_CBSEL` to the application address, set `cfg_ENA` = 1, and pulse `cfg_CONFIG` high to force the FPGA to reload itself.

---

## 4. Workflow / State Machine (To be implemented in C for the SoCs)

### Normal Boot
1. The entire system powers on.
2. The T20 *always* boots the Golden Image at address 0x000000.
3. The T120 boots its SoC and initializes the TCP/IP stack.
4. The T120 sends the `CMD_JUMP` command to the T20 via the custom bus.
5. The T20's Golden Image triggers `CONFIG_CTRL0` and loads the Application Image.
6. (If the Application Image is corrupt, the Efinix hardware will fail 6 times and automatically fall back to the Golden Image, setting `cfg_ERROR` to 1. The Golden Image can then report the corrupt state back to the T120).

### Remote Update (Over-The-Air)
1. The AI agent sends a new T20 `.hex` file to the T120's IP address.
2. The T120 pulls the T20's `CRESET_N` low and then high to guarantee the T20 is running the Golden Image and is ready.
3. The T120 sends `CMD_UPDATE` followed by the bitstream data over the bus.
4. The T20 Golden Image writes the received data to the SPI flash.
5. Once writing and verification are complete, the T120 sends `CMD_JUMP`.
6. The T20 reloads with the new AI-generated code.

---
**Task for AI:** Generate the C code for the Sapphire SoCs (for both the T120 and the T20 Golden Image) that implements this logic, along with the necessary Verilog modules to handle the custom bus communication and the `CONFIG_CTRL0` instantiation.