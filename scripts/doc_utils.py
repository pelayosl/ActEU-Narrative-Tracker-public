import argparse
import json
import sys


def extract_doc_ids(payload: dict) -> list[str]:
	retrieved = payload.get("retrieved_docs", [])
	return [doc.get("doc_id") for doc in retrieved if doc.get("doc_id")]


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Extract doc_ids from a JSON payload containing retrieved_docs."
	)
	parser.add_argument(
		"--input",
		"-i",
		help="Path to input JSON file. If omitted, reads from stdin.",
	)
	args = parser.parse_args()

	try:
		if args.input:
			with open(args.input, "r", encoding="utf-8") as handle:
				payload = json.load(handle)
		else:
			payload = json.load(sys.stdin)
	except json.JSONDecodeError as exc:
		print(f"Invalid JSON input: {exc}", file=sys.stderr)
		return 1

	doc_ids = extract_doc_ids(payload)
	json.dump({"doc_ids": doc_ids}, sys.stdout, ensure_ascii=False)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
