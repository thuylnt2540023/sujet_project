#!/usr/bin/env python3
"""
Extract [SUMMARY] blocks from download .log files under REPORTS/.

Output: REPORTS/summary.csv  (one row per download run)
        REPORTS/summary-sources.csv  (one row per source per download run)
"""

import csv
import json
import os
import re
import sys
from pathlib import Path


REPORTS_DIR = Path(__file__).resolve().parent.parent / "REPORTS"

# ── regex patterns ──────────────────────────────────────────────────────────
RE_TIMESTAMP = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\]')
RE_KV        = re.compile(r'^\[SUMMARY\] (\w[\w/]*)=(.*)')
RE_SOURCE    = re.compile(
    r'^\[SUMMARY\] source=(\S+)\s+fragments=(\d+)\s+bytes=(\d+)\s+time_ms=(\d+)\s+speed_KB/s=(\d+)'
)
RE_SEP       = re.compile(r'^\[SUMMARY\] =+')
RE_PER_SRC   = re.compile(r'^\[SUMMARY\] --- Per-source stats ---')
RE_FRAGMENT_SIZE = re.compile(r'^(\d+) bytes')


def parse_log(log_path: Path) -> list[dict]:
    """Return a list of summary records extracted from *log_path*."""
    records = []
    current: dict | None = None
    first_timestamp: str = ""

    with open(log_path, errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")

            # grab timestamp from this line
            ts_match = RE_TIMESTAMP.match(line)
            ts = ts_match.group(1) if ts_match else ""

            after_summary = line[line.find("] ", line.find("[SUMMARY]")) + 2:] if "[SUMMARY]" in line else None

            if after_summary is None:
                continue  # not a SUMMARY line

            # separator line  ===...===
            if RE_SEP.match(f"[SUMMARY] {after_summary}"):
                if current is None:
                    # opening separator → start new block
                    current = {"_sources": [], "_first_ts": ts}
                    first_timestamp = ts
                else:
                    # closing separator → seal record
                    records.append(current)
                    current = None
                continue

            if current is None:
                continue  # stray line outside a block

            # per-source line
            src_m = RE_SOURCE.match(f"[SUMMARY] {after_summary}")
            if src_m:
                current["_sources"].append({
                    "source":       src_m.group(1),
                    "fragments":    int(src_m.group(2)),
                    "bytes":        int(src_m.group(3)),
                    "time_ms":      int(src_m.group(4)),
                    "speed_KB_s":   int(src_m.group(5)),
                })
                continue

            if RE_PER_SRC.match(f"[SUMMARY] {after_summary}"):
                continue  # section header

            # generic key=value
            kv_m = RE_KV.match(f"[SUMMARY] {after_summary}")
            if kv_m:
                key, val = kv_m.group(1), kv_m.group(2).strip()
                current[key] = val

    return records


def derive_metadata(log_path: Path) -> dict:
    """Extract region and daemon-IP from the file path / name."""
    region = log_path.parent.name  # e.g. us-east-1

    # filename: download-<daemon_ip>-<file_name>.log
    # daemon_ip may be an IP or a port like "2048" (edge case)
    stem = log_path.stem  # strip .log
    m = re.match(r'^download-([^-]+(?:\.[^-]+){0,3}|[^-]+)-(.*)', stem)
    if m:
        daemon_ip = m.group(1)
        # re-join in case the file name itself contained hyphens that were consumed
        # safer: strip the "download-" prefix and take everything between first and second group
        parts = stem.split("-", 2)
        daemon_ip = parts[1] if len(parts) >= 2 else "unknown"
    else:
        daemon_ip = "unknown"

    return {"region": region, "daemon_ip": daemon_ip, "log_file": log_path.name}


def build_rows(log_path: Path) -> tuple[list[dict], list[dict]]:
    """Return (main_rows, source_rows) for this log file."""
    meta = derive_metadata(log_path)
    records = parse_log(log_path)

    main_rows = []
    source_rows = []

    for rec in records:
        # normalise fragment_size: "524288 bytes (512 KB)" → 524288
        frag_raw = rec.get("fragment_size", "")
        frag_bytes = ""
        fs_m = RE_FRAGMENT_SIZE.match(frag_raw)
        if fs_m:
            frag_bytes = fs_m.group(1)

        # normalise file_size: "9959701 bytes" → 9959701
        fsz_raw = rec.get("file_size", "")
        file_size_bytes = fsz_raw.split()[0] if fsz_raw else ""

        sources = rec.get("_sources", [])
        ts = rec.get("_first_ts", "")

        row = {
            "timestamp":         ts,
            "region":            meta["region"],
            "daemon_ip":         meta["daemon_ip"],
            "log_file":          meta["log_file"],
            "file":              rec.get("file", ""),
            "file_size_bytes":   file_size_bytes,
            "fragment_size_bytes": frag_bytes,
            "total_fragments":   rec.get("total_fragments", ""),
            "sources_used":      rec.get("sources_used", ""),
            "compression":       rec.get("compression", ""),
            "total_time_ms":     rec.get("total_time_ms", ""),
            "avg_speed_KB_s":    rec.get("avg_speed_KB/s", ""),
            "failed_fragments":  rec.get("failed_fragments", ""),
            "sources_json":      json.dumps(sources),
        }
        main_rows.append(row)

        for src in sources:
            source_rows.append({
                "timestamp":    ts,
                "region":       meta["region"],
                "daemon_ip":    meta["daemon_ip"],
                "log_file":     meta["log_file"],
                "file":         rec.get("file", ""),
                "compression":  rec.get("compression", ""),
                **src,
            })

    return main_rows, source_rows


def main():
    log_files = sorted(REPORTS_DIR.rglob("*.log"))
    if not log_files:
        print(f"No .log files found under {REPORTS_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(log_files)} log file(s) under {REPORTS_DIR}")

    all_main: list[dict] = []
    all_sources: list[dict] = []

    for lf in log_files:
        m, s = build_rows(lf)
        all_main.extend(m)
        all_sources.extend(s)
        print(f"  {lf.relative_to(REPORTS_DIR)}  →  {len(m)} run(s)")

    # write summary.csv
    out_main = REPORTS_DIR / "summary.csv"
    main_fields = [
        "timestamp", "region", "daemon_ip", "log_file",
        "file", "file_size_bytes", "fragment_size_bytes",
        "total_fragments", "sources_used", "compression",
        "total_time_ms", "avg_speed_KB_s", "failed_fragments",
        "sources_json",
    ]
    with open(out_main, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=main_fields)
        w.writeheader()
        w.writerows(all_main)

    # write summary-sources.csv
    out_sources = REPORTS_DIR / "summary-sources.csv"
    src_fields = [
        "timestamp", "region", "daemon_ip", "log_file",
        "file", "compression",
        "source", "fragments", "bytes", "time_ms", "speed_KB_s",
    ]
    with open(out_sources, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=src_fields)
        w.writeheader()
        w.writerows(all_sources)

    print(f"\nWrote {len(all_main)} rows  →  {out_main}")
    print(f"Wrote {len(all_sources)} rows  →  {out_sources}")


if __name__ == "__main__":
    main()
