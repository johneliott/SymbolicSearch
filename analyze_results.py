import csv

def main():
    total = 0
    successful = 0
    init_conflict = 0
    
    tau_vars = []
    eta_vars = []
    
    null_hyp = 0
    directional = 0
    explosive = 0
    
    with open('experiment_results.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row['status'] == 'init_conflict':
                init_conflict += 1
            elif row['status'] == 'success':
                successful += 1
                try:
                    tau_var = float(row['tau_var'])
                    eta_var = float(row['eta_var'])
                except ValueError:
                    continue
                    
                tau_vars.append(tau_var)
                eta_vars.append(eta_var)
                
                if tau_var < 0.01 and eta_var < 0.01:
                    null_hyp += 1
                elif tau_var >= 0.01:
                    directional += 1
                elif tau_var < 0.01 and eta_var >= 0.01:
                    explosive += 1
                    
    if successful == 0:
        print(f"Total Instances: {total}")
        print(f"Valid Orbits Evaluated: {successful}")
        print(f"Init Conflicts (Skipped): {init_conflict}\n")
        print("No successful evaluations to summarize.")
        return

    print(f"Total Instances: {total}")
    print(f"Valid Orbits Evaluated: {successful}")
    print(f"Init Conflicts (Skipped): {init_conflict}\n")

    print("=== Metric Distributions ===")
    print(f"Mean Var(tau): {sum(tau_vars)/len(tau_vars):.4f}")
    print(f"Max Var(tau):  {max(tau_vars):.4f}")
    print(f"Mean Var(eta): {sum(eta_vars)/len(eta_vars):.4f}")
    print(f"Max Var(eta):  {max(eta_vars):.4f}\n")

    print("=== Structural Phenotypes ===")
    print(f"1. Isotropic/Null Hypothesis (Var(tau) ≈ 0, Var(eta) ≈ 0): {null_hyp} ({null_hyp/successful*100:.1f}%)")
    print(f"2. Path-Dependent/Directional (Var(tau) > 0): {directional} ({directional/successful*100:.1f}%)")
    print(f"3. Cascade-Dense/Explosive (Var(tau) ≈ 0, Var(eta) > 0): {explosive} ({explosive/successful*100:.1f}%)")

if __name__ == '__main__':
    main()
