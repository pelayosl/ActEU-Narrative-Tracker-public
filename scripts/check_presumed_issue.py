"""
Check PresumedIssue labels in ndjson file
Counts documents with 2 or more PresumedIssue labels
"""

import json
from pathlib import Path
from tqdm import tqdm

INPUT_PATH = Path("C:\\Users\\pelay\\Documents\\EII\\4º Software\\TFG\\Datasets\\ActEU-telegram-messages-filtered-distilled\\ActEU-telegram-messages-filtered-distilled.ndjson")

def count_multi_label_documents(input_path: Path):
    """
    Count documents containing 2 or more labels in PresumedIssue.
    """
    count = 0
    total = 0

    with input_path.open("r", encoding="utf-8") as infile:
        for line in tqdm(infile, desc="Processing"):
            line = line.strip()
            if not line:
                continue

            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue

            total += 1
            annotations = doc.get("annotations", {})
            presumed_issue = annotations.get("PresumedIssue", {})

            if len(presumed_issue) >= 2:
                count += 1

    return count, total


if __name__ == "__main__":
    multi_label_count, total_docs = count_multi_label_documents(INPUT_PATH)
    print(f"\nTotal documents: {total_docs}")
    print(f"Documents with 2+ PresumedIssue labels: {multi_label_count}")
    print(f"Percentage: {(multi_label_count / total_docs * 100):.2f}%" if total_docs > 0 else "N/A")
