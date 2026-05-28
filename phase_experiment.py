import os
import random
import numpy as np
import concurrent.futures
import csv
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

def generate_random_3sat_cnf(n, m, seed, filename):
    random.seed(seed)
    seen = set()
    clauses = []
    while len(seen) < m:
        # Uniform random selection of 3 distinct variables, each negated with 50% probability
        c = tuple((2 * random.randint(0, 1) - 1) * x for x in sorted(random.sample(range(1, n + 1), 3)))
        if c in seen:
            continue
        clauses.append(c)
        seen.add(c)
        
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {m}\n")
        for c in clauses:
            f.write(" ".join(map(str, c)) + " 0\n")
    return filename

def process_instance(alpha, seed, k=6, n=100):
    m = int(alpha * n)
    cnf_path = f"bmc_crypto_benchmarks/phase_cnfs/rand_n{n}_m{m}_seed{seed}.cnf"
    generate_random_3sat_cnf(n, m, seed, cnf_path)
    
    formula = parse_cnf_file(cnf_path)
    variable_incidence_graph, global_degree = construct_variable_incidence_graph(formula)
    try:
        cluster_variables = extract_connected_k_cluster_via_bfs(variable_incidence_graph, global_degree, k)
    except SystemExit:
        return None
        
    m_ref = polarity_assignment(formula, cluster_variables)
    orbit = generate_symmetric_group_orbit(m_ref)
    context = find_pure_literals(formula)
    
    kernel = LispKernel()
    try:
        base, deltas = evaluate_orbit(kernel, formula, m_ref, orbit, context=context)
        if not deltas:
            return None
        
        taus = [d["tau"] for d in deltas]
        etas = [d["eta"] for d in deltas]
        
        cov_matrix = np.cov(taus, etas)
        # If the covariance matrix is 0-dimensional (e.g. invalid), determinant fails
        if cov_matrix.ndim == 2:
            v_orbit = np.linalg.det(cov_matrix)
        else:
            v_orbit = 0.0
            
        v_orbit = max(0.0, float(v_orbit))
        
        return {
            "alpha": alpha,
            "seed": seed,
            "v_orbit": v_orbit,
            "tau_var": float(np.var(taus)),
            "eta_var": float(np.var(etas))
        }
    finally:
        kernel.close()

def main():
    alphas = []
    for a in np.arange(3.0, 3.79, 0.2): alphas.append(round(a, 2))
    for a in np.arange(3.8, 4.81, 0.05): alphas.append(round(a, 2))
    for a in np.arange(5.0, 6.1, 0.2): alphas.append(round(a, 2))
    
    seeds_per_alpha = 50
    k = 6
    n = 100
    
    tasks = []
    for alpha in alphas:
        for seed in range(seeds_per_alpha):
            tasks.append((alpha, seed))
            
    results = []
    print(f"Running Phase Transition 'Breathing Mode' experiment: {len(tasks)} instances...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_task = {executor.submit(process_instance, alpha, seed, k, n): (alpha, seed) for alpha, seed in tasks}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_task)):
            res = future.result()
            if res:
                results.append(res)
            if (i + 1) % 100 == 0 or (i + 1) == len(tasks):
                print(f"[{i+1}/{len(tasks)}] Done.")
                
    # Save results
    with open("phase_transition_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["alpha", "seed", "v_orbit", "tau_var", "eta_var"])
        writer.writeheader()
        for r in results:
            writer.writerow(r)
            
    # Plotting
    plt.figure(figsize=(12, 7))
    
    # Scatter all points
    plt.scatter([r["alpha"] for r in results], [r["v_orbit"] for r in results], 
                color='gray', alpha=0.3, s=15, label='Instance Cloud Volume')
    
    # Calculate means and stds
    unique_alphas = sorted(list(set([r["alpha"] for r in results])))
    means = []
    stds = []
    for a in unique_alphas:
        vols = [r["v_orbit"] for r in results if r["alpha"] == a]
        if vols:
            means.append(np.mean(vols))
            stds.append(np.std(vols))
        else:
            means.append(0)
            stds.append(0)
            
    means = np.array(means)
    stds = np.array(stds)
    
    plt.plot(unique_alphas, means, color='crimson', linewidth=2, label='Mean $V_{orbit}$')
    plt.fill_between(unique_alphas, np.clip(means - stds, 0, None), means + stds, color='crimson', alpha=0.2, label=r'$\pm 1$ Std Dev')
    
    plt.axvline(x=4.26, color='black', linestyle='--', label=r'Theoretical Phase Transition ($\alpha \approx 4.26$)')
    
    plt.title('Phase Transition Breathing Mode\nOrbit Phase Volume ($V_{orbit}$) vs. Clause Density ($\\alpha$)')
    plt.xlabel(r'Clause Density $\alpha = M/N$')
    plt.ylabel(r'Orbit Phase Volume $V_{orbit}$ = det($\Sigma$)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig("phase_transition_breathing_mode.png", dpi=300)
    print("\nSaved phase_transition_breathing_mode.png")

if __name__ == "__main__":
    main()
