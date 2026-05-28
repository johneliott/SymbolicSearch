import os
import json
import csv
from preprocessor import (
    parse_cnf_file,
    construct_variable_incidence_graph,
    find_pure_literals,
    extract_connected_k_cluster_via_bfs,
    polarity_assignment,
    generate_symmetric_group_orbit
)
from harness import LispKernel, evaluate_orbit, summarize

def evaluate(cnf_path, k=5):
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
            return None
        stats = summarize(deltas)
        stats['file'] = os.path.basename(cnf_path)
        stats['k'] = k
        return stats
    finally:
        kernel.close()

results = []
results.append(evaluate("bmc_crypto_benchmarks/aes-cnf-gen/aes_1_round_clean.cnf", 5))
results.append(evaluate("bmc_crypto_benchmarks/simulated_bmc.cnf", 5))

for r in results:
    if r:
        print(f"\n{r['file']}:")
        print(f"  Var(tau): {r['tau_var']:.4f}")
        print(f"  Var(eta): {r['eta_var']:.4f}")
