import sys
import random

def generate_bmc_cnf(filename, num_steps=500, width=10):
    clauses = []
    def var(t, i):
        return t * width + i + 1

    # Directional constraints (BMC pipeline)
    # Layer t depends ONLY on Layer t-1
    for t in range(num_steps):
        for i in range(width):
            curr = var(t+1, i)
            # Make curr depend on 3 random vars from previous layer
            p1 = var(t, random.randint(0, width-1))
            p2 = var(t, random.randint(0, width-1))
            p3 = var(t, random.randint(0, width-1))
            # Clause: curr v -p1 v -p2 v -p3
            clauses.append([curr, -p1, -p2, -p3])
            # Clauses: -curr v p1, -curr v p2, -curr v p3
            clauses.append([-curr, p1])
            clauses.append([-curr, p2])
            clauses.append([-curr, p3])

    num_vars = (num_steps + 1) * width
    with open(filename, 'w') as f:
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for clause in clauses:
            f.write(" ".join(map(str, clause)) + " 0\n")

if __name__ == "__main__":
    generate_bmc_cnf("bmc_crypto_benchmarks/simulated_bmc.cnf", num_steps=500, width=10)
