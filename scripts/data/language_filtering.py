# File for processing ndjson files

import argparse
import json
import os
from pathlib import Path
from tqdm import tqdm

# --------- USAGE ------------------------------------------------------------------------------------
# Single file: python language_filtering.py --input-file data.ndjson --output-file filtered.ndjson <lang>
# Directory: python language_filtering.py --input-dir ./data --output-dir ./filtered <lang>
# ----------------------------------------------------------------------------------------------------

def filter_ndjson_by_language(input_path, output_path, language_code):
    filtered_lines = []
    with open(input_path, 'r', encoding='utf-8') as infile:
        for line in tqdm(infile, desc=f'filtering {input_path.name}', unit='lines'):
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


def process_directory(input_dir, output_dir, language_code):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ndjson_files = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == '.ndjson')
    if not ndjson_files:
        raise FileNotFoundError(f'No .ndjson files found in {input_dir}')

    for input_file in tqdm(ndjson_files, desc='processing files', unit='file'):
        output_file = output_dir / input_file.name
        filter_ndjson_by_language(input_file, output_file, language_code)


def main():
    parser = argparse.ArgumentParser(description='Filter NDJSON by language code.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input-file', help='Path to a single input NDJSON file.')
    group.add_argument('--input-dir', help='Path to a directory containing multiple NDJSON files.')
    parser.add_argument('--output-file', help='Path to the output NDJSON file for single-file mode.')
    parser.add_argument('--output-dir', help='Path to the output directory for directory mode.')
    parser.add_argument('language_code', help='Language code to filter by, e.g. en, es, pt.')

    args = parser.parse_args()

    if args.input_file:
        if not args.output_file:
            parser.error('--output-file is required when using --input-file')
        filter_ndjson_by_language(Path(args.input_file), Path(args.output_file), args.language_code)
    else:
        if not args.output_dir:
            parser.error('--output-dir is required when using --input-dir')
        process_directory(args.input_dir, args.output_dir, args.language_code)


if __name__ == '__main__':
    main()
