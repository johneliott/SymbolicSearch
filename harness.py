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

    def run_sequence(self, formula, seq, context=None):
        payload = json.dumps({
            "context": context or [],
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

def evaluate_orbit(kernel, formula, base_seq, context=None, N=500):
    base = kernel.run_sequence(formula, base_seq, context)
    deltas = []
    samples = sample_permutations(base_seq, N)
    
    # In your design, the raw decision count from the clean state is the stopping time tau
    base_tau = base["decisions"] 
    print(f"Evaluating orbit: {len(samples)} permutations. Base sequence halted at tau = {base_tau}")
    
    for pi in samples:
        result = kernel.run_sequence(formula, pi, context)
        current_tau = result["decisions"]
        
        deltas.append({
            "perm": pi,
            # Raw core metrics for absolute orbit analysis
            "tau": current_tau, 
            "props": result["props"],
            
            # Δ-projection components relative to your baseline trace
            "d_tau": current_tau - base_tau,
            "d_props": result["props"] - base["props"],
            "d_footprint": result.get("cardinality_gap", 0) - base.get("cardinality_gap", 0),
            
            # Terminal stratification
            "terminal": result.get("status", "UNKNOWN").upper(),
        })
    return base, deltas

def summarize(deltas):
    raw_taus = np.array([d["tau"] for d in deltas])
    d_props = np.array([d["d_props"] for d in deltas])
    d_taus = np.array([d["d_tau"] for d in deltas])
    
    return {
        # Core Hypotheses: Measure structural permutation sensitivity directly
        "tau_mean": float(np.mean(raw_taus)),
        "tau_var": float(np.var(raw_taus)),  # <--- This is your primary Var(τ) metric!
        
        # Propagation deformation metrics
        "props_delta_mean": float(np.mean(d_props)),
        "props_delta_var": float(np.var(d_props)),
        
        # Relative stopping deformation metrics
        "tau_delta_var": float(np.var(d_taus)),
        "skew_proxy": float(np.mean(np.abs(d_props))),
    }

def split_by_terminal(deltas):
    sat = [d for d in deltas if d["terminal"] == "SAT"]
    unsat = [d for d in deltas if d["terminal"] == "UNSAT"]
    return sat, unsat

def plot_results(deltas):
    d_props = np.array([d["d_props"] for d in deltas])
    d_taus = np.array([d["d_tau"] for d in deltas])
    d_footprints = np.array([d["d_footprint"] for d in deltas])
    sat, unsat = split_by_terminal(deltas)

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))

    # 1. ΔY_P
    axs[0, 0].hist(d_props, bins=25, color='royalblue', edgecolor='black', alpha=0.7)
    axs[0, 0].set_title(r'Distribution of $\Delta Y_P$' + '\n(Propagation Deformation)')
    axs[0, 0].set_xlabel(r'$\Delta Y_P$')
    axs[0, 0].set_ylabel('Frequency')
    axs[0, 0].grid(True, linestyle='--', alpha=0.6)

    # 2. ΔY_D (now tau)
    axs[0, 1].hist(d_taus, bins=25, color='seagreen', edgecolor='black', alpha=0.7)
    axs[0, 1].set_title(r'Distribution of $\Delta \tau$' + '\n(Decision / Stopping-Time Deformation)')
    axs[0, 1].set_xlabel(r'$\Delta \tau$')
    axs[0, 1].set_ylabel('Frequency')
    axs[0, 1].grid(True, linestyle='--', alpha=0.6)

    # 3. ΔY_B -> d_footprint
    axs[1, 0].hist(d_footprints, bins=25, color='darkorchid', edgecolor='black', alpha=0.7)
    axs[1, 0].set_title(r'Distribution of $\Delta Y_F$' + '\n(Total Structural Footprint)')
    axs[1, 0].set_xlabel(r'$\Delta Y_F$')
    axs[1, 0].set_ylabel('Frequency')
    axs[1, 0].grid(True, linestyle='--', alpha=0.6)

    # 4. Joint projection (P vs D) - colored by terminal status
    if sat:
        axs[1, 1].scatter([d["d_props"] for d in sat], [d["d_tau"] for d in sat], 
                          color='dodgerblue', alpha=0.6, edgecolors='black', label='SAT')
    if unsat:
        axs[1, 1].scatter([d["d_props"] for d in unsat], [d["d_tau"] for d in unsat], 
                          color='crimson', alpha=0.6, edgecolors='black', label='UNSAT')
    
    axs[1, 1].set_title('Joint Projection Stratified by Terminal State\n' + r'$\Delta Y_P$ vs $\Delta \tau$')
    axs[1, 1].set_xlabel(r'$\Delta Y_P$ (Propagation Cost)')
    axs[1, 1].set_ylabel(r'$\Delta \tau$ (Stopping Time Deformation)')
    if sat or unsat:
        axs[1, 1].legend()
    axs[1, 1].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.savefig("orbit_analysis.png", dpi=300)
    print("Saved publication-grade orbit_analysis.png")

def main():
    context = [-10, 14, -22]
    formula = [
        [-1, -2, 3],
        [-3, 4],
        [-4, 5],
        [-2, -5]
    ]
    base_seq = [1, 2, 3, 4]

    kernel = LispKernel()
    try:
        base, deltas = evaluate_orbit(kernel, formula, base_seq, context=context, N=200)
        print("\nBASE EXECUTION:")
        print(base)
        print("\nSUMMARY:")
        print(json.dumps(summarize(deltas), indent=2))
        plot_results(deltas)
    finally:
        kernel.close()

if __name__ == "__main__":
    main()
