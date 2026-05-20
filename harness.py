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
        payload = json.dumps({"formula": formula, "sequence": list(seq)})
        self.process.stdin.write(payload + "\n")
        self.process.stdin.flush()
        
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read()
            raise RuntimeError(f"Lisp kernel crashed or closed stdout unexpectedly.\nStderr: {stderr}")
            
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to decode JSON from Lisp script. Output was: {line}")

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
        out = []
        for _ in range(N):
            p = list(seq)
            random.shuffle(p)
            out.append(tuple(p))
        return out

def evaluate_orbit(kernel, formula, base_seq, N=500):
    base = kernel.run_sequence(formula, base_seq)
    deltas = []
    
    samples = sample_permutations(base_seq, N)
    print(f"Evaluating orbit with {len(samples)} samples...")
    for pi in samples:
        result = kernel.run_sequence(formula, pi)
        delta = {
            "perm": pi,
            "d_props": result["props"] - base["props"],
            "d_decisions": result["decisions"] - base["decisions"],
        }
        deltas.append(delta)
    return base, deltas

def summarize(deltas):
    d_props = np.array([d["d_props"] for d in deltas])
    return {
        "mean": float(np.mean(d_props)),
        "var": float(np.var(d_props)),
        "min": int(np.min(d_props)),
        "max": int(np.max(d_props)),
        "skew_proxy": float(np.mean(np.abs(d_props)))
    }

def plot_results(deltas):
    d_props = [d["d_props"] for d in deltas]
    d_decisions = [d["d_decisions"] for d in deltas]

    fig, axs = plt.subplots(1, 3, figsize=(18, 6))

    # 1. Distribution of Delta Y_P
    axs[0].hist(d_props, bins=20, color='royalblue', edgecolor='black', alpha=0.7)
    axs[0].set_title(r'Distribution of $\Delta Y_P$' + '\n(Propagation Sensitivity)')
    axs[0].set_xlabel(r'$\Delta Y_P$ (Change in Propagation Events)')
    axs[0].set_ylabel('Frequency')
    axs[0].grid(True, linestyle='--', alpha=0.6)

    # 2. Distribution of Delta Y_D
    axs[1].hist(d_decisions, bins=20, color='seagreen', edgecolor='black', alpha=0.7)
    axs[1].set_title(r'Distribution of $\Delta Y_D$' + '\n(Decision Sensitivity)')
    axs[1].set_xlabel(r'$\Delta Y_D$ (Change in Stopping Time)')
    axs[1].set_ylabel('Frequency')
    axs[1].grid(True, linestyle='--', alpha=0.6)

    # 3. Joint Distribution
    axs[2].scatter(d_props, d_decisions, color='crimson', alpha=0.6, edgecolors='black')
    axs[2].set_title('Joint Distribution\n' + r'$\Delta Y_P$ vs $\Delta Y_D$')
    axs[2].set_xlabel(r'$\Delta Y_P$ (Propagation Cost)')
    axs[2].set_ylabel(r'$\Delta Y_D$ (Decision Cost)')
    axs[2].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.savefig('orbit_analysis.png', dpi=300)
    print("Saved publication-grade plot to orbit_analysis.png")

def main():
    formula = [
        [-1, -2, 3],
        [-3, 4],
        [-4, 5],
        [-2, -5]
    ]
    # For a macro sequence [1, 2, 3, 4], the permutation sensitivity can be analyzed
    base_seq = [1, 2, 3, 4]

    kernel = LispKernel()
    try:
        base, deltas = evaluate_orbit(kernel, formula, base_seq, N=100)
        summary = summarize(deltas)
        
        print("\nBase Execution:", base)
        print("\nOrbit Summary:")
        print(json.dumps(summary, indent=2))
        
        plot_results(deltas)
    finally:
        kernel.close()

if __name__ == "__main__":
    main()
