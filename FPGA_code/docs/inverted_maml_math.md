# Inverted MAML & Fast Walsh-Hadamard Transform (FWHT) Specification

**Document Reference:** `INVERTED-MAML-AIMC-SPEC-V4`  
**Patent Status:** Patent Pending (SE 2630397-4)  
**Hardware Platforms:** Efinix Trion T120 (Master / Orchestration) & Trion T20 (Dedicated Compute Node)

---

## 1. Mathematical Definition

### 1.1 Inverted MAML Framework & Atomic Triad
Conventional analog In-Memory Computing (AIMC) architectures suffer from non-deterministic physical perturbations:
- Continuous voltage/charge leakage on capacitive storage nodes governed by time-variant RC discharge curves.
- Transistor threshold voltage variations (\(V_{th}\) mismatch) and thermal drift.
- Conductance degradation across operational cycles.

Standard Model-Agnostic Meta-Learning (MAML) adapts neural network weights across external tasks in digital domains. **Inverted MAML** reverses this paradigm: the task space is internal and physical. The meta-objective is to discover an initial parameter configuration \(W_0\) that remains robust across the hardware's continuous physical state transitions and thermodynamic decay:
$$\min_{W_0} \sum_{\tau \in \mathcal{T}_{\text{hardware}}} \mathcal{L}_{\tau}(f(X; W_{\tau}))$$

#### The Hybrid Atomic Triad Substrate
The analog computing core is organized into an **Atomic Triad** comprising three interleaved physical matrices:
1. **Primary Computation Matrix (\(M_{33}\)):** Statically programmed target weights representing the primary logical computation.
2. **First-Stage Compensation Matrix (\(M_3\)):** Upstream analog adaptation layer compensating for initial non-linearities and input stage drift.
3. **Second-Stage Compensation Matrix (\(M_8\)):** Downstream analog adaptation layer coupled via non-linear activation functions to compensate for global column error and output offsets.
4. **Asymmetric Reference Clock Cells:** Physical reference nodes designed with intentionally shortened RC time constants. Because reference cells discharge significantly faster than computational cells, their steep decay acts as an analog proprioceptive clock, breaking physical symmetry and providing an explicit temporal state coordinate.

---

### 1.2 Stratified Time-Slice Batching
Due to the digital-to-analog programming interval bottleneck, weights can only be refreshed periodically. During the continuous discharge cycle \(t \in [t_0, t_{\text{refresh}}]\), the physical state decays. Point-in-time gradient evaluation causes severe phase lag and limit-cycle oscillation.

The discharge window is partitioned into **10 uniform Strata**:
- **Strata 1–3 (High Energy Domain):** Captures sub-threshold initialization anomalies and peak transient leakage immediately after refresh.
- **Strata 4–7 (Linearized Decay Domain):** Evaluates the quasi-linear region where steady-state computation spends the highest duty cycle.
- **Strata 8–10 (Asymptotic Tail Domain):** Captures the compressed low-energy asymptotic decay near thermal noise floors.

During a single operational discharge cycle, local differential gradients \(\nabla \mathcal{L}(t_i)\) are sampled across strata without rewriting weights. The stratified mini-batch update is computed as a discrete integration:
$$\nabla W = \frac{1}{10} \sum_{i=1}^{10} \nabla \mathcal{L}(t_i)$$
*Operational Note (Breakthrough Mode):* In peak signal conditions, sampling at maximum row signal amplitude (\(t \approx 0.5\,\text{ms}\) before significant RC decay) maximizes signal-to-noise ratio (SNR) through steep \(\tanh\) nonlinearities, yielding rapid convergence.

---

### 1.3 Fast Walsh-Hadamard Transform (FWHT / FHT)

To extract individual cell partial derivatives \(\frac{\partial z_j}{\partial W_{i,j}}\) without sequential row scanning (which incurs high latency and drift during the scan itself), the system uses orthogonal multiplexed excitation.

#### Hadamard Matrix Definition
The Sylvester construction of the Hadamard matrix of order \(2^k\) is defined recursively:
$$H_1 = [1]$$
$$H_{2^k} = \begin{bmatrix} H_{2^{k-1}} & H_{2^{k-1}} \\ H_{2^{k-1}} & -H_{2^{k-1}} \end{bmatrix}$$

For an \(N \times N\) matrix (where \(N = 2^k\)):
$$H_N^T H_N = N \cdot I_N$$

#### Butterfly Computation
The Fast Walsh-Hadamard Transform computes \(\mathbf{y} = H_N \mathbf{x}\) in \(\mathcal{O}(N \log_2 N)\) additions and subtractions without multiplications.

For stage \(s \in \{1, \dots, \log_2 N\}\) with stride \(2^{s-1}\) and block length \(2^s\):
For each block index \(b\) and offset \(j \in [0, 2^{s-1}-1]\):
$$u = x[b \cdot 2^s + j]$$
$$v = x[b \cdot 2^s + j + 2^{s-1}]$$
$$x_{\text{next}}[b \cdot 2^s + j] = u + v$$
$$x_{\text{next}}[b \cdot 2^s + j + 2^{s-1}] = u - v$$

#### Sensitivity Decoupling
By modulating rows simultaneously with Walsh sequences \(H_N\) and capturing column ADC responses \(Y_{\text{col}}\), the local derivatives are decoded:
$$\mathbf{g}_{\text{row}} = \frac{1}{N} H_N \cdot Y_{\text{col}}$$
This lowers the measurement noise floor by \(\sqrt{N}\) relative to sequential excitation.

---

## 2. Fixed-Point Arithmetic Specification

All arithmetic on the digital controllers (T120 RISC-V and T20 hardware pipelines) operates strictly in fixed-point to ensure deterministic latency and zero floating-point emulation overhead.

| Parameter | Type / Format | Range | Scaling Factor | Description |
|:---|:---|:---|:---|:---|
| **Weight Values (\(W\))** | Signed `Q1.14` (16-bit) | \([-2.0, +1.99994]\) | \(2^{14} = 16384\) | Stored weights and DAC programming targets |
| **Input Vectors (\(X\))** | Signed `Q1.14` (16-bit) | \([-2.0, +1.99994]\) | \(2^{14} = 16384\) | Normalized input activations |
| **ADC Samples** | Signed `Q1.11` (12-bit sign-extended to 16-bit) | \([-1.0, +0.9995]\) | \(2^{11} = 2048\) | Physical ADC conversion outputs |
| **FWHT Intermediate** | Signed `Q8.14` (24-bit / 32-bit accum) | \([-128.0, +127.99]\) | \(2^{14}\) | Prevents overflow across \(\log_2 N\) butterfly stages |
| **Gradients (\(\nabla W\))**| Signed `Q1.14` (16-bit) | \([-2.0, +1.99994]\) | \(2^{14}\) | Decoded derivatives post-normalization |
| **Learning Rate (\(\alpha\))**| Unsigned `Q0.16` (16-bit) | \([0.0, 0.99998]\) | \(2^{16} = 65536\) | Step size multiplier |
| **Momentum (\(\beta\))**| Unsigned `Q0.16` (16-bit) | \([0.0, 0.99998]\) | \(2^{16} = 65536\) | Velocity damping factor (typically 0.95 = 62259) |

### Overflow & Saturation Rules
1. **Symmetric Saturation:** When an intermediate result exceeds \([ -2^{B-1}, 2^{B-1}-1 ]\), it is clamped to `INT_MAX` or `INT_MIN`. Wraparound arithmetic is strictly prohibited.
2. **Butterfly Bit Growth:** For \(N\)-point FWHT, dynamic range expands by \(\log_2 N\) bits. Accumulators must reserve \(\lceil \log_2 N \rceil\) guard bits prior to final right-shifting by \(\log_2 N\).
3. **Rounding:** Convergent rounding (round to nearest even) is applied during right-shifts to eliminate cumulative DC bias across successive MAML cycles.

---

## 3. Inter-FPGA Bus Transaction Protocol

Per `FPGA_code/docs/pinout_T120_T20.md`:
- **Master:** T120 (drives `T20_CLK9`, 4-bit TX data).
- **Slave / Compute:** T20 (drives 8-bit RX data).
- **Physical Pins:**
  - `T20_CLK9`: Bus clock (10 MHz to 25 MHz synchronous clock).
  - `TX[3:0]`: `TX11_T20_P1`, `TX11_T20_N1`, `TX12_T20_P1`, `TX12_T20_N1`.
  - `RX[7:0]`: `RX00_T20_P1/N1`, `RX01_T20_P1/N1`, `RX02_T20_P1/N1`, `RX03_T20_P1/N1`.

```
        T120 (Master)                            T20 (Compute)
   +--------------------+                    +--------------------+
   |                    |---- T20_CLK9 ----->|                    |
   |   Sapphire SoC     |---- TX[3:0] (4b) ->|   Custom Engine    |
   |   (TCP/IP, Boot)   |<--- RX[7:0] (8b) --|   (Analog Triad,   |
   |                    |                    |    FWHT Unit)      |
   +--------------------+                    +--------------------+
```

### 3.1 Packet Framing & Nibble Packing (TX Bus: T120 -> T20)
Because the TX bus is 4 bits wide, each byte is transmitted over 2 clock cycles:
- **Cycle 0:** High Nibble `TX[3:0] = Byte[7:4]`
- **Cycle 1:** Low Nibble `TX[3:0] = Byte[3:0]`

#### Standard Packet Structure
```
+---------------+---------------+---------------+--------------------+---------------+---------------+
| PREAMBLE (2B) |  OPCODE (1B)  | LENGTH (2B)   |   PAYLOAD (N B)    |   CRC16 (2B)  | POSTAMBLE(1B) |
|  0xAA  0x55   |  CMD_xxx      | Big-Endian    | Data bytes         | CCITT (0x1021)|     0x7E      |
+---------------+---------------+---------------+--------------------+---------------+---------------+
```

#### Supported Command Opcodes
| Opcode | Mnemonic | Description |
|:---|:---|:---|
| `0x01` | `CMD_UPDATE` | Stream bitstream data to write to T20 SPI Flash Application Slot |
| `0x02` | `CMD_JUMP` | Command T20 internal reconfiguration block to load Application Image |
| `0x03` | `CMD_RESET` | Soft reset of T20 compute pipeline |
| `0x10` | `CMD_SET_WEIGHTS` | Transfer fixed-point matrix weights (`Q1.14`) to T20 analog DAC drivers |
| `0x11` | `CMD_EXEC_INFERENCE` | Send input vector \(X\) and trigger analog MVM execution |
| `0x12` | `CMD_EXEC_MAML_CAL` | Trigger 10-strata Hadamard perturbation calibration sequence |
| `0x13` | `CMD_READ_STATUS` | Query T20 status, configuration error flags, and execution state |

### 3.2 Response Framing (RX Bus: T20 -> T120)
The RX bus is 8 bits wide (1 byte transferred per clock cycle):
```
+---------------+---------------+---------------+--------------------+---------------+---------------+
| PREAMBLE (2B) |  STATUS (1B)  | LENGTH (2B)   |   PAYLOAD (N B)    |   CRC16 (2B)  | POSTAMBLE(1B) |
|  0x55  0xAA   |  RESP_xxx     | Big-Endian    | Results / Telemetry| CCITT (0x1021)|     0x7E      |
+---------------+---------------+---------------+--------------------+---------------+---------------+
```

#### Status Codes
- `0x00`: `RESP_OK` (Success / Ack)
- `0x01`: `RESP_BUSY` (Analog calibration or flash operation in progress)
- `0x02`: `RESP_CRC_ERR` (Frame CRC mismatch)
- `0x03`: `RESP_CFG_ERR` (Hardware `CONFIG_CTRL0` error triggered)
- `0xFF`: `RESP_INVALID_CMD` (Unknown command)

---

## 4. Functional Partitioning: T120 vs. T20

```
+-----------------------------------------------------------------------------------+
|                                  T120 MASTER                                      |
|                                                                                   |
|  +-------------------------+    +-----------------------+    +-----------------+  |
|  |  Ethernet PHY & MAC     |    |  Sapphire RISC-V SoC  |    | SPI Flash / OTA |  |
|  |  (RGMII / RMII @ 8080)  |--->|  (lwIP TCP Server,    |--->| Reconfig Master |  |
|  +-------------------------+    |   MAML Outer Loop,    |    +-----------------+  |
|                                 |   Weight Storage)     |                         |
|                                 +-----------+-----------+                         |
|                                             |                                     |
+---------------------------------------------|-------------------------------------+
                                  4-bit TX    |    8-bit RX
                                  + T20_CLK9  v   (Custom Bus)
+-----------------------------------------------------------------------------------+
|                                  T20 COMPUTE                                      |
|                                                                                   |
|  +---------------------+    +-------------------------+    +-------------------+  |
|  | Bus De-packetizer   |--->| FWHT 16/32 Butterfly    |--->| Analog Matrix     |  |
|  | & HW Reconfig Ctrl  |    | Fast Transform Engine   |    | Core (M3, M8, M33)|  |
|  +---------------------+    +-------------------------+    +-------------------+  |
|                                                               |                   |
|                             +-------------------------+       |                   |
|                             | High-Speed Column ADCs  |<------+                   |
|                             | & Sample Buffer (10-Str)|                           |
|                             +-------------------------+                           |
+-----------------------------------------------------------------------------------+
```

### 4.1 T120 (Master Node) Responsibilities
1. **Network Connectivity:** Hosts Sapphire SoC running lwIP TCP/IP stack; serves remote update and control port 8080.
2. **Boot & Failsafe Orchestration:** Controls T20 `CRESET_N` physical line; handles fallback to Golden Image in case of CRC/config errors.
3. **Firmware & Bitstream Deployment:** Receives OTA updates over TCP and streams bitstreams across the 4-bit inter-FPGA link.
4. **MAML Outer-Loop Meta-Optimization:**
   - Computes learning rate decay and outer-loop updates.
   - Maintains authoritative weight parameter tables.
   - Evaluates system-level convergence and logs performance metrics.

### 4.2 T20 (Dedicated Compute Node) Responsibilities
1. **Analog In-Memory Computing Array Execution:**
   - Drives high-precision DACs for row activation of \(M_3, M_8, M_{33}\).
   - Manages sample-and-hold (S&H) timing across analog memory cells.
2. **Hardware Fast Walsh-Hadamard Transform Engine:**
   - Generates parallel Walsh sequences for simultaneous row excitation.
   - Performs pipelined multi-stage butterfly decoding on sampled column signals in real-time hardware.
3. **Discretized Stratification Buffering:**
   - Samples column outputs across the 10 defined temporal strata.
   - Performs localized gradient extraction directly in DSP blocks.
4. **Local Hardware Reconfiguration (`CONFIG_CTRL0`):**
   - Implements Golden Bootloader at Flash `0x000000`.
   - Reconfigures into dynamic application bitstreams at Flash `0x100000`.
