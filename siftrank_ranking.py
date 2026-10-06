#!/usr/bin/env python3
"""Print the function ranking from a SiftRank result file: rank, score, address, name.

Usage:
    siftrank_ranking.py results.json [--desc] [--parts] [--top N] [--csv]

The input is the JSON produced by SiftRank (a list of results, or an object holding that list).
Each result needs a "score". The function name and address come from the original export entry
("document"), falling back to the "# name (0xaddr)" header line of "value".
The code itself is never printed.
"""
import argparse
import csv
import json
import re
import sys

HEADER_RE = re.compile(r"^#\s*(.+?)\s*\((0x[0-9a-fA-F]+)\)")


def load_results(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        for k in ("results", "items", "ranking", "data"):
            if isinstance(data.get(k), list):
                return data[k]
        raise SystemExit("No result list found in {}".format(path))
    return data


def function_info(result):
    """Return (name, address) of the function, e.g. ("set_Form1#part7", "0x00402791")."""
    doc = result.get("document")
    if isinstance(doc, dict) and doc.get("name"):
        return doc["name"], doc.get("address", "")
    value = result.get("value")
    if isinstance(value, str):
        m = HEADER_RE.match(value)
        if m:
            return m.group(1), m.group(2)
    # Last resort: SiftRank's own key (random id, not human readable)
    return str(result.get("key", "<unknown>")), ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", help="SiftRank JSON output")
    ap.add_argument("--desc", action="store_true", help="higher score = better (default: lower score = better)")
    ap.add_argument("--parts", action="store_true", help="keep '#partN' entries separate instead of merging them per function")
    ap.add_argument("--top", type=int, default=0, help="only show the N best functions")
    ap.add_argument("--csv", action="store_true", help="CSV output (rank,score,address,name)")
    args = ap.parse_args()

    # Keyed by (name, address): several functions can share a name (e.g. ".ctor"); parts are merged unless --parts
    scores = {}
    for r in load_results(args.results):
        if not isinstance(r, dict) or not isinstance(r.get("score"), (int, float)):
            continue
        name, address = function_info(r)
        if not args.parts:
            name = name.split("#part")[0]
        k = (name, address)
        best = scores.get(k)
        if best is None or (r["score"] > best if args.desc else r["score"] < best):
            scores[k] = r["score"]

    ranking = sorted(scores.items(), key=lambda kv: kv[1], reverse=args.desc)
    if args.top > 0:
        ranking = ranking[:args.top]

    if args.csv:
        w = csv.writer(sys.stdout)
        w.writerow(["rank", "score", "address", "name"])
        for i, ((name, address), score) in enumerate(ranking, 1):
            w.writerow([i, score, address, name])
    else:
        print("{:>4}  {:>10}  {:<12}  {}".format("RANK", "SCORE", "ADDRESS", "NAME"))
        for i, ((name, address), score) in enumerate(ranking, 1):
            print("{:>4}  {:>10.4f}  {:<12}  {}".format(i, score, address, name))


if __name__ == "__main__":
    main()
