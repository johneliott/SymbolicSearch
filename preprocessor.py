import itertools
import sys
import json

'''
1. parses raw .cnf file to extract formula
2. constructs variable incidence graph (VIG)
3. extracts connected k-cluster (k=4,5,6,7) via BFS
4. passes formula and complete exhaustive orbit S_k to Lisp
4a. deterministic polarity assignment (determine its reference polarity by counting its literal occurrences within the cluster's local clause neighborhood and assign the variable the polarity thats more frequent!!!) and the reference macro sequence m_ref is the ordered list of these k signed literals!!!
4b. orbit generation (generate the set of k! (unique) permutations of the reference macro sequence m_ref; ONLY THE SEQUENCE ORDERING WILL CHANGE ACROSS PERMUTATIONS!!! THE LITERAL POLARITIES WILL STAY THE SAME ACROSS ALL k! VARIANTS!!!)
5a. output a JSON object with the following keys: metadata (dictionary with the source_benchmark filename, k_size, orbit_cardinality, and reference_macro m_ref); context: a list of literals representing the background assignment (A_0); formula (raw CNF structure); orbit (list of lists, each sub-list is one permutation of the macro literals)

IDENTIFY A TIGHTLY-COUPLED CLUSTER OF k LITERALS AND GENERATE THE COMPLETE SYMMETRIC GROUP ORBIT S_k FOR THESE LITERALS!!! (which ensures a high-density structural probe of the formula)
'''

# format of the cnf files is: c for comment; p for problem line/specification, ignore both lines when parsing raw .cnf files to extract the formula
def parse_cnf_file(cnf_file_path):
    formula = []

    with open(cnf_file_path) as cnf_file:
        for line in cnf_file:
            if (line.startswith("c") or line.startswith("p")):
                continue
            else:
                # clean up each line with a clause in it and remove the 0 for end of clause in cnf formatting
                clause = list(map(int, line.strip().split()))
                clause = [x for x in clause if x != 0]

                if (clause != []):
                    formula.append(clause)

    return formula



# BUILDS THE GRAPH FOR EACH VARIABLE TO ITS NEIGHBORING VARIABLE(S)/EDGES AND ALSO CALCULATES GLOBAL DEGREE OF EACH VARIABLE (total number of clause appearances across the formula)
def find_pure_literals(formula):
    pos = set()
    neg = set()
    for clause in formula:
        for lit in clause:
            if lit > 0:
                pos.add(lit)
            else:
                neg.add(abs(lit))
    pure_pos = pos - neg
    pure_neg = neg - pos
    pure_literals = list(pure_pos) + [-x for x in pure_neg]
    return sorted(pure_literals, key=lambda x: (abs(x), x))

def construct_variable_incidence_graph(formula):
    # nodes V = variables
    # edges E = co-occurrence in at least 1 clause
    # variable_incidence_graph is a dictionary --> key is a variable and the value is the set of variables it has at least 1 edge with (aka is in the same clause at least 1x with the variable(s)) 
    # {variable : set of neighboring variable(s)}
    variable_incidence_graph = {}
    
    # global_degree is also a dictionary but maps the key (variable) to the total number of clause appearances across the formula
    global_degree = {}

    for clause in formula:
        # remove polarity of each variable
        vars_in_clause = sorted(list(set(abs(x) for x in clause)))
        
        for var in vars_in_clause:
            # make the value a set to avoid duplicates for all the variables each variable is connected to if it isn't already being tracked in the graph yet
            variable_incidence_graph.setdefault(var, set())

            # add all the variables in the clause (that isn't the current variable) to the variable_incidence_graph to track which variables share edges
            for shared_edge_var in vars_in_clause:
                if (var != shared_edge_var):
                    variable_incidence_graph[var].add(shared_edge_var)

            # add/increment the count for the number of clauses each variable is present in
            global_degree[var] = global_degree.get(var, 0) + 1

    return variable_incidence_graph, global_degree


# get the cluster with the most connections using BFS -- has a fixed k value
def extract_connected_k_cluster_via_bfs(variable_incidence_graph, global_degree, k):
    # always is the first index/occurrence of the highest global degree even if it's tied?
    # YES!!! since the entire macro extraction pipeline must be deterministic!!!
    seed_variable_key = min(global_degree.keys(), key=lambda x: (-global_degree[x], x))

    # EXECUTE BFS FROM THE SEED VARIABLE!!!
    cluster_variables = []
    # no duplicates in visited
    visited_variables = set()

    queue = [seed_variable_key]
    visited_variables.add(seed_variable_key)

    while queue and len(cluster_variables) < k:
        current_node = queue.pop(0)
        cluster_variables.append(current_node)

        # the cluster has reached k unique variables, so terminate search ASAP
        if (len(cluster_variables) == k):
            break

        # track all neighbors that haven't been visited yet and sort by highest degree
        neighbors = [n for n in variable_incidence_graph.get(current_node, []) if n not in visited_variables]
        neighbors.sort(key=lambda x: (-global_degree[x], x))

        # go through each neighboring variable in the list from highest to lowest degree and if it's not been visited yet, add it to the visited list and add it to the queue of variables to check
        for neighbor in neighbors:
            if neighbor not in visited_variables:
                visited_variables.add(neighbor)
                queue.append(neighbor)


    # sanity check in case the cluster is too small/aren't enough variables for a macro of size k
    if (len(cluster_variables) < k):
        print("Cluster size/length (%d) is smaller than k value (%d)." % (len(cluster_variables), k))
        exit()

    return cluster_variables


# assign polarity for each variable in the cluster based on the frequency of the polarity of each variable in the original formula!!! if true count = false count, variable value will be true to ensure deterministic outcomes across the same input CNF file and k value
def polarity_assignment(formula, cluster_variables):
    local_clause_neighborhood = {}

    for clause in formula:
        for literal in clause:
            local_clause_neighborhood[literal] = local_clause_neighborhood.get(literal, 0) + 1

    m_ref = []
    for var in cluster_variables:
        true_count = local_clause_neighborhood.get(var, 0)
        false_count = local_clause_neighborhood.get(-var, 0)

        if (true_count >= false_count):
            m_ref.append(var)
        else:
            m_ref.append(-var)

    return m_ref


# all permutations of the reference macro sequence -- LIST OF LISTS
def generate_symmetric_group_orbit(m_ref):
    # removed this and made orbit a list of lists instead of a list of tuples since that's how it'll be returned in the final output --> JSON
    # orbit = list(itertools.permutations(m_ref))
    orbit = [list(permutation) for permutation in itertools.permutations(m_ref)]
    return orbit


# outputs a JSON object with the following keys: metadata (dictionary with the source_benchmark filename, k_size, orbit_cardinality, and reference_macro m_ref); context: a list of literals representing the background assignment (A_0) (initialized now to an empty list); formula (raw CNF structure); orbit (list of lists, each sub-list is one permutation of the macro literals)
def output_JSON(cnf_file_path, k, orbit, m_ref, formula, context):
    output_payload = {
        "metadata" : {
            "source_benchmark": cnf_file_path,
            "k_size": k,
            "orbit_cardinality": len(orbit),
            "m_ref": m_ref
        },
        "context": context,
        "formula": formula,
        "orbit": orbit
    }

    return output_payload


def main():
# # Target: 
# python preprocessor.py bench_01.cnf 7
    if (len(sys.argv) < 3):
        print("Correct usage: python preprocessor.py <path_to_benchmark.cnf>, <k_size>")
        sys.exit(1)

    cnf_file_path = sys.argv[1]
    k = int(sys.argv[2])

    formula = parse_cnf_file(cnf_file_path)

    variable_incidence_graph, global_degree = construct_variable_incidence_graph(formula)

    pure_literals = find_pure_literals(formula)

    cluster_variables = extract_connected_k_cluster_via_bfs(variable_incidence_graph, global_degree, k)

    m_ref = polarity_assignment(formula, cluster_variables)

    orbit = generate_symmetric_group_orbit(m_ref)

    output_payload = output_JSON(cnf_file_path, k, orbit, m_ref, formula, pure_literals)


    new_output_file_path = "pipeline_output_payload.json"
    with open(new_output_file_path, "w", encoding='utf-8') as new_json_file:
        json.dump(output_payload, new_json_file, indent=2)

if __name__ == "__main__":
    main()
