# File for processing ndjson files

import json
import sys
from tqdm import tqdm


def filter_ndjson_by_language(input_path, output_path, language_code):
    filtered_lines = []
    with open(input_path, 'r', encoding='utf-8') as infile:
        for line in tqdm(infile, desc="searching..."):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get('language') == language_code or obj.get('language_detected') == language_code:
                filtered_lines.append(json.dumps(obj, ensure_ascii=False) + '\n')
    if filtered_lines:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.writelines(filtered_lines)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Use: python data_processing.py <input.ndjson> <output.ndjson> <language_code>")
        sys.exit(1)
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    language_code = sys.argv[3]
    filter_ndjson_by_language(input_path, output_path, language_code)
