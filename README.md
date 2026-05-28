# SymbolicSearch: Empirical Measurement of Permutation Sensitivity in Incremental SAT Solving

**Permutation Sensitivity in Incremental Boolean Constraint Propagation**

This repository contains an experimental framework for measuring how the ordering of external decision sequences affects the internal behavior of a deterministic Boolean Constraint Propagation (BCP) kernel. By eliminating solver-internal heuristic artifacts (such as variable state decay, phase saving, and non-chronological restarts), this framework isolates the path-dependency of the joint system: the interaction between a specific CNF graph topology and the deterministic state transitions of the propagation kernel.

## Architecture

The framework consists of a highly optimized, custom-built execution pipeline designed to evaluate the symmetric group orbit ($S_k$) of an extracted macro sequence.

### 1. Python Preprocessor (`preprocessor.py`)
- **Variable Incidence Graph (VIG):** Constructs a topological map of the CNF formula.
- **Macro Extraction:** Extracts a tightly-coupled cluster of $k$ variables via Breadth-First Search (BFS) from a high-centrality seed.
- **Pure Literal Elimination:** Identifies pure literals to condition the solver with a "Simplified Backbone State" ($A_0$), stripping away trivial outer-graph noise before macro evaluation.
- **Orbit Generation:** Generates the exact $k!$ symmetric group orbit $S_k$ while holding literal polarities strictly frozen.

### 2. Common Lisp BCP Kernel (`BCP_KERNEL.lisp` & `runner.lisp`)
- **$\mathcal{O}(1)$ Watched Literals:** The BCP engine is built from the ground up utilizing a Two-Literal Watching mechanism to achieve extreme efficiency, allowing it to scale to industrial hardware and cryptographic graphs (50k+ clauses).
- **Single-Shuffled Database:** To eliminate memory-layout priority bias, the formula clause array is randomly shuffled exactly once during hydration and held strictly static across all $k!$ evaluations.
- **Strict IPC Isolation:** Each permutation executes in isolation, strictly recording deterministic stopping indices ($\tau$) and propagation unit implications ($Y_P$).

### 3. Evaluation Harness & Orchestrator (`harness.py`, `run_experiment.py`, `generate_final_plots.py`)
- Calculates the topological vector profile for each sequence:
  - **Stopping Time ($\tau$):** The depth at which the kernel encounters a structural contradiction.
  - **Propagation Velocity ($\eta$):** The normalized density of information flow ($\eta = Y_P / \tau$).
- Statistically aggregates $\text{Var}(\tau)$, $\text{Var}(\eta)$, and $CV(\eta)$ to classify the CNF hypergraph into distinct phenotypic distributions.

## Benchmark Results & Structural Phenotypes

We mapped the topology of three distinct benchmark classes, evaluating them under the Simplified Backbone State:

1. **Cryptographic SAT (AES-128)**
   - **Profile:** The Isotropic / Null Hypothesis ($H_0$)
   - **Metrics:** $\text{Var}(\tau) = 0.0000$, $\text{Var}(\eta) = 0.0000$
   - **Conclusion:** AES possesses flawlessly rigid and symmetric diffusion layers. The chronological order of macro injections does not deform the implication timeline. 

2. **Bounded Model Checking (BMC)**
   - **Profile:** The Cascade-Dense / Explosive Profile
   - **Metrics:** $\text{Var}(\tau) = 0.0000$, $\text{Var}(\eta) > 0$, $CV(\eta) > 0$
   - **Conclusion:** Pipelined directional constraints force all evaluation paths to halt at an identical depth, but the *velocity* of reverse-implications triggers massive parallel constraint resolutions, isolating the mechanics of hardware pipelines.

3. **Random 3-SAT (Phase-Transition)**
   - **Profile:** The Path-Dependent / Directional Profile
   - **Metrics:** $\text{Var}(\tau) \gg 0$, $\text{Var}(\eta) \gg 0$
   - **Conclusion:** At the phase-transition ratio ($\alpha \approx 4.26$), random networks produce deep, non-isotropic geometric valleys. The assignment order directly dictates whether the system hits a rapid conflict or wanders through dense implication cascades.

## Setup and Usage

Ensure you have [SBCL](https://www.sbcl.org/) installed for the Lisp kernel, and Python 3.10+ for the harness.

```bash
# Set up a python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run a single evaluation and plot the orbit
python3 harness.py

# Run the batch experiment across all benchmarks
python3 run_experiment.py

# Generate thesis defense visual overlays for AES, BMC, and Random 3-SAT
python3 generate_final_plots.py
```

## Reference Documents

The theoretical formulation, methodology, and ongoing notes for this framework can be found in the following documents:
*   [The LEGO Bin Analogy](https://docs.google.com/document/d/106pWM471TeMmkFkNuzdlfH_obuVzOLFF1O99mTmnTPo/edit?usp=sharing)
*   [Theoretical Intuition](https://docs.google.com/document/d/1Iatv2ceMATE1ZuM3xn8pW-_jRTXDSyoa_5Fif4WqAGM/edit?usp=sharing)
*   [Empirical Study Design](https://docs.google.com/document/d/18h5eRQK6Ce6lHeLzHPrEQsXuUlrd3fk9Q8lHXuy32T0/edit?usp=sharing)
*   [Potential Applications](https://docs.google.com/document/d/18I2sywKv9rfcKYKnu45_qLsSbnVRMhZSAQYWXHk47Rw/edit?usp=sharing)