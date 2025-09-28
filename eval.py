import json
import re
import argparse
import sys
from collections import defaultdict

types = {
    "Rename Class" : "ClassName",
    "Rename Variable" : "VariableName",
    "Rename Parameter" : "ParameterName",
    "Rename Attribute" : "FieldName",
    "Rename Method" : "MethodName"
}

def parse_oldName_newName(refactoring_change):
    old_name = ''
    new_name = ''

    if refactoring_change['type'] == 'Rename Class':
        match = re.search(r"Rename Class .*\.([A-Za-z0-9_]+) renamed to .*\.([A-Za-z0-9_]+)",
                          refactoring_change['description'])
        if match:
            old_name = match.group(1)
            new_name = match.group(2)

    elif refactoring_change['type'] == 'Rename Method':
        match = re.search(r"Rename Method .*? ([A-Za-z0-9_]+)\(.*?\)\s*:\s*.*? renamed to .*? ([A-Za-z0-9_]+)\(",
                          refactoring_change['description'])
        if match:
            old_name = match.group(1)
            new_name = match.group(2)

    elif refactoring_change['type'] == 'Rename Variable':
        match = re.search(r"Rename Variable ([A-Za-z0-9_]+) ?: .*? to ([A-Za-z0-9_]+) ?: .*?",
                          refactoring_change['description'])
        if match:
            old_name = match.group(1)
            new_name = match.group(2)

    elif refactoring_change['type'] == 'Rename Attribute':
        match = re.search(r"Rename Attribute ([A-Za-z0-9_]+) ?: .*? to ([A-Za-z0-9_]+) ?: .*? in class",
                          refactoring_change['description'])
        if match:
            old_name = match.group(1)
            new_name = match.group(2)

    elif refactoring_change['type'] == 'Rename Parameter':
        match = re.search(r"Rename Parameter ([A-Za-z0-9_]+) ?: .*? to ([A-Za-z0-9_]+) ?: .*? in method",
                          refactoring_change['description'])
        if match:
            old_name = match.group(1)
            new_name = match.group(2)

    return old_name, new_name

def main():
    parser = argparse.ArgumentParser(
        description='Evaluate recommendation performance against oracle data',
        epilog='Example: python eval.py -r recommend.json -o oracle.json --threshold 0.6',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Input files
    parser.add_argument('--recommend', '-r',
                       default='recommend.json',
                       help='Input recommendation JSON file (default: recommend.json)')
    parser.add_argument('--oracle', '-o',
                       default='oracle.json', 
                       help='Input oracle JSON file (default: oracle.json)')
    
    # Output files
    parser.add_argument('--actual-recommend',
                       default='actual_recommend.json',
                       help='Output filtered recommendations file (default: actual_recommend.json)')
    parser.add_argument('--oracle-dict',
                       default='oracle_dict.json',
                       help='Output oracle dictionary file (default: oracle_dict.json)')
    parser.add_argument('--eval-results',
                       default='eval_res.json',
                       help='Output evaluation results file (default: eval_res.json)')
    
    # Evaluation parameters
    parser.add_argument('--threshold', '-t',
                       type=float,
                       default=0.53,
                       help='Score threshold for filtering recommendations (default: 0.53)')
    parser.add_argument('--alpha',
                       type=float,
                       default=0.5,
                       help='Weight for similarity in score calculation (default: 0.5)')
    
    args = parser.parse_args()
    
    # Load recommendation data
    try:
        with open(args.recommend, "r") as f:
            recommend_dict = json.load(f)
    except FileNotFoundError:
        print(f"Error: Recommendation file '{args.recommend}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in recommendation file '{args.recommend}': {e}", file=sys.stderr)
        sys.exit(1)

    actual_recommend = {}
    for key, value in recommend_dict.items():
        renas = value["renas"]
        renas_filtered = {}
        for renas_key, renas_value in renas.items():
            filtered_renas_value = []
            for item in renas_value:
                score = ((args.alpha * item['similarity']) + ((1 - args.alpha) / item['relationship']))
                if score >= args.threshold:
                    filtered_renas_value.append(item)
            renas_filtered[renas_key] = filtered_renas_value
        actual_recommend[key] = renas_filtered

    try:
        with open(args.actual_recommend, "w") as f:
            json.dump(actual_recommend, f)
        print(f"Filtered recommendations saved to '{args.actual_recommend}'")
    except IOError as e:
        print(f"Error: Could not write to '{args.actual_recommend}': {e}", file=sys.stderr)
        sys.exit(1)

    # Processing oracle
    try:
        with open(args.oracle, "r") as f:
            oracle = json.load(f)
    except FileNotFoundError:
        print(f"Error: Oracle file '{args.oracle}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in oracle file '{args.oracle}': {e}", file=sys.stderr)
        sys.exit(1)

    oracle_dict = {}
    for itemSet in oracle:
        res = []
        for refactoring_change in itemSet["refactoring_changes"]:

            old_name, new_name = parse_oldName_newName(refactoring_change)

            res.append({
             "type": refactoring_change["type"],
             "commit": itemSet["v2_hash"],
             "oldname": old_name,
             "newname": new_name,
             "typeOfIdentifier": types[refactoring_change["type"]],
             "line": refactoring_change["leftSideLocations"][0]["startLine"],
             "files": refactoring_change["leftSideLocations"][0]["filePath"]
            })

        seed_oldName, seed_newName = parse_oldName_newName(itemSet['seed_example'])
        seed = {
            "type": itemSet['seed_example']["type"],
            "commit": itemSet["v2_hash"],
            "oldname": seed_oldName,
            "newname": seed_newName,
            "typeOfIdentifier": types[itemSet['seed_example']["type"]],
            "line": itemSet['seed_example']["leftSideLocations"][0]["startLine"],
            "files": itemSet['seed_example']["leftSideLocations"][0]["filePath"]
        }

        output = {
            "seed": seed,
            "data": res
        }
        oracle_dict[itemSet["id"]] = output

    try:
        with open(args.oracle_dict, "w") as f:
            json.dump(oracle_dict, f)
        print(f"Oracle dictionary saved to '{args.oracle_dict}'")
    except IOError as e:
        print(f"Error: Could not write to '{args.oracle_dict}': {e}", file=sys.stderr)
        sys.exit(1)

    def contains_in_ids(_old_name, _ids):
        for _id in _ids:
            if _old_name in _id:
                return True
        return False

    eval_res = {}

    def evaluate(key, oracle, actual):
        true_positive = []
        for o in oracle:
            for a in actual:
                if o['oldname'] == a['name'] and o['line'] == a['line'] and o['files'] == a['files']:
                    true_positive.append(a)

        eval_res[key] = {
            "true_positive": true_positive,
            "oracle": oracle,
            "actual_recommendation": actual
        }

    already_visited = defaultdict(list)
    for oracle_key, oracle_value in oracle_dict.items():
        actual_oracle_value = actual_recommend[oracle_value["seed"]["commit"]]
        for positional_key, recommend_value in actual_oracle_value.items():
            if len(actual_oracle_value) == 1:
                already_visited[oracle_key].append(positional_key)
                evaluate(oracle_key, oracle_value["data"], recommend_value)
            else:
                _ids = [item['id'] for item in recommend_value]
                if positional_key not in already_visited[oracle_key] and contains_in_ids(oracle_value["seed"]['oldname'], _ids):
                    already_visited[oracle_key].append(positional_key)
                    evaluate(oracle_key, oracle_value["data"], recommend_value)



    print(already_visited)
    try:
        with open(args.eval_results, "w") as f:
            json.dump(eval_res, f)
        print(f"Evaluation results saved to '{args.eval_results}'")
    except IOError as e:
        print(f"Error: Could not write to '{args.eval_results}': {e}", file=sys.stderr)
        sys.exit(1)

    for key, value in eval_res.items():
        true_positive_count = len(value["true_positive"]) - 1 if len(value["true_positive"]) > 0 else 0
        oracle_count = len(value["oracle"]) - 1
        actual_recommendation_count = len(value["actual_recommendation"]) - 1
        recall = true_positive_count / oracle_count
        precision = true_positive_count/ actual_recommendation_count
        f1_score = 2 * precision * recall / (precision + recall) if precision + recall != 0 else 0

        print(key, f"captured {true_positive_count}/{oracle_count}" ,f"recall = {recall:.4f} precision = {precision:.4f} f1 = {f1_score:.4f}")


if __name__ == '__main__':
    main()
