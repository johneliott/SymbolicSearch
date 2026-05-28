import sys
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
            stderr=sys.stderr,
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

def evaluate_orbit(kernel, formula, base_seq, samples, context=None):
    base = kernel.run_sequence(formula, base_seq, context)
    if base.get("status") == "init_conflict":
        print("Context is inherently contradictory. Skipping orbit evaluation.")
        return base, []

    deltas = []
    
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
            "eta": result["props"] / current_tau if current_tau > 0 else 0.0,
            
            # Terminal stratification
            "terminal": result.get("status", "UNKNOWN").upper(),
        })
    return base, deltas

def summarize(deltas):
    raw_taus = np.array([d["tau"] for d in deltas])
    raw_etas = np.array([d["eta"] for d in deltas])
    
    return {
        # Core Hypotheses: Measure structural permutation sensitivity directly
        "tau_mean": float(np.mean(raw_taus)),
        "tau_var": float(np.var(raw_taus)),  # <--- This is your primary Var(τ) metric!
        
        # Propagation deformation metrics
        "eta_mean": float(np.mean(raw_etas)),
        "eta_var": float(np.var(raw_etas)),
    }

def split_by_terminal(deltas):
    sat = [d for d in deltas if d["terminal"] == "SAT"]
    unsat = [d for d in deltas if d["terminal"] == "UNSAT"]
    return sat, unsat

def plot_results(deltas):
    raw_taus = np.array([d["tau"] for d in deltas])
    raw_etas = np.array([d["eta"] for d in deltas])
    sat, unsat = split_by_terminal(deltas)

    fig, axs = plt.subplots(1, 3, figsize=(18, 5))

    # 1. Eta
    axs[0].hist(raw_etas, bins=25, color='royalblue', edgecolor='black', alpha=0.7)
    axs[0].set_title(r'Distribution of $\eta$' + '\n(Propagation Velocity)')
    axs[0].set_xlabel(r'$\eta$')
    axs[0].set_ylabel('Frequency')
    axs[0].grid(True, linestyle='--', alpha=0.6)

    # 2. Tau
    axs[1].hist(raw_taus, bins=25, color='seagreen', edgecolor='black', alpha=0.7)
    axs[1].set_title(r'Distribution of $\tau$' + '\n(Stopping Time)')
    axs[1].set_xlabel(r'$\tau$')
    axs[1].set_ylabel('Frequency')
    axs[1].grid(True, linestyle='--', alpha=0.6)

    # 3. joint projection
    if sat:
        axs[2].scatter([d["eta"] for d in sat], [d["tau"] for d in sat], 
                          color='dodgerblue', alpha=0.6, edgecolors='black', label='SAT')
    if unsat:
        axs[2].scatter([d["eta"] for d in unsat], [d["tau"] for d in unsat], 
                          color='crimson', alpha=0.6, edgecolors='black', label='UNSAT')
    
    axs[2].set_title('Joint Projection Stratified by Terminal State\n' + r'$\eta$ vs $\tau$')
    axs[2].set_xlabel(r'$\eta$ (Propagation Velocity)')
    axs[2].set_ylabel(r'$\tau$ (Stopping Time)')
    if sat or unsat:
        axs[2].legend()
    axs[2].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.savefig("orbit_analysis.png", dpi=300)
    print("Saved publication-grade orbit_analysis.png")

def main():
    try:
        with open("pipeline_output_payload.json", "r", encoding='utf-8') as f:
            payload = json.load(f)
    except FileNotFoundError:
        print("pipeline_output_payload.json not found. Run preprocessor.py first.")
        return

    context = payload.get("context", [])
    formula = payload["formula"]
    base_seq = payload["metadata"]["m_ref"]
    samples = payload["orbit"]

    kernel = LispKernel()
    try:
        base, deltas = evaluate_orbit(kernel, formula, base_seq, samples, context=context)
        print("\nBASE EXECUTION:")
        print(base)
        
        if deltas:
            print("\nSUMMARY:")
            print(json.dumps(summarize(deltas), indent=2))
            plot_results(deltas)
        else:
            print("\nNo permutations evaluated due to initial context conflict.")
    finally:
        kernel.close()

if __name__ == "__main__":
    main()