#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Tuple
from jsonschema import Draft202012Validator
import spacy
nlp = spacy.load("ja_ginza")

# POS helpers 
CANON_POS = {
    "noun": "Noun",
    "n": "Noun",
    "verb": "Verb",
    "v": "Verb",
    "adjective": "Adjective",
    "adj": "Adjective",
    "adverb": "Adverb",
    "adv": "Adverb",
    "pronoun": "Pronoun",
    "particle": "Particle",
    "conjunction": "Conjunction",
    "counter": "Counter",
    "grammar": "grammar", 
    "expression": "Expression",
    "adjectival noun": "Adjective",
    "verbal noun": "Verb",
    "kanji": "Noun",
    "katakana": "Noun"}

def normalize_pos_label(pos_raw: str | None) -> str:
    if not pos_raw:
        return ""
    key = str(pos_raw).strip().lower()
    if key in CANON_POS:
        return CANON_POS[key]
    if "adjectival" in key and "noun" in key:
        return "Adjective"
    if "verbal" in key and "noun" in key:
        return "Verb"
    if "adj" in key:
        return "Adjective"
    if "adv" in key:
        return "Adverb"
    if "conj" in key:
        return "Conjunction"
    if "pron" in key:
        return "Pronoun"
    if "part" in key:
        return "Particle"
    if key in ("kanji", "katakana"):
        return "Noun"
    return pos_raw 

def derive_pos_with_ginza(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    try:
        doc = nlp(text)
        token = next((t for t in doc if t.pos_ not in {"PUNCT", "SPACE"}), None)
        if not token:
            return ""
        upos = token.pos_  
        if upos in {"NOUN", "PROPN"}:
            return "Noun"
        if upos in {"VERB", "AUX"}:
            return "Verb"
        if upos == "ADJ":
            return "Adjective"
        if upos == "ADV":
            return "Adverb"
        if upos == "PRON":
            return "Pronoun"
        if upos in {"ADP", "PART"}:
            return "Particle"
        if upos in {"SCONJ", "CCONJ"}:
            return "Conjunction"
        if upos == "NUM":
            return "Counter"
        return "Expression"
    except Exception:
        return ""


def supplement_pos_with_rules(text: str, current_pos: str = "") -> str:
    """Supplement POS using rule-based patterns when Ginza is unavailable or uncertain."""
    if not isinstance(text, str) or not text.strip():
        return current_pos or "Expression"
    
    text = text.strip()
    
    particles = {"は", "が", "を", "に", "で", "へ", "の", "より", "って", "という", "など", "しか", "こそ", "さえ", "でも", "ばかり", "だけ", "ほど", "くらい"}
    
    conjunctions = {"と", "から", "まで", "や", "も", "か", "し", "が", "けれど", "のに", "ので", "ば", "たら", "なら"}
    
    counters = {"人", "本", "枚", "冊", "円", "個", "台", "匹", "頭", "羽", "杯", "着", "足", "軒", "階", "時間", "分", "秒", "日", "月", "年", "週間", "時間", "分間", "秒間"}
    
    if text in particles:
        return "Particle"
    
    if text in conjunctions:
        return "Conjunction"
    
    if any(text.endswith(counter) for counter in counters):
        return "Counter"
    
    specific_counters = {"一つ", "二つ", "三つ", "四つ", "五つ", "六つ", "七つ", "八つ", "九つ", "十",
                        "一人", "二人", "三人", "四人", "五人", "六人", "七人", "八人", "九人", "十人",
                        "一本", "二本", "三本", "四本", "五本", "六本", "七本", "八本", "九本", "十本",
                        "一枚", "二枚", "三枚", "四枚", "五枚", "六枚", "七枚", "八枚", "九枚", "十枚"}
    if text in specific_counters:
        return "Counter"
    
    if re.match(r"^[一二三四五六七八九十百千万億]+[人本枚冊円個台匹頭羽杯着足軒階時間分秒日月年週間]", text):
        return "Counter"
    
    if re.match(r"^[ァ-ヶー]+$", text):
        return "Noun"
    
    if text.endswith(("する", "れる", "られる", "せる", "させる")):
        return "Verb"
    
    if text.endswith("い") or text.endswith("な"):
        return "Adjective"
    
    if text.endswith(("く", "に", "と")):
        return "Adverb"
    
    return current_pos or "Expression"


ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_CLEAN = ROOT / "data" / "clean"
SCHEMAS = ROOT / "schemas"


# Helper functions
def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def stable_id(prefix: str, payload: Dict[str, Any]) -> str:
    h = hashlib.md5(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{h}"


def to_examples(raw_examples: Any) -> List[Dict[str, str]]:
    examples: List[Dict[str, str]] = []
    if isinstance(raw_examples, list):
        for ex in raw_examples:
            if isinstance(ex, dict):
                ja = ex.get("ja") or ex.get("japanese") or ex.get("jp") or ""
                en = ex.get("en") or ex.get("english") or ""
                if isinstance(ja, str) and ja.strip():
                    examples.append({"ja": ja.strip(), "en": (en or "").strip()})
            elif isinstance(ex, str):
                if ex.strip():
                    examples.append({"ja": ex.strip(), "en": ""})
    return examples


def ensure_list_strings(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, (str, int, float))]
    return [str(value)]


def strip_leading_numbering(text: Any) -> str:
    if not isinstance(text, str):
        return text or ""
    s = text.strip()
    s = re.sub(r"^\s*\d+(?:\.\d+)*(?:[)\.])?\s+", "", s)
    s = re.sub(r"^\s*[IVXLCM]+\.[\s]+", "", s, flags=re.IGNORECASE)
    return s


def contains_latin_letters(text: str) -> bool:
    return bool(isinstance(text, str) and re.search(r"[A-Za-z]", text))


def split_examples_pipe(examples: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if not examples:
        return []
    out: List[Dict[str, str]] = []
    for ex in examples:
        ja = (ex.get("ja") or "").strip()
        en = (ex.get("en") or "").strip()
        if " | " in ja:
            parts = [p.strip() for p in ja.split("|")]
            for p in parts:
                if p:
                    out.append({"ja": p, "en": en})
        else:
            out.append({"ja": ja, "en": en})
    return out


def detect_concept_from_examples(examples: List[Dict[str, str]]) -> str | None:
    """Heuristically detect a Japanese grammar concept from example JA strings."""
    if not examples:
        return None
    text = "\n".join(ex.get("ja") or "" for ex in examples)
    patterns: List[Tuple[str, str]] = [
        (r"てよかった", "てよかった"),
        (r"てくれる", "てくれる"),
        (r"てもらえる", "てもらえる"),
        (r"てもらえませんか", "てもらえませんか"),
        (r"てあげる", "てあげる"),
        (r"てみる", "てみる"),
        (r"やすい", "〜やすい"),
        (r"にくい", "〜にくい"),
        (r"なければならない", "なければならない"),
        (r"なければいけない", "なければいけない"),
        (r"かもしれない", "かもしれない"),
        (r"ように", "ように"),
        (r"ために", "ために"),
        (r"ところ", "ところ"),
        (r"ことができる", "ことができる"),
        (r"てはいけない", "てはいけない"),
        (r"なさい", "〜なさい"),
        (r"ばかり", "〜ばかり"),
        (r"だけ", "〜だけ"),
]
    for regex, concept in patterns:
        if re.search(regex, text):
            return concept
    return None


def has_japanese_chars(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return bool(re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", text))


def looks_like_romaji(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    t = text.strip().lower()
    romaji_tokens = [
        "wa", "ga", "o", "wo", "ni", "de", "kara", "made", "to", "ya", "mo", "ka",
        "desu", "da", "masu", "arimasu", "imasu", "janai", "nai", "suru", "kuru", "iku",
        "kudasai", "onegai", "shimasu", "kudasaimasenka", "arigatou", "ohayou", "konbanwa",
        "sasuga", "naporeon", "demo", "yooroppa", "shihai", "koto", "dekinakatta",
        "shiranai", "aida", "neteita", "kotoshi", "natsuyasumi", "dou", "nasaru", "tsumori"
    ]
    if contains_latin_letters(t):
        tokens = re.findall(r"[a-z]+", t)
        if tokens and sum(1 for tok in tokens if tok in romaji_tokens) >= max(1, len(tokens)//4):
            return True
        eng_markers = ["the", "and", "is", "are", "was", "were", "have", "has", "had", "to ", "for ", "with "]
        if not any(m in t for m in eng_markers) and t == t.lower():
            return True
        if re.search(r"\b(wa|ga|o|ni|de|kara|made|to|ya|mo|ka|desu|masu|nai|suru|kuru|iku)\b", t):
            return True
    return False





# Schema validation 

def load_validator(schema_file: str) -> Draft202012Validator:
    schema = load_json(SCHEMAS / schema_file)
    if not isinstance(schema, dict):
        raise RuntimeError(f"Schema not found or invalid: {schema_file}")
    return Draft202012Validator(schema)


GRAMMAR_VALIDATOR = None  
VOCAB_VALIDATOR = None 


def validate_item(item: Dict[str, Any]) -> Tuple[bool, List[str]]:
    global GRAMMAR_VALIDATOR, VOCAB_VALIDATOR
    if item.get("type") == "grammar_pattern":
        if GRAMMAR_VALIDATOR is None:
            GRAMMAR_VALIDATOR = load_validator("grammar_pattern.schema.json")
        errors = sorted(GRAMMAR_VALIDATOR.iter_errors(item), key=lambda e: e.path)
    elif item.get("type") == "vocabulary_entry":
        if VOCAB_VALIDATOR is None:
            VOCAB_VALIDATOR = load_validator("vocabulary_entry.schema.json")
        errors = sorted(VOCAB_VALIDATOR.iter_errors(item), key=lambda e: e.path)
    else:
        return False, ["Unknown type: " + str(item.get("type"))]
    msgs = [f"{list(e.path)}: {e.message}" for e in errors]
    return (len(msgs) == 0), msgs


# Per source cleaners

def clean_jlpt(raw: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    grammar: List[Dict[str, Any]] = []
    vocab: List[Dict[str, Any]] = []
    dropped_entries: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return grammar, vocab, dropped_entries

    for r in raw:
        if not isinstance(r, dict):
            continue

        item_id = str(r.get("id") or stable_id("jlpt", {"t": r.get("title"), "m": r.get("meaning")}))
        title_raw = r.get("title") or r.get("title_ja") or r.get("label") or r.get("jp") or ""
        description_raw = r.get("meaning") or r.get("description") or ""
        usage_raw = r.get("usage") or ""
        title = strip_leading_numbering(title_raw)
        description = strip_leading_numbering(description_raw)
        usage = strip_leading_numbering(usage_raw)
        jlpt_level = r.get("jlpt_level") or r.get("level") or ""
        tags = ensure_list_strings(r.get("tags"))
        examples = to_examples(r.get("examples") or [])
        if usage and usage != "nan" and contains_latin_letters(usage) and not looks_like_romaji(usage):
            description = usage
        elif description and description.strip() == title.strip():
            description = ""
        elif description and re.match(r"^\d+\.\s*", description.strip()):
            clean_meaning = re.sub(r"^\d+\.\s*", "", description.strip())
            if clean_meaning == title.strip():
                description = ""
            else:
                description = clean_meaning
        if examples:
            cleaned: List[Dict[str, str]] = []
            for ex in examples:
                ja = (ex.get("ja") or "").strip()
                en = (ex.get("en") or "").strip()

                is_fragment = False
                if ja and title:
                    if ja in title and len(ja) < len(title) * 0.6:
                        is_fragment = True
                    if ja.endswith(("った", "ったこと", "ったことが", "ったことがある", "ったことがあります")):
                        is_fragment = True
                    if any(ja.endswith(p) for p in ["し", "って", "こと", "の", "ながら", "らしい", "さすが", "間に", "つもり", "でも", "は", "が", "を", "に", "で"]):
                        is_fragment = True
                if is_fragment:
                    continue 
                if en.startswith("Translation of: "):
                    en = en.replace("Translation of: ", "").strip()
                if looks_like_romaji(en) or en == ja or en.strip().lower() in {"grammar pattern", "- meaning needed", "nan"}:
                    en = ""

                if ja and (not title or ja != title):
                    cleaned.append({"ja": ja, "en": en})
            examples = cleaned

        desc_is_dup = description.strip() == title.strip() or description.strip().startswith(title.strip())
        desc_is_numbered_dup = re.sub(r"^\s*\d+(?:\.\d+)*(?:[)\.])?\s*", "", description.strip()) == title.strip()
        desc_is_placeholder = description.strip().lower() in {"grammar pattern", "- meaning needed"}

        if not description or has_japanese_chars(description) or desc_is_dup or desc_is_numbered_dup or desc_is_placeholder:
            description = ""

        title_final = title
        
        if len(title_final) < 2: 
            dropped_entries.append({
                "id": item_id,
                "title": title_final,
                "reason": "too_short",
                "original_meaning": description_raw,
                "original_usage": usage_raw,
                "examples_count": len(r.get("examples") or [])
            })
            continue
        if not description and not examples: 
            dropped_entries.append({
                "id": item_id,
                "title": title_final,
                "reason": "no_description_no_examples",
                "original_meaning": description_raw,
                "original_usage": usage_raw,
                "examples_count": len(r.get("examples") or [])
            })
            continue
        if description and len(description) < 3:
            dropped_entries.append({
                "id": item_id,
                "title": title_final,
                "reason": "short_description",
                "original_meaning": description_raw,
                "original_usage": usage_raw,
                "examples_count": len(r.get("examples") or [])
            })
            continue
        if title_final in ["法", "間あいだ"] or description in ["How To Use", "nan"]:
            dropped_entries.append({
                "id": item_id,
                "title": title_final,
                "reason": "incomplete_corrupted",
                "original_meaning": description_raw,
                "original_usage": usage_raw,
                "examples_count": len(r.get("examples") or [])
            })
            continue

        g = {
            "id": item_id,
            "type": "grammar_pattern",
            "title": str(title_final or item_id),
            "description": str(description or ""),
            "language": "ja",
            "jlpt_level": str(jlpt_level or ""),
            "examples": examples,
            "tags": list({*tags, "jlpt"}),
            "sources": [{"name": "jlpt"}],
            "relations": [],
            "embedding": None,
        }

        ok, errs = validate_item(g)
        if not ok:
            g["title"] = g.get("title") or item_id
            g["description"] = g.get("description") or ""
            g["examples"] = g.get("examples") or []
            ok2, errs2 = validate_item(g)
            if not ok2:
                dropped_entries.append({
                    "id": item_id,
                    "title": title_final,
                    "reason": "validation_failed",
                    "original_meaning": description_raw,
                    "original_usage": usage_raw,
                    "examples_count": len(r.get("examples") or []),
                    "validation_errors": str(errs2[:2])
                })
                continue

        grammar.append(g)

    return grammar, vocab, dropped_entries


def clean_duolingo(raw: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    grammar: List[Dict[str, Any]] = []
    vocab: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return grammar, vocab

    for r in raw:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or stable_id("duo", r))
        title = r.get("title") or r.get("name") or ""
        meaning = r.get("meaning") or r.get("description") or ""

        if str(r.get("id", "")).startswith("guidebook_") or r.get("examples"):
            if title and title.lower() in ["section", "unit", "lesson", "guidebook"]:
                continue
            if title and re.match(r"^Section \d+ Unit \d+$", title):
                continue
            if not meaning or len(meaning.strip()) < 3:
                continue
                
            g = {
                "id": rid,
                "type": "grammar_pattern",
                "title": str(title or rid),
                "description": str(meaning or ""),
                "language": "ja",
                "jlpt_level": str(r.get("jlpt_level") or ""),
                "examples": to_examples(r.get("examples") or []),
                "tags": list({*ensure_list_strings(r.get("tags")), "duolingo"}),
                "sources": [{"name": "duolingo"}],
                "relations": [],
                "embedding": None,
            }
            ok, errs = validate_item(g)
            if ok:
                grammar.append(g)
            else:
                print(f"Skipping invalid Duolingo grammar {rid}: {errs[:2]}")
        else:
            lemma = r.get("lemma") or title
            if not lemma or not meaning:
                continue
            raw_pos = str(r.get("pos") or r.get("type") or "")
            pos_norm = normalize_pos_label(raw_pos) or derive_pos_with_ginza(lemma) or supplement_pos_with_rules(lemma)
            v = {
                "id": rid,
                "type": "vocabulary_entry",
                "lemma": str(lemma),
                "reading": str(r.get("reading") or ""),
                "pos": pos_norm or raw_pos,
                "meanings": ensure_list_strings(r.get("meanings") or (meaning and [meaning] or [])),
                "examples": to_examples(r.get("examples") or []),
                "tags": list({*ensure_list_strings(r.get("tags")), "duolingo"}),
                "relations": [],
                "embedding": None,
            }
            ok, errs = validate_item(v)
            if ok:
                vocab.append(v)
            else:
                print(f"Skipping invalid Duolingo vocab {rid}: {errs[:2]}")

    return grammar, vocab


def clean_anki(raw: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    grammar: List[Dict[str, Any]] = []
    vocab: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return grammar, vocab

    for r in raw:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or stable_id("anki", r))
        lemma = r.get("lemma") or r.get("title") or r.get("japanese") or r.get("word") or ""
        meaning = r.get("meaning") or r.get("description") or ""
        reading = r.get("reading") or ""
        pos = r.get("pos") or r.get("part_of_speech") or r.get("type") or ""
        
        if not lemma or not meaning:
            continue
            
        meanings = ensure_list_strings(r.get("meanings") or (meaning and [meaning] or []))
        if not meanings:
            continue
            
        examples = []
        raw_examples = r.get("examples") or []
        for ex in raw_examples:
            if isinstance(ex, dict):
                ja = ex.get("japanese") or ex.get("ja") or ""
                en = ex.get("english") or ex.get("en") or ""
                if ja:
                    examples.append({"ja": ja, "en": en})
        
        pos_norm = normalize_pos_label(pos) or derive_pos_with_ginza(lemma) or derive_pos_with_ginza(reading) or supplement_pos_with_rules(lemma) or supplement_pos_with_rules(reading)
        
        v = {
            "id": rid,
            "type": "vocabulary_entry",
            "lemma": str(lemma),
            "reading": str(reading),
            "pos": str(pos_norm or pos),
            "meanings": meanings,
            "examples": examples,
            "tags": list({*ensure_list_strings(r.get("tags")), "anki"}),
            "relations": [],
            "embedding": None,
        }
        ok, errs = validate_item(v)
        if ok:
            vocab.append(v)
        else:
            print(f"Skipping invalid Anki vocab {rid}: {errs[:2]}")

    return grammar, vocab





# Deduplicattion & merge 
def merge_by_id(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for it in items:
        iid = it.get("id")
        if not isinstance(iid, str):
            continue
        if iid not in by_id:
            by_id[iid] = it
    return list(by_id.values())


# Main 
def main() -> None:
    parser = argparse.ArgumentParser(description="Clean raw data into schema-compliant JSON files")
    args = parser.parse_args()

    grammar_all: List[Dict[str, Any]] = []
    vocab_all: List[Dict[str, Any]] = []
    dropped_entries: List[Dict[str, Any]] = []

    # Load unified JLPT JSON
    jlpt_json = load_json(DATA_RAW / "jlpt_raw.json")
    if jlpt_json and "entries" in jlpt_json:
        print(f"Loaded unified JLPT JSON: {jlpt_json['metadata']['total_entries']} entries")
        # Process the unified entries
        for entry in jlpt_json["entries"]:
            if entry.get("type") == "grammar_pattern":
                grammar_all.append(entry)
            elif entry.get("type") == "vocabulary_entry":
                vocab_all.append(entry)
    else:
        # Fallback to individual JLPT data if unified format not available
        jlpt_raw = load_json(DATA_RAW / "jlpt_raw.json")
        if jlpt_raw is not None:
            g, v, d = clean_jlpt(jlpt_raw)
            grammar_all.extend(g)
            vocab_all.extend(v)
            dropped_entries.extend(d)

    # Load other sources
    duo_raw = load_json(DATA_RAW / "duo_raw.json")
    anki_raw = load_json(DATA_RAW / "anki_raw.json")

    # Clean each source
    if duo_raw is not None:
        g, v = clean_duolingo(duo_raw)
        grammar_all.extend(g)
        vocab_all.extend(v)

    if anki_raw is not None:
        g, v = clean_anki(anki_raw)
        grammar_all.extend(g)
        vocab_all.extend(v)

    # Deduplicate by id
    grammar_all = merge_by_id(grammar_all)
    vocab_all = merge_by_id(vocab_all)

    # Final validation
    bad_grammar = 0
    for it in grammar_all:
        ok, errs = validate_item(it)
        if not ok:
            bad_grammar += 1
            print(f"Invalid grammar {it.get('id')}: {errs[:2]}")
    bad_vocab = 0
    for it in vocab_all:
        ok, errs = validate_item(it)
        if not ok:
            bad_vocab += 1
            print(f"Invalid vocab {it.get('id')}: {errs[:2]}")

    print(f"Grammar: {len(grammar_all)} (invalid: {bad_grammar})")
    print(f"Vocab: {len(vocab_all)} (invalid: {bad_vocab})")

    # delete old entries implicitly)
    out_grammar = DATA_CLEAN / "grammar_pattern.json"
    out_vocab = DATA_CLEAN / "vocabulary_entry.json"
    write_json(out_grammar, grammar_all)
    write_json(out_vocab, vocab_all)
    print(f"Wrote {len(grammar_all)} → {out_grammar}")
    print(f"Wrote {len(vocab_all)} → {out_vocab}")

    # Export dropped entries to JSON for debugging
    if dropped_entries:
        dropped_json_path = DATA_CLEAN / "dropped_entries.json"
        write_json(dropped_json_path, dropped_entries)
        print(f"Wrote {len(dropped_entries)} dropped entries to {dropped_json_path}")


if __name__ == "__main__":
    main()

