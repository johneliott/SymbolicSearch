# SymbolicSearch

**Permutation Sensitivity in Incremental Boolean Constraint Propagation**

This repository contains an experimental framework for measuring how the ordering of external decision sequences affects the internal behavior of a deterministic Boolean Constraint Propagation (BCP) kernel operating over a fixed CNF formula.

It consists of:
*   A deterministic BCP execution kernel written in Common Lisp (`bpc.lisp`, `runner.lisp`).
*   An experimental statistical harness written in Python (`harness.py`) to generate sample permutations, interact with the Lisp kernel via JSON IPC, and visualize $\Delta Y_P$ (Propagation Sensitivity) and $\Delta Y_D$ (Decision Sensitivity) distributions.

## Reference Documents

The theoretical formulation, methodology, and ongoing notes for this framework can be found in the following documents:
*   [The LEGO Bin Analogy](https://docs.google.com/document/d/106pWM471TeMmkFkNuzdlfH_obuVzOLFF1O99mTmnTPo/edit?usp=sharing)
*   [Theoretical Intuition](https://docs.google.com/document/d/1Iatv2ceMATE1ZuM3xn8pW-_jRTXDSyoa_5Fif4WqAGM/edit?usp=sharing)
*   [Empirical Study Design](https://docs.google.com/document/d/18h5eRQK6Ce6lHeLzHPrEQsXuUlrd3fk9Q8lHXuy32T0/edit?usp=sharing)
*   [Result Interpretations](https://docs.google.com/document/d/11QvYh9nLwjqMqpgxK7e5Wp9e9xQ7fXcFJAyNqW2ZB7o/edit?usp=sharing)
*   [Potential Applications](https://docs.google.com/document/d/18I2sywKv9rfcKYKnu45_qLsSbnVRMhZSAQYWXHk47Rw/edit?usp=sharing)

## Setup and Usage

Ensure you have [SBCL](https://www.sbcl.org/) installed for the Lisp kernel, and Python 3 for the harness.

```bash
# Set up a python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the experimental harness
python3 harness.py
```

Running the harness will output basic trajectory delta metrics to standard out and save the distribution histograms in a new image file (`orbit_analysis.png`).
