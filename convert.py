import json
import re
import argparse
import sys

types = {
    "Rename Class" : "ClassName",
    "Rename Variable" : "VariableName",
    "Rename Parameter" : "ParameterName",
    "Rename Attribute" : "FieldName",
    "Rename Method" : "MethodName"
}
def main():
    parser = argparse.ArgumentParser(
        description='Convert oracle JSON data to seed converted format',
        epilog='Example: python convert.py -i oracle.json -o rename.json',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-i', '--input', 
                       default='oracle.json',
                       help='Input JSON file path (default: oracle.json)')
    parser.add_argument('-o', '--output', 
                       default='rename.json',
                       help='Output JSON file path (default: rename.json)')
    
    args = parser.parse_args()
    
    try:
        with open(args.input, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file '{args.input}': {e}", file=sys.stderr)
        sys.exit(1)
    res = []

    # for itemSet in data:
    #     for refactoring_change in itemSet["refactoring_changes"]:
    #         old_name = ''
    #         new_name = ''
    #
    #         if refactoring_change['type'] == 'Rename Class':
    #                 match = re.search(r"Rename Class .*\.([A-Za-z0-9_]+) renamed to .*\.([A-Za-z0-9_]+)", refactoring_change['description'])
    #                 if match:
    #                     old_name = match.group(1)
    #                     new_name = match.group(2)
    #
    #         elif refactoring_change['type'] == 'Rename Method':
    #                 match = re.search(r"Rename Method .*? ([A-Za-z0-9_]+)\(.*?\)\s*:\s*.*? renamed to .*? ([A-Za-z0-9_]+)\(", refactoring_change['description'])
    #                 if match:
    #                     old_name = match.group(1)
    #                     new_name = match.group(2)
    #
    #         elif refactoring_change['type'] == 'Rename Variable':
    #                 match = re.search(r"Rename Variable ([A-Za-z0-9_]+) ?: .*? to ([A-Za-z0-9_]+) ?: .*?", refactoring_change['description'])
    #                 if match:
    #                     old_name = match.group(1)
    #                     new_name = match.group(2)
    #
    #         elif refactoring_change['type'] == 'Rename Attribute':
    #                 match = re.search(r"Rename Attribute ([A-Za-z0-9_]+) ?: .*? to ([A-Za-z0-9_]+) ?: .*? in class", refactoring_change['description'])
    #                 if match:
    #                     old_name = match.group(1)
    #                     new_name = match.group(2)
    #
    #         elif refactoring_change['type'] == 'Rename Parameter':
    #                 match = re.search(r"Rename Parameter ([A-Za-z0-9_]+) ?: .*? to ([A-Za-z0-9_]+) ?: .*? in method", refactoring_change['description'])
    #                 if match:
    #                     old_name = match.group(1)
    #                     new_name = match.group(2)
    #
    #         res.append({
    #          "type": refactoring_change["type"],
    #          "commit": itemSet["v2_hash"],
    #          "oldname": old_name,
    #          "newname": new_name,
    #          "typeOfIdentifier": types[refactoring_change["type"]],
    #          "line": refactoring_change["leftSideLocations"][0]["startLine"],
    #          "files": refactoring_change["leftSideLocations"][0]["filePath"].replace("/", r"\/")
    #     })

    for itemSet in data:
        old_name = ''
        new_name = ''

        if itemSet['seed_example']['type'] == 'Rename Class':
            match = re.search(r"Rename Class .*\.([A-Za-z0-9_]+) renamed to .*\.([A-Za-z0-9_]+)",
                              itemSet['seed_example']['description'])
            if match:
                old_name = match.group(1)
                new_name = match.group(2)

        elif itemSet['seed_example']['type'] == 'Rename Method':
            match = re.search(
                r"Rename Method .*? ([A-Za-z0-9_]+)\(.*?\)\s*:\s*.*? renamed to .*? ([A-Za-z0-9_]+)\(",
                itemSet['seed_example']['description'])
            if match:
                old_name = match.group(1)
                new_name = match.group(2)

        elif itemSet['seed_example']['type'] == 'Rename Variable':
            match = re.search(r"Rename Variable ([A-Za-z0-9_]+) ?: .*? to ([A-Za-z0-9_]+) ?: .*?",
                              itemSet['seed_example']['description'])
            if match:
                old_name = match.group(1)
                new_name = match.group(2)

        elif itemSet['seed_example']['type'] == 'Rename Attribute':
            match = re.search(r"Rename Attribute ([A-Za-z0-9_]+) ?: .*? to ([A-Za-z0-9_]+) ?: .*? in class",
                              itemSet['seed_example']['description'])
            if match:
                old_name = match.group(1)
                new_name = match.group(2)

        elif itemSet['seed_example']['type'] == 'Rename Parameter':
            match = re.search(r"Rename Parameter ([A-Za-z0-9_]+) ?: .*? to ([A-Za-z0-9_]+) ?: .*? in method",
                              itemSet['seed_example']['description'])
            if match:
                old_name = match.group(1)
                new_name = match.group(2)

        res.append({
            "type": itemSet['seed_example']["type"],
            "commit": itemSet["v2_hash"],
            "oldname": old_name,
            "newname": new_name,
            "typeOfIdentifier": types[itemSet['seed_example']["type"]],
            "line": itemSet['seed_example']["leftSideLocations"][0]["startLine"],
            "files": itemSet['seed_example']["leftSideLocations"][0]["filePath"].replace("/", r"\/")
        })

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json_str = json.dumps(res, indent=4, ensure_ascii=False) 
            json_str = json_str.replace("\\/", "/")  
            f.write(json_str)
        print(f"Successfully converted data from '{args.input}' to '{args.output}'")
    except IOError as e:
        print(f"Error: Could not write to output file '{args.output}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()