# Inverted MAML: Summing Attenuator Balancing Act, Hardware Lineage & Future ADC(145/149) Tap Specification
### Engineering Analysis: Carrier SNR vs. ColTIA Dynamic Headroom vs. Vernier Compensation Authority

> **Patent Reference**: SE 2630397-4 (Open Science Hardware)  
> **Platform**: Dual-FPGA Inverted MAML Silicon Engine (Trion T120 Master SoC + Trion T20 Matrix Controller)  
> **Silicon Matrices**: Dual-2T1C Differential Analog Triode Multipliers (M33, M3, M8)  
> **Authors**: Inverted MAML Hardware & Firmware Engineering Team  
> **Date**: November 3, 2026  

---

## 1. Executive Summary

In the Inverted MAML physical analog computing architecture, the passive resistive attenuator positioned between the Matrix 33 uncompensated feedforward output and the inverting input of the ColTIA transimpedance amplifiers is not a simple gain trimmer. It governs a fundamental physical tri-lemma:
1. **Hadamard Carrier Wave Demodulation SNR**: Preservation of microscopic modulation envelopes from Matrix 33 necessary for non-backprop inner-loop gradient extraction.
2. **ColTIA Transimpedance Amplifier Dynamic Headroom**: Prevention of physical op-amp saturation ("bottning") against single-supply ground and negative rails.
3. **Matrix 8 Vernier Compensation Authority**: Ensuring the analog compensation path can cancel baseline offsets without driving physical weights into $\pm 127\text{ LSB}$ saturation limits.

Empirical verification on physical silicon confirms that the passive attenuator choice is a delicate **balancing act**. If attenuation is too aggressive ($1\text{ k}\Omega / 15\text{ k}\Omega$ or $33\text{ k}\Omega$), Hadamard carrier signals vanish into background noise. If attenuation is too weak ($1\text{ k}\Omega / 3.9\text{ k}\Omega$), excessive DC current collapses ColTIA headroom down to $-1\,600\text{ LSB}$ (leaving only $\sim 180\text{ LSB}$ to rail). The calibrated value of **$1\text{ k}\Omega / 5.1\text{ k}\Omega$** achieves the optimal sweet spot on both Card 1 and Card 2.

To eliminate this compromise entirely in next-generation silicon, an auxiliary pre-attenuation sampling tap (**ADC_149 / ADC_149**) will decouple Hadamard carrier sensing from the DC calculation summation node.

---

## 2. Attenuator Modification History & Silicon Lineage

Across the experimental development of Inverted MAML hardware revisions, multiple attenuator ratios have been systematically evaluated on physical silicon:

```
===================================================================================================================
DATE / REVISION   HARDWARE   ATTENUATOR RESISTOR   CARRIER SNR    COLTIA HEADROOM    COMPENSATION AUTHORITY   STATUS
===================================================================================================================
Initial Baseline  Card 1     1k / 3.9k Ohm         Strong         Compressed         Marginal (Near Rail)     Replaced
Calibration Step  Card 1     1k / 5.1k Ohm         Optimal        >750 LSB Margin    Balanced (±20 LSB)       Milestone 2 Target
Experiment A      Card 1     1k / 3.3k Ohm         Excessive      Severely Clipped   Saturated (-127 LSB)     Rejected
Experiment B      Card 1     1k / 15k Ohm          Vanished       Large              Saturated (+127 LSB)     Failed (No Learning)
Experiment C      Card 1     1k / 33k Ohm          Zero Signal    Immense            No Gradient              Failed (Dead Loop)
Restoration       Card 1     1k / 5.1k Ohm         Optimal        >750 LSB Margin    Balanced (±20 LSB)       Verified (7.73 bits)
-------------------------------------------------------------------------------------------------------------------
Initial Build     Card 2     1k / 3.9k Ohm         Strong         Compressed         Restricted by Op-Amp     Diagnosed
Resoldered State  Card 2     1k / 5.1k Ohm         Optimal        Restored (+700 LSB) Balanced (±20 LSB)       Active Test
===================================================================================================================
```

* **Card 1 Progression**: Initially fabricated with $3.9\text{ k}\Omega$, then upgraded to $5.1\text{ k}\Omega$ which enabled the historical Milestone 2 record of **$280.6\text{ LSB}^2$ ($7.73\text{ bits}$ ENOB)**. Subsequent trials with $3.3\text{ k}\Omega$ caused excessive rail-clipping, while $15\text{ k}\Omega$ and $33\text{ k}\Omega$ completely extinguished carrier wave visibility. The design was firmly restored to $5.1\text{ k}\Omega$.
* **Card 2 Progression**: Built with $3.9\text{ k}\Omega$. Initial tests revealed that while isolated favorable vectors achieved $174.9\text{ LSB}^2$ ($8.07\text{ bits}$), the average over rotating vectors was dragged down to $5.43\text{ bits}$ due to ColTIA headroom compression. On November 3, 2026, Card 2 was resoldered to **$1\text{ k}\Omega / 5.1\text{ k}\Omega$**, matching Card 1.

---

## 3. The Physical Tri-Lemma: Why the Attenuator is a Balancing Act

The summing node acts as the current junction where the uncompensated signal from Matrix 33 and the compensation current from Matrix 8 converge at the virtual ground of the ColTIA transimpedance stage:

$$\sum I_{\text{node}} = I_{\text{M33}}\cdot \frac{R_{\text{pull}}}{R_{\text{series}} + R_{\text{pull}}} + I_{\text{M8,vernier}} - I_{\text{ColTIA,in}} = 0$$

```
   Matrix 33 Output (Hadamard Modulation + DC)
          │
         [R_series = 1k]
          │
          ├───[R_pull = 3.9k / 5.1k / 15k]─── GND (Passive Shunt)
          │
          ├─── Matrix 8 Vernier Compensation Path (driven by Sigmoid 4)
          │
          ▼
   ColTIA Virtual Ground (Inverting Input Op-Amp)
          │
         [R_feedback]
          │
          ▼
   ADC_49 Sampling Node (Demodulation & Residual Output)
```

### Regime 1: Over-Attenuation ($1\text{ k}\Omega / 15\text{ k}\Omega$ or $33\text{ k}\Omega$)
* **Failure Mechanism**: Matrix 33 modulation is shunted to ground. The high-frequency Hadamard carrier envelopes ($\sim 500\text{ kHz}$) are reduced to microvolt levels, sinking below the quantization noise floor of the ADC and the thermal noise floor of the analog routing.
* **Result**: The digital Hadamard demodulator receives virtually zero cross-correlation energy. Weight gradients $\Delta W$ drop to zero, halting convergence completely.

### Regime 2: Moderately High Attenuation ($1\text{ k}\Omega / 10\text{ k}\Omega$)
* **Failure Mechanism**: Carrier envelopes are barely detectable, but the static impedance ratio forces the compensation path (Matrix 8 vernier) to operate at extreme dynamic range to cancel residual offsets.
* **Result**: Matrix 8 physical weights hit the hard rail saturation limits of $\pm 127\text{ LSB}$. The inner loop cannot close because compensation authority is exhausted.

### Regime 3: Under-Attenuation ($1\text{ k}\Omega / 3.9\text{ k}\Omega$)
* **Failure Mechanism**: Low shunt impedance draws excessive current into the single-supply ColTIA op-amps.
* **Result**: The DC quiescent level is dragged down to **$-1\,600\text{ LSB}$**, leaving a razor-thin margin of only $\sim 180\text{ LSB}$ before triggering the physical **$-1\,797\text{ LSB}$ ColTIA Saturation Guard**. When arbitrary input vectors require negative excursion, the amplifiers compress into non-linear saturation, creating phantom gradient bursts that degrade average ENOB.

### Regime 4: The Calibrated Optimum ($1\text{ k}\Omega / 5.1\text{ k}\Omega$)
* **Operating Point**: Increases shunt impedance by $24\%$, reducing DC current draw by $\sim 30\%$.
* **Empirical Outcome**: Lifts the DC level from $-1\,600\text{ LSB}$ up to **$-900\text{ LSB}$**, restoring **$>750\text{ LSB}$ of symmetric linear dynamic headroom** while retaining ample Hadamard carrier amplitude for sub-LSB gradient demodulation.

---

## 4. Operational Status of Active Drivers

1. **DAC(2) Input Drivers**:
   * Upgraded on both Card 1 and Card 2 to **MCP6444-E/SL (70 mA high-current op-amps)**.
   * Eliminates drive starvation on the feedforward In-Data rows, providing clean differential sinusoidal carrier waves.
2. **Sigmoid 4 Vernier Drivers**:
   * **Currently unmodified** on Card 2 (still equipped with the standard low-current op-amp, $\sim 10\text{--}15\text{ mA}$).
   * While the $5.1\text{ k}\Omega$ resistor relieves DC current strain on ColTIA, Sigmoid 4 remains the secondary current bottleneck when driving all 6 columns of Matrix 8 simultaneously under extreme vector alignments. Upgrading Sigmoid 4 to MCP6444-E/SL represents the final planned solder modification.

---

## 5. Architectural Roadmap: The Dedicated Auxiliary ADC Tap (ADC_149 / ADC_149)

To permanently decouple Hadamard gradient demodulation from loop summation dynamics, future hardware iterations (Rev 3.0 / Next-Gen Silicon) will incorporate a dedicated auxiliary sampling tap:

```
               Matrix 33 Uncompensated Output
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [High-Z Pre-Amp Tap]               [Variable Passive Attenuator]
            │                                 │
     ADC_149 / ADC_149                 Summing Junction
    (Auxiliary Hadamard)                      │
            │                         Matrix 8 Vernier Comp
            ▼                                 │
   Direct Demodulation Engine                 ▼
   (Max SNR, No Attenuation)           ColTIA Main Loop Output
                                              │
                                              ▼
                                            ADC_49
                                      (Error / Residual)
```

### Key Engineering Advantages:
1. **Zero Compromise on Carrier SNR**: The auxiliary ADC samples the Hadamard carrier directly before the attenuation network at full voltage swing ($>1\text{ V}_{\text{p-p}}$), guaranteeing maximal SNR regardless of how heavily the calculation node is dampened.
2. **Arbitrary Loop Damping**: Engineers can freely tune the summing attenuator ($3.9\text{ k}\Omega$, $5.1\text{ k}\Omega$, $10\text{ k}\Omega$, or dynamic electronic pots) purely to optimize ColTIA headroom and compensation swing, without any risk of extinguishing the gradient carrier signal.
3. **Immunity to Solder Variance**: Eliminates sensitivity to board-to-board resistor tolerances, guaranteeing uniform convergence across scaled multi-tile analog matrix arrays.

