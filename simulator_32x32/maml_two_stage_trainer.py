"""
TWO-STAGE META-LEARNING WITH ABRUPT & GRADUAL PHYSICS CHANGES
==============================================================

Stage 1: Base Model Training
  - Outer Loop: Create NEW physics each iteration (abrupt changes)
  - Inner Loop: MAML learns to adapt quickly to that physics
  - Result: Meta-learned base model generalizes across physics spaces
  
Stage 2: Operation Mode
  - Inner Loop Only: Continuous learning during deployment
  - Physics changes GRADUALLY (thermal drift, aging)
  - Result: Adaptive weights compensate for slow drift
  
Theory:
  The outer loop forces the base model to learn a "good starting point" that
  can quickly adapt to ANY physical environment. This is true meta-learning.
  The inner loop then uses this meta-learned base model for fast adaptation
  during deployment with gradual physics changes.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors


class TwoStageDynamicMAML:
    """
    Extended MAML with explicit outer loop for meta-learning across physics spaces.
    """
    
    def __init__(self, triad: AtomicTriad, learning_rate: float = 0.50,
                 inner_lr: float = 0.05, outer_lr: float = 0.01,
                 num_strata: int = 1, adaptive_lr: bool = True):
        """
        Args:
            triad: AtomicTriad system
            learning_rate: Main learning rate (inner loop base)
            inner_lr: Inner loop learning rate
            outer_lr: Outer loop meta-learning rate
            num_strata: Stratified measurements per cycle
            adaptive_lr: Enable learning rate decay
        """
        self.triad = triad
        self.learning_rate = learning_rate
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self.num_strata = num_strata
        self.adaptive_lr = adaptive_lr
        
        # Base model weights (learned during outer loop)
        self.base_M3_weights = triad.M3.weights.copy()
        self.base_M8_weights = triad.M8.weights.copy()
        
        # Metrics tracking
        self.outer_loop_history = []
        self.operation_mode_history = []
        self.current_stage = "training"  # "training" or "operation"
    
    def reset_to_base_model(self):
        """Reset weights to learned base model (for inner loop start)."""
        self.triad.set_correction_weights(
            self.base_M3_weights.copy(),
            self.base_M8_weights.copy()
        )
    
    def save_as_base_model(self):
        """Save current weights as meta-learned base model."""
        self.base_M3_weights = self.triad.M3.weights.copy()
        self.base_M8_weights = self.triad.M8.weights.copy()
    
    def apply_abrupt_physics_change(self, harsh_config: Optional[Dict] = None):
        """
        Abruptly change physics (for outer loop training).
        
        This creates a NEW physics environment to force meta-learning.
        
        Args:
            harsh_config: Manufacturing variation parameters
        """
        if harsh_config is None:
            harsh_config = {
                'V_th_sigma': 0.15,
                'g_m_sigma': 0.20,
                'R_sigma': 0.20,
            }
        
        # Remove old variations
        for matrix in [self.triad.M33, self.triad.M3, self.triad.M8]:
            # Apply fresh manufacturing variations
            matrix.cell_bank.inject_manufacturing_variations(harsh_config)
            
            # Apply fresh per-cell Vth variations (generate array first)
            num_cells = len(matrix.cell_bank.cells_active) + len(matrix.cell_bank.cells_bias)
            vth_variations = np.random.normal(0, 0.06, size=(32, 32))
            matrix.cell_bank.apply_per_cell_vth_variations(vth_variations)
    
    def apply_gradual_physics_drift(self, drift_fraction: float):
        """
        Gradually drift physics (for operation mode).
        
        Simulates slow thermal/aging effects during deployment.
        
        Args:
            drift_fraction: 0.0 to 1.0 (0=no drift, 1.0=maximum drift)
        """
        # Drift can include:
        # - Slow thermal changes
        # - Oxide degradation
        # - Electromigration
        
        for matrix in [self.triad.M33, self.triad.M3, self.triad.M8]:
            # Apply gradually increasing thermal stress
            thermal_stress = 35.0 * drift_fraction  # 0 to +35°C
            matrix.cell_bank.inject_thermal_drift(temp_delta_C=thermal_stress)
            
            # Slight aging effects (slow Vth degradation)
            for cell in matrix.cell_bank.cells_active:
                aging_effect = 0.02 * drift_fraction  # Up to 2% Vth shift
                cell.V_th_mfg += aging_effect
    
    def train_outer_loop(self, x_train: np.ndarray, y_train: np.ndarray,
                        outer_iterations: int = 5,
                        inner_cycles_per_outer: int = 50,
                        harsh_config: Optional[Dict] = None,
                        verbose: bool = True) -> Dict:
        """
        STAGE 1: Train base model with outer loop (abrupt physics changes).
        
        Args:
            x_train: (N, 32) training inputs
            y_train: (N, 32) training targets
            outer_iterations: Number of outer loop iterations (each with new physics)
            inner_cycles_per_outer: Inner loop cycles per outer iteration
            harsh_config: Physics configuration
            verbose: Print progress
        
        Returns:
            training_log with outer loop metrics
        """
        self.current_stage = "training"
        training_log = {
            'outer_iterations': [],
            'inner_cycle_stats': [],  # List of lists
            'physics_change_cycles': [],  # When physics changed
            'final_precision_per_outer': [],
            'base_model_precision': []
        }
        
        print("\n" + "=" * 90)
        print("STAGE 1: BASE MODEL TRAINING (Outer Loop + Inner Loops)")
        print("=" * 90)
        print(f"Outer iterations: {outer_iterations}")
        print(f"Inner cycles per outer: {inner_cycles_per_outer}")
        print(f"Total training cycles: {outer_iterations * inner_cycles_per_outer}")
        
        for outer_iter in range(outer_iterations):
            print(f"\n{'─' * 90}")
            print(f"OUTER LOOP ITERATION {outer_iter + 1}/{outer_iterations}")
            print(f"{'─' * 90}")
            
            # === ABRUPT PHYSICS CHANGE ===
            print(f"  Applying ABRUPT physics change...")
            self.apply_abrupt_physics_change(harsh_config)
            training_log['physics_change_cycles'].append(
                outer_iter * inner_cycles_per_outer
            )
            
            # === RESET TO BASE MODEL ===
            print(f"  Resetting weights to base model...")
            self.reset_to_base_model()
            
            # === MEASURE BASELINE ===
            optimizer = InvertedMAML(
                self.triad, learning_rate=self.inner_lr, num_strata=self.num_strata,
                adaptive_lr=self.adaptive_lr, lr_decay_factor=0.98
            )
            
            baseline_precision = self._measure_precision(x_train, y_train, optimizer)
            print(f"  Baseline precision (before adaptation): {baseline_precision:.2f} bits")
            
            # === INNER LOOP: MAML updates ===
            inner_losses = []
            inner_precisions = []
            
            for inner_cycle in range(inner_cycles_per_outer):
                cycle_loss = 0.0
                
                for x, y in zip(x_train, y_train):
                    loss = optimizer.update_weights(x, y)
                    cycle_loss += loss
                
                avg_loss = cycle_loss / len(x_train)
                precision = self._measure_precision(x_train, y_train, optimizer)
                
                inner_losses.append(avg_loss)
                inner_precisions.append(precision)
                
                if verbose and (inner_cycle % 10 == 0 or inner_cycle == inner_cycles_per_outer - 1):
                    lr_display = optimizer.lr if optimizer.adaptive_lr else optimizer.lr_init
                    print(f"    Inner cycle {inner_cycle:3d}: Loss={avg_loss:.2e}, "
                          f"Precision={precision:.2f} bits, LR={lr_display:.4f}")
            
            # === SAVE IMPROVED BASE MODEL ===
            final_precision = inner_precisions[-1]
            print(f"  Final precision (after adaptation): {final_precision:.2f} bits")
            print(f"  Improvement this outer iteration: {final_precision - baseline_precision:+.2f} bits")
            
            # Accumulate base model (meta-learning: base model learns to start well)
            self.save_as_base_model()
            
            training_log['outer_iterations'].append(outer_iter)
            training_log['inner_cycle_stats'].append({
                'losses': inner_losses,
                'precisions': inner_precisions,
                'baseline': baseline_precision,
                'final': final_precision,
                'improvement': final_precision - baseline_precision
            })
            training_log['final_precision_per_outer'].append(final_precision)
            training_log['base_model_precision'].append(final_precision)
        
        self.outer_loop_history = training_log
        return training_log
    
    def run_operation_mode(self, x_test: np.ndarray, y_test: np.ndarray,
                          operation_cycles: int = 100,
                          drift_speed: float = 0.01,  # Per cycle
                          verbose: bool = True) -> Dict:
        """
        STAGE 2: Operation mode (inner loop only, gradual physics drift).
        
        This simulates deployed hardware that:
        - Starts with learned base model
        - Physics drifts slowly (thermal, aging)
        - Inner loop continuously adapts
        
        Args:
            x_test: (N, 32) test/operational inputs
            y_test: (N, 32) target outputs
            operation_cycles: Number of cycles during operation
            drift_speed: Physics change per cycle (0.0 to 1.0)
            verbose: Print progress
        
        Returns:
            operation_log with metrics
        """
        self.current_stage = "operation"
        operation_log = {
            'cycles': [],
            'precisions': [],
            'losses': [],
            'drift_level': [],
            'weight_changes': []
        }
        
        print("\n" + "=" * 90)
        print("STAGE 2: OPERATION MODE (Inner Loop Only + Gradual Physics Drift)")
        print("=" * 90)
        print(f"Operation cycles: {operation_cycles}")
        print(f"Drift speed: {drift_speed:.4f} per cycle")
        print(f"Max total drift: {operation_cycles * drift_speed:.2f}")
        
        # === SETUP OPERATION MODE ===
        print(f"\nStarting with learned base model...")
        self.reset_to_base_model()
        
        # Create fresh physics for operation (single deployment environment)
        self.apply_abrupt_physics_change()
        baseline_precision = self._measure_precision(x_test, y_test, 
                                                     InvertedMAML(self.triad, self.inner_lr))
        print(f"Baseline precision (start of operation): {baseline_precision:.2f} bits")
        
        optimizer = InvertedMAML(
            self.triad, learning_rate=self.inner_lr, num_strata=self.num_strata,
            adaptive_lr=False, lr_decay_factor=0.98  # No decay in operation
        )
        
        # Store initial weights
        W_M3_prev = self.triad.M3.weights.copy()
        W_M8_prev = self.triad.M8.weights.copy()
        
        for op_cycle in range(operation_cycles):
            # === GRADUAL PHYSICS DRIFT ===
            # Slowly change physics (thermal, aging)
            drift_fraction = (op_cycle / operation_cycles) * drift_speed
            self.apply_gradual_physics_drift(drift_fraction)
            
            # === INNER LOOP ADAPTATION ===
            cycle_loss = 0.0
            
            for x, y in zip(x_test, y_test):
                loss = optimizer.update_weights(x, y)
                cycle_loss += loss
            
            avg_loss = cycle_loss / len(x_test)
            precision = self._measure_precision(x_test, y_test, optimizer)
            
            # Measure weight changes (adaptation activity)
            weight_change = (
                np.linalg.norm(self.triad.M3.weights - W_M3_prev) +
                np.linalg.norm(self.triad.M8.weights - W_M8_prev)
            )
            W_M3_prev = self.triad.M3.weights.copy()
            W_M8_prev = self.triad.M8.weights.copy()
            
            operation_log['cycles'].append(op_cycle)
            operation_log['precisions'].append(precision)
            operation_log['losses'].append(avg_loss)
            operation_log['drift_level'].append(drift_fraction)
            operation_log['weight_changes'].append(weight_change)
            
            if verbose and (op_cycle % 10 == 0 or op_cycle == operation_cycles - 1):
                print(f"  Cycle {op_cycle:3d}: Loss={avg_loss:.2e}, Precision={precision:.2f} bits, "
                      f"Drift={drift_fraction:.3f}, WeightChange={weight_change:.4e}")
        
        print(f"\nFinal precision (end of operation): {operation_log['precisions'][-1]:.2f} bits")
        print(f"Precision retention: {operation_log['precisions'][-1] - baseline_precision:+.2f} bits")
        
        self.operation_mode_history = operation_log
        return operation_log
    
    def _measure_precision(self, x_test: np.ndarray, y_test: np.ndarray,
                          optimizer: InvertedMAML) -> float:
        """Helper: measure output precision."""
        total_error = 0.0
        
        for x, y in zip(x_test, y_test):
            self.triad.refresh_cycle()
            output, _ = self.triad.forward(x, t_snapshot_ms=0.5)
            error = np.abs(output - y)
            total_error += np.mean(error)
        
        avg_error = total_error / len(x_test)
        # Convert to bits: SNR in bits = -log2(error)
        precision_bits = -np.log2(np.clip(avg_error, 1e-6, 1.0))
        return precision_bits
    
    def get_summary(self) -> Dict:
        """Get comprehensive summary of both stages."""
        summary = {
            'stage1_training': self.outer_loop_history,
            'stage2_operation': self.operation_mode_history,
            'base_model_final_precision': self.base_M3_weights is not None
        }
        return summary
