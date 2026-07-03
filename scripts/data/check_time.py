#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def has_timestamp(obj):
    """
    Returns True if either published_time or modified_time exists
    and has a non-null value.
    """
    return (
        obj.get("published_time") is not None
        or obj.get("modified_time") is not None
    )


def check_file(file_path):
    missing_count = 0
    missing_line = ""
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.rstrip()

            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[ERROR] {file_path}:{line_num} - Invalid JSON ({e})")
                continue

            if not has_timestamp(obj):
                missing_line = line
                missing_count += 1

    return missing_count, missing_line


def main():
    directory = Path("C:\\Users\\pelay\\Documents\\EII\\4º Software\\TFG\\Datasets\\filtered-docs\\news\\es")
    missing_lines = []
    if not directory.is_dir():
        print(f"Not a directory: {directory}")
        sys.exit(1)

    total_files = 0
    total_missing = 0

    for ndjson_file in directory.rglob("*.ndjson"):
        total_files += 1
        num, line = check_file(ndjson_file)
        total_missing += num
        if line != "":
            missing_lines.append(line)
        

    print("\n" + "=" * 80)
    print(f"Checked {total_files} NDJSON files")
    print(f"Found {total_missing} records missing both timestamps")
    print(f"Example: {missing_lines[0]}")

if __name__ == "__main__":

    main()