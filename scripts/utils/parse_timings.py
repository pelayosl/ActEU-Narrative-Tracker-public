#!/usr/bin/env python3
"""Aggregate the performance-timing logs into per-operation statistics.

Reads one or more timing log files written by ``app.infrastructure.timing`` (the API
process and the Celery worker write separate files; pass a glob to combine them) and
prints count / mean / p50 / p95 / max for:

* user-facing requests   — ``event=request`` lines, grouped by ``op`` (route template);
* pipeline job execution — ``event=task`` lines, grouped by ``op`` (task name);
* pipeline queue wait    — derived by pairing ``event=dispatch`` and ``event=task``
                           records by ``job_id`` (worker start_ts − dispatch ts).

Usage:
    python scripts/utils/parse_timings.py timings.log
    python scripts/utils/parse_timings.py "logs/*timings*.log"
"""

import glob
import sys
from collections import defaultdict


def _parse_line(line: str) -> dict[str, str] | None:
    """Extract the ``key=value`` tokens from one timing record, or None."""
    if "op=" not in line:
        return None
    fields: dict[str, str] = {}
    for token in line.split():
        if "=" in token:
            key, _, value = token.partition("=")
            fields[key] = value
    return fields if "op" in fields and "event" in fields else None


def _stats(values: list[float]) -> tuple[int, float, float, float, float]:
    """Return (count, mean, p50, p95, max) over a list of measurements."""
    ordered = sorted(values)
    n = len(ordered)

    def pct(p: float) -> float:
        # Nearest-rank percentile.
        rank = max(0, min(n - 1, int(round(p / 100 * n + 0.5)) - 1))
        return ordered[rank]

    return n, sum(ordered) / n, pct(50), pct(95), ordered[-1]


def _print_table(title: str, grouped: dict[str, list[float]]) -> None:
    print(f"\n=== {title} (ms) ===")
    if not grouped:
        print("  (no records)")
        return
    print(f"  {'operation':<45} {'n':>6} {'mean':>9} {'p50':>9} {'p95':>9} {'max':>9}")
    for op in sorted(grouped):
        n, mean, p50, p95, mx = _stats(grouped[op])
        print(f"  {op:<45} {n:>6} {mean:>9.1f} {p50:>9.1f} {p95:>9.1f} {mx:>9.1f}")


def main(patterns: list[str]) -> int:
    paths: list[str] = []
    for pattern in patterns:
        paths.extend(glob.glob(pattern))
    if not paths:
        print(f"No files matched: {patterns}", file=sys.stderr)
        return 1

    requests: dict[str, list[float]] = defaultdict(list)
    tasks: dict[str, list[float]] = defaultdict(list)
    dispatch_ts: dict[str, float] = {}            # job_id -> dispatch epoch
    task_start: dict[str, tuple[str, float]] = {}  # job_id -> (op, start epoch)

    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                fields = _parse_line(line)
                if fields is None:
                    continue
                event = fields["event"]
                op = fields["op"]
                if event == "request":
                    requests[op].append(float(fields["dur_ms"]))
                elif event == "task":
                    tasks[op].append(float(fields["dur_ms"]))
                    if "job_id" in fields and "start_ts" in fields:
                        task_start[fields["job_id"]] = (op, float(fields["start_ts"]))
                elif event == "dispatch" and "job_id" in fields:
                    dispatch_ts[fields["job_id"]] = float(fields["ts"])

    queue_wait: dict[str, list[float]] = defaultdict(list)
    for job_id, (op, start) in task_start.items():
        dispatched = dispatch_ts.get(job_id)
        if dispatched is not None:
            queue_wait[op].append((start - dispatched) * 1000)

    _print_table("User-facing requests", requests)
    _print_table("Pipeline job execution", tasks)
    _print_table("Pipeline queue wait", queue_wait)
    return 0


if __name__ == "__main__":
    args = sys.argv[1:] or ["timings.log"]
    raise SystemExit(main(args))
