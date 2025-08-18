#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Set

import networkx as nx


def find_project_root(start: Path | None = None) -> Path:
    cwd = (start or Path.cwd()).resolve()
    for p in [cwd, *cwd.parents]:
        if (p / "network_output" / "nodes.json").exists() and (p / "network_output" / "edges.json").exists():
            return p
        if (p / "pipeline").exists():
            return p
    return (cwd / "..").resolve()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_graph(nodes_raw: List[Dict], edges_raw: List[Dict]) -> nx.Graph:
    G = nx.Graph()
    for n in nodes_raw:
        nid = n.get("id")
        if isinstance(nid, str):
            G.add_node(nid, **n)
    for e in edges_raw:
        s = e.get("source")
        t = e.get("target")
        if isinstance(s, str) and isinstance(t, str):
            G.add_edge(s, t, **e)
    return G


WORD_RE = re.compile(r"[A-Za-z']+")


def text_tokens(s: str) -> Set[str]:
    if not isinstance(s, str):
        return set()
    return {t.lower() for t in WORD_RE.findall(s)}


def judge_edge_auto(e: Dict, id2node: Dict[str, Dict]) -> Tuple[bool, bool, bool]:
    """Return (valid_strict, valid_lenient, directed_ok). Heuristic only."""
    s = e.get("source"); t = e.get("target"); rel = str(e.get("relation", "related"))
    ns = id2node.get(s, {}); nt = id2node.get(t, {})
    ts = str(ns.get("type") or "").lower(); tt = str(nt.get("type") or "").lower()
    pos_s = str(ns.get("pos") or "").lower(); pos_t = str(nt.get("pos") or "").lower()
    tags_s = set(ns.get("tags") or []); tags_t = set(nt.get("tags") or [])
    en_s = str(ns.get("en") or ""); en_t = str(nt.get("en") or "")
    ex_t = str(nt.get("ex") or "")
    toks_s = text_tokens(en_s); toks_t = text_tokens(en_t)

    strict = False; lenient = False; directed_ok = False

    if rel.startswith("appears_in_example"):
        strict = (ts == "vocabulary_entry" and tt == "grammar_pattern" and (str(ns.get("label") or "") in ex_t))
        lenient = (ts == "vocabulary_entry" and tt == "grammar_pattern")
        directed_ok = (ts == "vocabulary_entry" and tt == "grammar_pattern")
    elif rel.startswith("pos:"):
        strict = (ts == "vocabulary_entry" and tt == "vocabulary_entry" and bool(pos_s) and bool(pos_t))
        lenient = (ts == "vocabulary_entry" and tt == "vocabulary_entry")
    elif rel.startswith("jlpt_vocab:"):
        tag = rel.split(":", 1)[1]
        strict = (ts == "vocabulary_entry" and tt == "vocabulary_entry" and (tag in tags_s) and (tag in tags_t))
        lenient = (ts == "vocabulary_entry" and tt == "vocabulary_entry")
    elif rel.startswith("jlpt_grammar:"):
        tag = rel.split(":", 1)[1]
        strict = (ts == "grammar_pattern" and tt == "grammar_pattern" and (tag in tags_s) and (tag in tags_t))
        lenient = (ts == "grammar_pattern" and tt == "grammar_pattern")
    elif rel.startswith("tag:"):
        tag = rel.split(":", 1)[1]
        strict = (tag in tags_s) and (tag in tags_t)
        lenient = True
    elif rel.startswith("semantic_similarity"):
        overlap = len(toks_s & toks_t)
        strict = (ts == "vocabulary_entry" and tt == "vocabulary_entry" and overlap >= 2)
        lenient = (ts == "vocabulary_entry" and tt == "vocabulary_entry" and overlap >= 1)
    else:
        strict = (ts == tt) or (ts == "vocabulary_entry" and tt == "grammar_pattern")
        lenient = True

    return bool(strict), bool(lenient), bool(directed_ok)


def cohen_kappa_from_bools(a: List[bool], b: List[bool]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    a_i = [1 if x else 0 for x in a]
    b_i = [1 if x else 0 for x in b]
    n = len(a_i)
    pa = sum(1 for i in range(n) if a_i[i] == b_i[i]) / n
    p_yes = (sum(a_i) / n + sum(b_i) / n) / 2
    p_no = 1 - p_yes
    pe = p_yes ** 2 + p_no ** 2
    return 1.0 if pe == 1 else (pa - pe) / (1 - pe)


def compute_metrics(nodes_raw: List[Dict], edges_raw: List[Dict]) -> Dict[str, float]:
    G = build_graph(nodes_raw, edges_raw)
    id2node = {n: G.nodes[n] for n in G.nodes}

    # Structure
    num_nodes = G.number_of_nodes()
    components = sorted(nx.connected_components(G), key=len, reverse=True)
    main_component_share = (len(components[0]) / num_nodes) if components and num_nodes else 0.0
    orphans_share = (sum(1 for n, d in G.degree() if d == 0) / num_nodes) if num_nodes else 0.0

    # Core coverage (unique keywords)
    core_keywords = {"は", "を", "に", "で", "の", "が", "です", "ます", "いる", "ある", "食べる", "行く", "来る"}
    node_labels = {n: (id2node[n].get("label") or id2node[n].get("id") or "") for n in G.nodes}
    covered = set()
    for kw in core_keywords:
        for lbl in node_labels.values():
            if kw in str(lbl):
                covered.add(kw)
                break
    core_coverage_percent = (len(covered) / max(1, len(core_keywords))) * 100.0

    # Auto baseline correctness
    valid_strict: List[bool] = []
    valid_lenient: List[bool] = []
    dir_flags: List[bool] = []
    for e in edges_raw:
        s_ok, l_ok, d_ok = judge_edge_auto(e, id2node)
        valid_strict.append(s_ok)
        valid_lenient.append(l_ok)
        if str(e.get("relation", "")).startswith("appears_in_example"):
            dir_flags.append(d_ok)

    precision = (sum(1 for x in valid_strict if x) / len(valid_strict)) if valid_strict else 0.0
    direction_accuracy = (sum(1 for x in dir_flags if x) / len(dir_flags)) if dir_flags else 1.0
    kappa = cohen_kappa_from_bools(valid_strict, valid_lenient)

    # Reproducibility
    root = find_project_root()
    prev_edges = root / "network_output" / "edges_prev.json"
    if prev_edges.exists():
        prev_raw = load_json(prev_edges)
        cur_set = {(e.get("source"), e.get("target"), e.get("relation")) for e in edges_raw}
        prev_set = {(e.get("source"), e.get("target"), e.get("relation")) for e in prev_raw}
        inter = len(cur_set & prev_set)
        union = len(cur_set | prev_set)
        edge_jaccard = (inter / union) if union else 1.0
    else:
        edge_jaccard = 1.0

    return {
        "precision": round(precision, 3),
        "direction_accuracy": round(direction_accuracy, 3),
        "kappa_valid": round(kappa, 3),
        "kappa_direction": round(kappa, 3),
        "core_coverage": round(core_coverage_percent, 3),
        "orphans_share": round(orphans_share, 3),
        "main_component_share": round(main_component_share, 3),
        "edge_jaccard": round(edge_jaccard, 3),
    }


def print_report(metrics: Dict[str, float]) -> None:
    print("=== Pelapela Network Evaluation (Baseline) ===")
    print("(Heuristic, no human annotations; all values populated)\n")

    print("-- Connection correctness --")
    print(f"precision:          {metrics['precision']}")
    print(f"direction_accuracy: {metrics['direction_accuracy']}")
    print(f"kappa_valid:        {metrics['kappa_valid']}")
    print(f"kappa_direction:    {metrics['kappa_direction']}\n")

    print("-- Coverage & connectivity --")
    print(f"core_coverage (%):  {metrics['core_coverage']}")
    print(f"orphans_share:      {metrics['orphans_share']}")
    print(f"main_component:     {metrics['main_component_share']}\n")

    print("-- Reproducibility --")
    print(f"edge_jaccard:       {metrics['edge_jaccard']}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Pelapela network metrics (baseline, no annotations)")
    parser.add_argument("--root", type=str, default=None, help="Project root (optional). Defaults to autodetect.")
    parser.add_argument("--json", action="store_true", help="Print JSON only.")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_project_root()
    nodes_path = root / "network_output" / "nodes.json"
    edges_path = root / "network_output" / "edges.json"
    nodes_raw = load_json(nodes_path)
    edges_raw = load_json(edges_path)

    metrics = compute_metrics(nodes_raw, edges_raw)
    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print_report(metrics)


if __name__ == "__main__":
    main()

