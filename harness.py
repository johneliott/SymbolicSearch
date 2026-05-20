import json
import subprocess
import itertools
import random
import numpy as np
import matplotlib.pyplot as plt

class LispKernel:
    def __init__(self, script_path="runner.lisp"):
        self.process = subprocess.Popen(
            ['sbcl', '--script', script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    def run_sequence(self, formula, seq):
        payload = json.dumps({
            "formula": formula,
            "sequence": list(seq)
        })
        self.process.stdin.write(payload + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read()
            raise RuntimeError(stderr)
        return json.loads(line)

    def close(self):
        self.process.stdin.close()
        self.process.terminate()
        self.process.wait()

def sample_permutations(seq, N):
    if len(seq) <= 6:
        perms = list(itertools.permutations(seq))
        random.shuffle(perms)
        return perms[:N]
    else:
        return [tuple(random.sample(seq, len(seq))) for _ in range(N)]

def evaluate_orbit(kernel, formula, base_seq, N=500):
    base = kernel.run_sequence(formula, base_seq)
    deltas = []
    samples = sample_permutations(base_seq, N)
    print(f"Evaluating orbit: {len(samples)} permutations")
    for pi in samples:
        result = kernel.run_sequence(formula, pi)
        deltas.append({
            "perm": pi,
            # Δ-projection components
            "d_decisions": result["decisions"] - base["decisions"],
            "d_props": result["props"] - base["props"],
            # Mapping Y_B to cardinality_gap from Lisp kernel
            "d_backtracks": result.get("cardinality_gap", 0) - base.get("cardinality_gap", 0),
            # terminal stratification
            "terminal": result.get("status", "UNKNOWN").upper(),
        })
    return base, deltas

def summarize(deltas):
    d_props = np.array([d["d_props"] for d in deltas])
    d_decisions = np.array([d["d_decisions"] for d in deltas])
    d_backtracks = np.array([d["d_backtracks"] for d in deltas])
    return {
        "props_mean": float(np.mean(d_props)),
        "props_var": float(np.var(d_props)),
        "decisions_var": float(np.var(d_decisions)),
        "backtrack_mean": float(np.mean(d_backtracks)),
        "backtrack_var": float(np.var(d_backtracks)),
        "skew_proxy": float(np.mean(np.abs(d_props))),
    }

def split_by_terminal(deltas):
    sat = [d for d in deltas if d["terminal"] == "SAT"]
    unsat = [d for d in deltas if d["terminal"] == "UNSAT"]
    return sat, unsat

def plot_results(deltas):
    d_props = np.array([d["d_props"] for d in deltas])
    d_decisions = np.array([d["d_decisions"] for d in deltas])
    d_backtracks = np.array([d["d_backtracks"] for d in deltas])
    sat, unsat = split_by_terminal(deltas)

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))

    # 1. ΔY_P
    axs[0, 0].hist(d_props, bins=25, color='royalblue', edgecolor='black', alpha=0.7)
    axs[0, 0].set_title(r'Distribution of $\Delta Y_P$' + '\n(Propagation Deformation)')
    axs[0, 0].set_xlabel(r'$\Delta Y_P$')
    axs[0, 0].set_ylabel('Frequency')
    axs[0, 0].grid(True, linestyle='--', alpha=0.6)

    # 2. ΔY_D
    axs[0, 1].hist(d_decisions, bins=25, color='seagreen', edgecolor='black', alpha=0.7)
    axs[0, 1].set_title(r'Distribution of $\Delta Y_D$' + '\n(Decision / Stopping-Time Deformation)')
    axs[0, 1].set_xlabel(r'$\Delta Y_D$')
    axs[0, 1].set_ylabel('Frequency')
    axs[0, 1].grid(True, linestyle='--', alpha=0.6)

    # 3. ΔY_B (NEW — critical)
    axs[1, 0].hist(d_backtracks, bins=25, color='darkorchid', edgecolor='black', alpha=0.7)
    axs[1, 0].set_title(r'Distribution of $\Delta Y_B$' + '\n(Structural Divergence / Conflict Cost)')
    axs[1, 0].set_xlabel(r'$\Delta Y_B$')
    axs[1, 0].set_ylabel('Frequency')
    axs[1, 0].grid(True, linestyle='--', alpha=0.6)

    # 4. Joint projection (P vs D) - colored by terminal status
    if sat:
        axs[1, 1].scatter([d["d_props"] for d in sat], [d["d_decisions"] for d in sat], 
                          color='dodgerblue', alpha=0.6, edgecolors='black', label='SAT')
    if unsat:
        axs[1, 1].scatter([d["d_props"] for d in unsat], [d["d_decisions"] for d in unsat], 
                          color='crimson', alpha=0.6, edgecolors='black', label='UNSAT')
    
    axs[1, 1].set_title('Joint Projection Stratified by Terminal State\n' + r'$\Delta Y_P$ vs $\Delta Y_D$')
    axs[1, 1].set_xlabel(r'$\Delta Y_P$ (Propagation Cost)')
    axs[1, 1].set_ylabel(r'$\Delta Y_D$ (Decision Cost)')
    if sat or unsat:
        axs[1, 1].legend()
    axs[1, 1].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.savefig("orbit_analysis.png", dpi=300)
    print("Saved publication-grade orbit_analysis.png")

def main():
    formula = [
        [-1, -2, 3],
        [-3, 4],
        [-4, 5],
        [-2, -5]
    ]
    base_seq = [1, 2, 3, 4]

    kernel = LispKernel()
    try:
        base, deltas = evaluate_orbit(kernel, formula, base_seq, N=200)
        print("\nBASE EXECUTION:")
        print(base)
        print("\nSUMMARY:")
        print(json.dumps(summarize(deltas), indent=2))
        plot_results(deltas)
    finally:
        kernel.close()

if __name__ == "__main__":
    main()
