import os
import random
import numpy as np
import networkx as nx
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
from harness import LispKernel, evaluate_orbit, summarize

def generate_3xor_cnf(mu, seed, n=100, m=300):
    random.seed(seed)
    clauses = []
    
    ca = list(range(1, (n//2) + 1))
    cb = list(range((n//2) + 1, n + 1))
    
    for _ in range(m):
        is_mixed = random.random() < mu
        if not is_mixed:
            if random.random() < 0.5:
                vars = random.sample(ca, 3)
            else:
                vars = random.sample(cb, 3)
        else:
            if random.random() < 0.5:
                vars = random.sample(ca, 2) + random.sample(cb, 1)
            else:
                vars = random.sample(ca, 1) + random.sample(cb, 2)
                
        # Random RHS
        rhs = random.randint(0, 1)
        x, y, z = vars
        
        if rhs == 0:
            clauses.append([-x, -y, -z])
            clauses.append([-x,  y,  z])
            clauses.append([ x, -y,  z])
            clauses.append([ x,  y, -z])
        else:
            clauses.append([ x,  y,  z])
            clauses.append([ x, -y, -z])
            clauses.append([-x,  y, -z])
            clauses.append([-x, -y,  z])
            
    os.makedirs("bmc_crypto_benchmarks/xor_cnfs", exist_ok=True)
    filename = f"bmc_crypto_benchmarks/xor_cnfs/xor_mu_{mu:.2f}_seed_{seed}.cnf"
    with open(filename, "w") as f:
        f.write(f"p cnf {n} {len(clauses)}\n")
        for c in clauses:
            f.write(" ".join(map(str, c)) + " 0\n")
            
    return filename

def compute_spectral_gap(formula, n=100):
    G = nx.Graph()
    G.add_nodes_from(range(1, n + 1))
    for clause in formula:
        vars_in_clause = list(set([abs(l) for l in clause]))
        for i in range(len(vars_in_clause)):
            for j in range(i+1, len(vars_in_clause)):
                u = vars_in_clause[i]
                v = vars_in_clause[j]
                if G.has_edge(u, v):
                    G[u][v]['weight'] += 1
                else:
                    G.add_edge(u, v, weight=1)
                    
    # Normalized Laplacian L = I - D^{-1/2} A D^{-1/2}
    L = nx.normalized_laplacian_matrix(G).todense()
    eigenvalues = np.sort(np.linalg.eigvalsh(L))
    
    if len(eigenvalues) >= 2:
        return eigenvalues[1] # lambda_2
    return 0.0

def process_instance(mu, seed, k=6):
    cnf_path = generate_3xor_cnf(mu, seed)
    formula = parse_cnf_file(cnf_path)
    
    gamma = compute_spectral_gap(formula)
    
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
        
        stats = summarize(deltas)
        v_orbit = stats["tau_var"] + stats["eta_var"]
        
        return {
            "mu": mu,
            "seed": seed,
            "gamma": gamma,
            "v_orbit": v_orbit,
            "tau_var": stats["tau_var"],
            "eta_var": stats["eta_var"]
        }
    finally:
        kernel.close()

def main():
    mu_values = np.arange(0.00, 0.51, 0.05)
    seeds_per_mu = 30
    k = 6
    
    tasks = []
    for mu in mu_values:
        for seed in range(seeds_per_mu):
            tasks.append((mu, seed))
            
    results = []
    print(f"Running spectral experiment: {len(tasks)} instances...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_task = {executor.submit(process_instance, mu, seed, k): (mu, seed) for mu, seed in tasks}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_task)):
            res = future.result()
            if res:
                results.append(res)
            print(f"[{i+1}/{len(tasks)}] Done.")
            
    # Save results
    with open("spectral_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["mu", "seed", "gamma", "v_orbit", "tau_var", "eta_var"])
        writer.writeheader()
        for r in results:
            writer.writerow(r)
            
    # Plotting
    gammas = [r["gamma"] for r in results]
    v_orbits = [r["v_orbit"] for r in results]
    mus = [r["mu"] for r in results]
    
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(gammas, v_orbits, c=mus, cmap='coolwarm', alpha=0.7, edgecolors='k')
    plt.colorbar(scatter, label=r'Mixing Parameter ($\mu$)')
    plt.title('Orbit Cloud Volume vs. Static Spectral Gap\nInverse Relationship in Random 3-XOR-SAT')
    plt.xlabel(r'Static Spectral Gap $\gamma$ ($\lambda_2$)')
    plt.ylabel(r'Orbit Cloud Volume $V_{orbit}$ (Var($\tau$) + Var($\eta$))')
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig("spectral_gap_inverse_relationship.png", dpi=300)
    print("Saved spectral_gap_inverse_relationship.png")

if __name__ == "__main__":
    main()
