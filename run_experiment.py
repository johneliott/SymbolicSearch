import os
import glob
import csv
import concurrent.futures
from preprocessor import (
    parse_cnf_file,
    construct_variable_incidence_graph,
    find_pure_literals,
    extract_connected_k_cluster_via_bfs,
    polarity_assignment,
    generate_symmetric_group_orbit
)
from harness import LispKernel, evaluate_orbit, summarize

def process_cnf_file(cnf_path, k=7):
    formula = parse_cnf_file(cnf_path)
    if not formula:
        return None

    variable_incidence_graph, global_degree = construct_variable_incidence_graph(formula)
    
    # Extract cluster
    try:
        cluster_variables = extract_connected_k_cluster_via_bfs(variable_incidence_graph, global_degree, k)
    except SystemExit:
        return None # In case the cluster size is smaller than k

    pure_literals = find_pure_literals(formula)
    m_ref = polarity_assignment(formula, cluster_variables)
    orbit = generate_symmetric_group_orbit(m_ref)

    kernel = LispKernel()
    try:
        base, deltas = evaluate_orbit(kernel, formula, m_ref, orbit, context=pure_literals)
        if not deltas:
            # Init conflict
            return {
                "file": os.path.basename(cnf_path),
                "k": k,
                "status": "init_conflict",
                "tau_mean": "",
                "tau_var": "",
                "eta_mean": "",
                "eta_var": ""
            }
        
        stats = summarize(deltas)
        return {
            "file": os.path.basename(cnf_path),
            "k": k,
            "status": "success",
            "tau_mean": stats["tau_mean"],
            "tau_var": stats["tau_var"],
            "eta_mean": stats["eta_mean"],
            "eta_var": stats["eta_var"]
        }
    finally:
        kernel.close()

def main():
    k = 7
    cnf_files = glob.glob("generate_cnf_files/cnf/medium/*.cnf") + glob.glob("generate_cnf_files/cnf/large/*.cnf")
    
    results = []
    
    print(f"Starting batch evaluation on {len(cnf_files)} CNF files with k={k}...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_cnf = {executor.submit(process_cnf_file, cnf, k): cnf for cnf in cnf_files}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_cnf)):
            cnf = future_to_cnf[future]
            try:
                res = future.result()
                if res:
                    results.append(res)
                    print(f"[{i+1}/{len(cnf_files)}] Processed {os.path.basename(cnf)} - Status: {res['status']}")
                else:
                    print(f"[{i+1}/{len(cnf_files)}] Skipped {os.path.basename(cnf)} - Cluster too small")
            except Exception as exc:
                print(f"[{i+1}/{len(cnf_files)}] {os.path.basename(cnf)} generated an exception: {exc}")

    csv_file = "experiment_results.csv"
    with open(csv_file, mode='w', newline='') as f:
        fieldnames = ["file", "k", "status", "tau_mean", "tau_var", "eta_mean", "eta_var"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            writer.writerow(res)
            
    print(f"\nExperiment complete. Results saved to {csv_file}")

if __name__ == "__main__":
    main()
