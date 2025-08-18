#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict
import random

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / "data" / "clean"
OUT_DIR = ROOT / "network_output"
OUT_DIR.mkdir(exist_ok=True)

random.seed(42)

def enrich_guidebook_content(lesson_topic: str) -> str:
    """Enrich guidebook lesson content with contextual information and examples."""
    if not lesson_topic:
        return ""

    lesson_topic_lower = lesson_topic.lower()
    
    if "buy" in lesson_topic_lower or "purchase" in lesson_topic_lower:
        if "stationery" in lesson_topic_lower:
            return f"🛒 Learn vocabulary and phrases for buying stationery items like pens, notebooks, and paper.\n\n💡 Useful phrases:\n• これをください (Please give me this)\n• いくらですか (How much is it?)\n• ありがとうございます (Thank you very much)"
        elif "food" in lesson_topic_lower:
            return f"🍽️ Learn how to order food and drinks in Japanese restaurants and cafes.\n\n💡 Key vocabulary:\n• メニュー (menu)\n• おいしい (delicious)\n• いただきます (let's eat - said before meals)"
    
    elif "order" in lesson_topic_lower:
        if "food" in lesson_topic_lower or "drink" in lesson_topic_lower:
            return f"🍽️ Master food and drink ordering vocabulary and polite expressions.\n\n💡 Key phrases:\n• 〜をください (Please give me...)\n• おいしい (delicious)\n• いただきます (let's eat)"
    
    return ""

def load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))

def create_meaningful_edges(vocab: List[Dict[str, Any]], grammar: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create meaningful edges that show educational relationships."""
    edges = []
    
    print("Creating connections...")
    
    jlpt_to_grammar = defaultdict(list)
    jlpt_to_vocab = defaultdict(list)
    
    for g in grammar:
        jlpt = g.get("jlpt_level", "unknown")
        jlpt_to_grammar[jlpt].append(g["id"])
    
    for v in vocab:
        jlpt = "unknown"
        for tag in v.get("tags", []):
            if tag.startswith("jlpt_"):
                jlpt = tag
                break
        jlpt_to_vocab[jlpt].append(v["id"])
    
    for jlpt, ids in jlpt_to_grammar.items():
        if len(ids) > 1:
            for i, source_id in enumerate(ids):
                connections = 0
                max_connections = min(3, len(ids) - 1)
                
                for j in range(len(ids)):
                    if i != j and connections < max_connections:
                        distance = abs(i - j)
                        if distance <= 3 and random.random() < 0.7:     
                            edges.append({
                                "source": source_id,
                                "target": ids[j],
                                "relation": f"jlpt_grammar:{jlpt}",
                                "weight": 1.0
                            })
                            connections += 1
                        elif distance <= 10 and random.random() < 0.3:
                            edges.append({
                                "source": source_id,
                                "target": ids[j],
                                "relation": f"jlpt_grammar:{jlpt}",
                                "weight": 0.8
                            })
                            connections += 1
    
    for jlpt, ids in jlpt_to_vocab.items():
        if len(ids) > 1:
            for i, source_id in enumerate(ids):
                connections = 0
                max_connections = min(2, len(ids) - 1)
                
                for j in range(len(ids)):
                    if i != j and connections < max_connections:
                        distance = abs(i - j)
                        if distance <= 5 and random.random() < 0.6:
                            edges.append({
                                "source": source_id,
                                "target": ids[j],
                                "relation": f"jlpt_vocab:{jlpt}",
                                "weight": 0.9
                            })
                            connections += 1
    
    # Part of speech connections 
    pos_to_vocab = defaultdict(list)
    for v in vocab:
        pos = v.get("pos", "unknown")
        pos_to_vocab[pos].append(v["id"])
    
    for pos, ids in pos_to_vocab.items():
        if len(ids) > 1:
            for i, source_id in enumerate(ids):
                connections = 0
                max_connections = min(2, len(ids) - 1)
                
                for j in range(len(ids)):
                    if i != j and connections < max_connections:
                        distance = abs(i - j)
                        if distance <= 8 and random.random() < 0.5:
                            edges.append({"source": source_id,"target": ids[j],"relation": f"pos:{pos}","weight": 0.7})
                            connections += 1
    
    tag_to_vocab = defaultdict(list)
    tag_to_grammar = defaultdict(list)
    
    for v in vocab:
        for tag in v.get("tags", []):
            if tag not in ["vocabulary", "anki", "jlpt", "jlpt_n5", "jlpt_n4", "jlpt_n3", "jlpt_n2", "jlpt_n1"]:
                tag_to_vocab[tag].append(v["id"])
    
    for g in grammar:
        for tag in g.get("tags", []):
            if tag not in ["grammar", "jlpt", "jlpt_n5", "jlpt_n4", "jlpt_n3", "jlpt_n2", "jlpt_n1"]:
                tag_to_grammar[tag].append(g["id"])
    
    # Tag connections
    for tag, ids in tag_to_vocab.items():
        if len(ids) > 1:
            for i, source_id in enumerate(ids):
                connections = 0
                max_connections = min(2, len(ids) - 1)
                
                for j in range(len(ids)):
                    if i != j and connections < max_connections:
                        distance = abs(i - j)
                        if distance <= 6 and random.random() < 0.6:
                            edges.append({
                                "source": source_id,
                                "target": ids[j],
                                "relation": f"tag:{tag}",
                                "weight": 0.6
                            })
                            connections += 1
    
    for tag, ids in tag_to_grammar.items():
        if len(ids) > 1:
            for i, source_id in enumerate(ids):
                connections = 0
                max_connections = min(2, len(ids) - 1)
                
                for j in range(len(ids)):
                    if i != j and connections < max_connections:
                        distance = abs(i - j)
                        if distance <= 4 and random.random() < 0.7:
                            edges.append({
                                "source": source_id,
                                "target": ids[j],
                                "relation": f"tag:{tag}",
                                "weight": 0.8
                            })
                            connections += 1
    
    # Cross type connections    
    vocab_lemmas = {v.get("id"): (v.get("lemma") or "").strip() for v in vocab}
    
    for g in grammar:
        exs = g.get("examples", []) or []
        connected_count = 0
        max_connections = 3
        
        for ex in exs:
            if isinstance(ex, dict):
                ja_text = str(ex.get("ja", ""))
                
                for vid, lemma in vocab_lemmas.items():
                    if lemma and lemma in ja_text and connected_count < max_connections:
                        if random.random() < 0.8:
                            edges.append({
                                "source": vid,
                                "target": g["id"],
                                "relation": "appears_in_example",
                                "weight": 0.9
                            })
                            connected_count += 1
    
    # Semantic connections
    meaning_groups = defaultdict(list)
    for v in vocab:
        meanings = v.get("meanings", [])
        if meanings:
            first_meaning = str(meanings[0]).lower()
            key_words = first_meaning.split()[:3]
            semantic_key = " ".join(key_words)
            meaning_groups[semantic_key].append(v["id"])
    
    for semantic_key, ids in meaning_groups.items():
        if len(ids) > 1:
            for i, source_id in enumerate(ids):
                connections = 0
                max_connections = min(2, len(ids) - 1)
                
                for j in range(len(ids)):
                    if i != j and connections < max_connections:
                        if random.random() < 0.7:  
                            edges.append({
                                "source": source_id,
                                "target": ids[j],
                                "relation": "semantic_similarity",
                                "weight": 0.8
                            })
                            connections += 1
    
    print(f"Created {len(edges)} meaningful connections")
    return edges

def main() -> None:
    grammar = load_json(DATA_CLEAN / "grammar_pattern.json")
    vocab = load_json(DATA_CLEAN / "vocabulary_entry.json")

    print(f"Loaded {len(grammar)} grammar patterns and {len(vocab)} vocabulary entries")

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Create nodes
    for g in grammar:
        content_snippet = ""
        
        if g.get("type") == "guidebook_lesson" or "guidebook_" in g.get("id", ""):
            lesson_topic = g.get("description", "")
            
            if lesson_topic:
                enriched_content = enrich_guidebook_content(lesson_topic)
                content_snippet = enriched_content
            
            exs = g.get("examples", []) or []
            if exs:
                example_parts = []
                for ex in exs:
                    if isinstance(ex, dict):
                        ja = str(ex.get("ja", "")).strip()
                        en = str(ex.get("en", "")).strip()
                        if ja and en:
                            example_parts.append(f"{ja}\n{en}")
                
                if example_parts:
                    if content_snippet:
                        content_snippet += "\n\n"
                    content_snippet += "\n\n".join(example_parts)
            
            if g.get("tips") and len(g.get("tips", "")) > 10:
                if content_snippet:
                    content_snippet += "\n\n💡 "
                else:
                    content_snippet = "💡 "
                tips = g.get("tips", "")[:200]
                if len(g.get("tips", "")) > 200:
                    tips += "..."
                content_snippet += tips
        
        else:
            exs = g.get("examples", []) or []
            if exs:
                example_parts = []
                for ex in exs:
                    if isinstance(ex, dict):
                        ja = str(ex.get("ja", "")).strip()
                        en = str(ex.get("en", "")).strip()
                        if ja or en:
                            example_parts.append(f"{ja}\n{en}")
                
                if example_parts:
                    content_snippet = "\n\n".join(example_parts)
            
            if not content_snippet and g.get("description"):
                content_snippet = g.get("description")
        
        level = g.get("level", 1)
        
        pos = g.get("pos", "Grammar")
        
        nodes.append({
            "id": g["id"],
            "label": g.get("title_ja") or g.get("title") or g["id"],
            "type": "grammar_pattern",
            "pos": pos,
            "level": level,
            "difficulty": f"Level {level}",
            "tags": g.get("tags", []),
            "en": g.get("description", ""),
            "ex": content_snippet,
            "cluster_key": f"grammar_level_{level}"})

    for v in vocab:
        content_snippet = ""
        
        if v.get("type") == "guidebook_lesson" or "guidebook_" in v.get("id", ""):
            if v.get("description"):
                content_snippet = f"📚 {v.get('description')}"
            
            v_exs = v.get("examples", []) or []
            if v_exs:
                example_parts = []
                for ex in v_exs:
                    if isinstance(ex, dict):
                        ja = str(ex.get("ja", "")).strip()
                        en = str(ex.get("en", "")).strip()
                        if ja and en:
                            example_parts.append(f"{ja}\n{en}")
                
                if example_parts:
                    if content_snippet:
                        content_snippet += "\n\n"
                    content_snippet += "\n\n".join(example_parts)
            
            if v.get("tips") and len(v.get("tips", "")) > 10:
                if content_snippet:
                    content_snippet += "\n\n💡 "
                else:
                    content_snippet = "💡 "
                tips = v.get("tips", "")[:200]
                if len(v.get("tips", "")) > 200:
                    tips += "..."
                content_snippet += tips
        
        else:
            v_exs = v.get("examples", []) or []
            if v_exs:
                example_parts = []
                for ex in v_exs:
                    if isinstance(ex, dict):
                        ja = str(ex.get("ja", "")).strip()
                        en = str(ex.get("en", "")).strip()
                        if ja or en:
                            example_parts.append(f"{ja}\n{en}")
                
                if example_parts:
                    content_snippet = "\n\n".join(example_parts)
            
            if not content_snippet and v.get("meaning"):
                content_snippet = f"Meaning: {v.get('meaning')}"
            
            if not content_snippet and v.get("description"):
                content_snippet = v.get("description")
        
        level = v.get("level", 1)
        pos = v.get("pos", "unknown")
        
        nodes.append({
            "id": v["id"],
            "label": v.get("lemma", v["id"]),
            "type": "vocabulary_entry",
            "pos": pos,
            "level": level,
            "difficulty": f"Level {level}",
            "tags": v.get("tags", []),
            "en": ", ".join([m for m in v.get("meanings", []) if isinstance(m, str)])[:240],
            "ex": content_snippet,
            "cluster_key": f"vocab_level_{level}_{pos}"
        })

    # Create edges
    edges = create_meaningful_edges(vocab, grammar)
    
    print(f"Created {len(edges)} edges")

    (OUT_DIR / "nodes.json").write_text(json.dumps(nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "edges.json").write_text(json.dumps(edges, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(nodes)} nodes and {len(edges)} edges to {OUT_DIR}")
    
    level_counts = defaultdict(int)
    pos_counts = defaultdict(int)
    
    for n in nodes:
        level_counts[n["level"]] += 1
        if n["type"] == "vocabulary_entry":
            pos_counts[n["pos"]] += 1
    
    print("\nNode distribution:")
    print("Difficulty levels:", dict(level_counts))
    print("Parts of speech:", dict(pos_counts))

if __name__ == "__main__":
    main() 