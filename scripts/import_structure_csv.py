import csv
import yaml
from collections import defaultdict
from pathlib import Path
import sys

CSV_PATH = Path("csv/structure.csv")
OUT_DIR = Path("structures")

REQUIRED_COLUMNS = {
    "work_id",
    "node_id",
    "parent_id",
    "level_id",
    "ordinal",
    "lang",
    "title",
    "site",
    "url",
}

# -------------------------
# Validation helpers
# -------------------------

def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def validate_columns(fieldnames):
    missing = REQUIRED_COLUMNS - set(fieldnames)
    if missing:
        fail(f"CSV is missing columns: {', '.join(sorted(missing))}")


# -------------------------
# Main importer
# -------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        validate_columns(reader.fieldnames)
        rows = list(reader)

    works = defaultdict(list)
    for row in rows:
        works[row["work_id"]].append(row)

    for work_id, work_rows in works.items():
        build_work_structure(work_id, work_rows)


def build_work_structure(work_id, rows):
    nodes = {}
    seen_parents = set()

    for row in rows:
        node_id = row["node_id"].strip()
        if not node_id:
            fail(f"Empty node_id in work {work_id}")

        nodes.setdefault(node_id, {
            "id": node_id,
            "level": row["level_id"].strip(),
            "ordinal": int(row["ordinal"]),
            "title": {},
        })

        node = nodes[node_id]

        parent_id = row["parent_id"].strip()
        if parent_id:
            node["parent"] = parent_id
            seen_parents.add(parent_id)

        # titles (multilingual)
        lang = row["lang"].strip()
        title = row["title"].strip()
        if lang and title:
            node["title"][lang] = title

        # links (grouped by site)
        site = row["site"].strip()
        url = row["url"].strip()
        if site and url:
            node.setdefault("links", {})
            node["links"][site] = url

    # -------------------------
    # Validation
    # -------------------------

    for node in nodes.values():
        if "parent" in node and node["parent"] not in nodes:
            fail(f"Parent '{node['parent']}' not found (node {node['id']})")

    # -------------------------
    # Infer levels
    # -------------------------

    level_ordinals = {}
    for node in nodes.values():
        lvl = node["level"]
        level_ordinals[lvl] = min(
            level_ordinals.get(lvl, node["ordinal"]),
            node["ordinal"],
        )

    levels = [
        {"id": lvl, "ordinal": ord_}
        for lvl, ord_ in sorted(level_ordinals.items(), key=lambda x: x[1])
    ]

    # -------------------------
    # Sort nodes (stable + readable)
    # -------------------------

    def sort_key(n):
        return (
            n.get("parent", ""),
            n["ordinal"],
            n["id"],
        )

    sorted_nodes = sorted(nodes.values(), key=sort_key)

    # -------------------------
    # Output YAML
    # -------------------------

    out = {
        "structure": {
            "levels": levels,
            "nodes": sorted_nodes,
        }
    }

    out_path = OUT_DIR / f"{work_id}.structure.yaml"
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            out,
            f,
            sort_keys=False,
            allow_unicode=True,
        )

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
