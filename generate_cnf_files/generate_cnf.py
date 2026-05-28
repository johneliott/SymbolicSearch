'''
file for generating the small/medium/large cnf files

small: use for debugging --> 
'''


# python3 rand n m k [seed]

import os
import subprocess
import random

# in the same directory, but path to rand.py for generating the CNF files
rand_path = "rand.py"

# base directory for the generated cnf files
base_directory = "cnf"

# make the small/medium/large level directories if they don't exist
for level in ["small", "medium", "large"]:
    os.makedirs(os.path.join(base_directory, level), exist_ok=True)


def generate_instance(vars, clauses, k, output_path, seed):
    cmd = [
        "python3",
        rand_path,
        str(vars),
        str(clauses),
        str(k), # literals per clause
        str(seed),
    ]
    
    with open(output_path, "w") as new_cnf_file:
        subprocess.run(cmd, stdout=new_cnf_file, check=True)



# SMALL CONFIGURATIONS FOR DEBUGGING!!!
small_configs = [
    (3, 5),
    (4, 12),
    (5, 15),
    (6, 15),
    (7, 15),
]

files_per_small_config = 3

for i, (n, m) in enumerate(small_configs):
    for j in range(files_per_small_config):
        # seed needed to sample different random formulas; avoid overfitting
        seed = random.randint(0, 10**6)
        new_cnf_file = f"small_{n}vars_{m}clauses_{j:03d}.cnf"
        new_cnf_path = os.path.join(base_directory, "small", new_cnf_file)

        generate_instance(n, m, 3, new_cnf_path, seed)


# MEDIUM CONFIGURATIONS FOR VALIDATION!!!
medium_configs = [20, 30]
files_per_medium_config = 10

for i, n in enumerate(medium_configs):
    # clause-to-variable ratio
    m = int(4.5 * n)

    for j in range(files_per_medium_config):
        seed = random.randint(0, 10**6)
        new_cnf_file = f"medium_{n}vars_{m}clauses_{j:03d}.cnf"
        new_cnf_path = os.path.join(base_directory, "medium", new_cnf_file)

        generate_instance(n, m, 3, new_cnf_path, seed)


# LARGE CONFIGURATIONS FOR EXPERIMENTS!!!
large_configs = [50, 75, 100]
files_per_large_config = 25

for i, n in enumerate(large_configs):
    # closer to phase transition
    m = int(5.0 * n)

    for j in range(files_per_large_config):
        seed = random.randint(0, 10**6)
        new_cnf_file = f"large_{n}vars_{m}clauses_{j:03d}.cnf"
        new_cnf_path = os.path.join(base_directory, "large", new_cnf_file)

        generate_instance(n, m, 3, new_cnf_path, seed)


print("CNF generation complete.")