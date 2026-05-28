import os
import math
import numpy as np
import matplotlib.pyplot as plt

from preprocessor import (
    parse_cnf_file,
    construct_variable_incidence_graph,
    find_pure_literals,
    extract_connected_k_cluster_via_bfs,
    polarity_assignment,
    generate_symmetric_group_orbit
)
from harness import LispKernel, evaluate_orbit

def evaluate_and_plot(cnf_path, k, title, ax):
    print(f"Processing {cnf_path}...")
    formula = parse_cnf_file(cnf_path)
    variable_incidence_graph, global_degree = construct_variable_incidence_graph(formula)
    cluster_variables = extract_connected_k_cluster_via_bfs(variable_incidence_graph, global_degree, k)
    pure_literals = find_pure_literals(formula)
    m_ref = polarity_assignment(formula, cluster_variables)
    orbit = generate_symmetric_group_orbit(m_ref)
    
    kernel = LispKernel()
    try:
        base, deltas = evaluate_orbit(kernel, formula, m_ref, orbit, context=pure_literals)
        if not deltas:
            print("INIT CONFLICT")
            return
        
        taus = [d["tau"] for d in deltas]
        etas = [d["eta"] for d in deltas]
        
        tau_mean = np.mean(taus)
        tau_var = np.var(taus)
        eta_mean = np.mean(etas)
        eta_var = np.var(etas)
        
        cv_eta = np.sqrt(eta_var) / eta_mean if eta_mean > 0 else 0
        
        print(f"  Var(tau): {tau_var:.4f}")
        print(f"  Var(eta): {eta_var:.4f}")
        print(f"  CV(eta):  {cv_eta:.4f}")
        
        # Add a little jitter for the scatter plot to make overlapping points visible
        jitter_taus = taus + np.random.normal(0, 0.05, len(taus))
        jitter_etas = etas + np.random.normal(0, 0.05 * (np.max(etas) - np.min(etas) + 0.1), len(etas))

        ax.scatter(jitter_taus, jitter_etas, alpha=0.5, edgecolors='none', color='dodgerblue')
        ax.set_title(f"{title}\nVar(tau)={tau_var:.4f}, CV(eta)={cv_eta:.4f}")
        ax.set_xlabel(r'$\tau$ (Stopping Time)')
        ax.set_ylabel(r'$\eta$ (Propagation Velocity)')
        ax.grid(True, linestyle='--', alpha=0.6)
        
    finally:
        kernel.close()

def main():
    fig, axs = plt.subplots(1, 3, figsize=(18, 6))
    
    # 1. AES
    evaluate_and_plot("bmc_crypto_benchmarks/aes-cnf-gen/aes_1_round_clean.cnf", 5, "Cryptographic SAT (AES-128)\nIsotropic Profile", axs[0])
    
    # 2. BMC
    evaluate_and_plot("bmc_crypto_benchmarks/simulated_bmc.cnf", 5, "Bounded Model Checking\nCascade-Dense Profile", axs[1])
    
    # 3. Random 3-SAT
    evaluate_and_plot("generate_cnf_files/cnf/large/large_50vars_250clauses_000.cnf", 7, "Random 3-SAT\nPath-Dependent Profile", axs[2])
    
    plt.tight_layout()
    plt.savefig("thesis_defense_orbits.png", dpi=300)
    print("\nSaved thesis_defense_orbits.png")

if __name__ == "__main__":
    main()
