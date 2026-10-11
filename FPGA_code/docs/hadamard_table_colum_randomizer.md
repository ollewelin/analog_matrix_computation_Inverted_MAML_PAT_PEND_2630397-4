# Two-Level Randomization Strategy for Analog IMC Calibration

This document outlines the dual-level stochastic sampling strategy for the inverted MAML calibration loop, utilizing Hadamard-coded perturbations. The objective is to decouple the physical hardware voltage leakage from the training data while maintaining the computational efficiency of the digital controller.

## 1. Inner Randomization (Within the Short Measurement Window)

* **Action:** Randomize the execution order of the Hadamard matrix columns (time steps) for every new measurement table.

* **Purpose:** Prevents specific Hadamard row frequencies (Walsh functions) from correlating with the local discharge slope. It converts systematic phase bias into zero-mean uncorrelated white noise.

* **Efficient Implementation:**

  1. Transmit the columns in the randomized sequence.

  2. Upon ADC sampling, use a look-up table (scatter-write) to place the sampled data directly into its canonical index in the memory buffer.

  3. Execute the standard Fast Hadamard Transform (FHT) on the pre-sorted buffer. This preserves the $O(N \log_2 N)$ computational efficiency without any processing penalty for the randomization.

## 2. Outer Randomization (Across the Full Refresh Cycle)

* **Action:** Randomize the temporal placement of the short measurement window across the entire macroscopic refresh cycle span ($T_{INF}$).

* **Purpose:** Captures the full non-linear discharge curve without tying long-term thermal drift or component variations to a sequential sampling phase.

* **Implementation:**

  1. Keep the deterministic input data fixed across multiple refresh cycles.

  2. Use a Fisher-Yates shuffle to select the temporal offset of the measurement window for each cycle.

  3. Repeat until the entire refresh span is fully mapped by the aggregated short tables.

  4. Execute the MAML weight update only after the full span is covered.