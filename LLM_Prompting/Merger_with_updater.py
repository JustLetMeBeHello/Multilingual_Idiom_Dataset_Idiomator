"""
merge_idiom_dataset.py
 
Merges idiom meanings + example sentences for 5 languages.
 
Input paths (relative to base dir):
  idioms_structured/Idiom_meanings/Labelled_Meanings/{lang}/Merged_Meanings_{lang}_FINAL.jsonl
  idioms_structured/Idiom_meanings/Example_Sentences/{lang}/Examples_{lang}.jsonl
 
Output path:
  idioms_structured/Final_Seed_Dataset/{lang}/Final_{lang}.jsonl
 
Each output line is one sense, with its meaning fields + an "examples" list (null if none found).
Run from the root of your project:
  python merge_idiom_dataset.py
"""
 
import json
import os
from collections import defaultdict
from pathlib import Path
 
# ── Config ────────────────────────────────────────────────────────────────────
 
BASE_DIR = Path("idioms_structured")
 
LANGUAGES = ["English", "Spanish", "Indonesian", "Telugu", "Hindi"]
 
MEANINGS_TEMPLATE = "Idiom_meanings/Labelled_Meanings/{lang}/Merged_Meanings_{lang}_FINAL.jsonl"
EXAMPLES_TEMPLATE = "Idiom_meanings/Example_Sentences/{lang}/Examples_{lang}.jsonl"
OUTPUT_TEMPLATE   = "Final_Seed_Dataset/{lang}/Final_{lang}.jsonl"
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def load_meanings(path: Path) -> list[dict]:
    """
    Meanings file format: each line is a JSON array [idiom_id, [sense_obj, ...]]
    Returns a flat list of all sense objects.
    """
    senses = []
    if not path.exists():
        print(f"  [WARN] Meanings file not found: {path}")
        return senses
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                # record is [idiom_id, [sense1, sense2, ...]]
                if isinstance(record, list) and len(record) == 2:
                    sense_list = record[1]
                    if isinstance(sense_list, list):
                        senses.extend(sense_list)
                    else:
                        print(f"  [WARN] Line {lineno}: expected list of senses, got {type(sense_list)}")
                else:
                    print(f"  [WARN] Line {lineno}: unexpected meanings format")
            except json.JSONDecodeError as e:
                print(f"  [WARN] Line {lineno}: JSON decode error — {e}")
    return senses
 
 
def load_examples(path: Path) -> dict[tuple, list]:
    """
    Examples file format: each line is a JSON object with idiom_id, sense_number, examples list.
    Returns dict keyed by (idiom_id, sense_number) -> list of example dicts.
    """
    index = defaultdict(list)
    if not path.exists():
        print(f"  [WARN] Examples file not found: {path}")
        return index
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                key = (record["idiom_id"], record["sense_number"])
                index[key].extend(record.get("examples") or [])
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  [WARN] Line {lineno}: error reading examples — {e}")
    return index
 
 
def merge_language(lang: str) -> dict:
    """Merge meanings + examples for one language. Returns stats dict."""
    meanings_path = BASE_DIR / MEANINGS_TEMPLATE.format(lang=lang)
    examples_path = BASE_DIR / EXAMPLES_TEMPLATE.format(lang=lang)
    output_path   = BASE_DIR / OUTPUT_TEMPLATE.format(lang=lang)
 
    print(f"\n── {lang} ──")
    print(f"  Meanings : {meanings_path}")
    print(f"  Examples : {examples_path}")
    print(f"  Output   : {output_path}")
 
    senses   = load_meanings(meanings_path)
    examples = load_examples(examples_path)
 
    output_path.parent.mkdir(parents=True, exist_ok=True)
 
    idiom_ids   = set()
    sense_count = 0
    example_count = 0
    senses_with_examples = 0
    senses_without_examples = 0
 
    with open(output_path, "w", encoding="utf-8") as out:
        for sense in senses:
            idiom_id     = sense.get("idiom_id")
            sense_number = sense.get("sense_number")
            key          = (idiom_id, sense_number)
 
            matched_examples = examples.get(key, None)  # None = key never appeared
 
            merged = {**sense, "examples": matched_examples}
 
            out.write(json.dumps(merged, ensure_ascii=False) + "\n")
 
            # Stats
            if idiom_id:
                idiom_ids.add(idiom_id)
            sense_count += 1
            if matched_examples:
                example_count += len(matched_examples)
                senses_with_examples += 1
            else:
                senses_without_examples += 1
 
    # Also account for examples whose sense wasn't in meanings
    orphan_examples = 0
    for key, exs in examples.items():
        # Check if this key had a matching sense
        # We'll just count examples for keys not found in meanings
        pass  # handled by null on the sense side; orphan examples are simply not included
 
    stats = {
        "language": lang,
        "unique_idioms": len(idiom_ids),
        "total_senses": sense_count,
        "senses_with_examples": senses_with_examples,
        "senses_without_examples": senses_without_examples,
        "total_examples": example_count,
    }
 
    print(f"  ✓ Written {sense_count} senses → {output_path}")
    return stats
 
 
# ── Main ──────────────────────────────────────────────────────────────────────
 
def main():
    all_stats = []
    for lang in LANGUAGES:
        stats = merge_language(lang)
        all_stats.append(stats)
 
    # Print summary table
    print("\n" + "═" * 70)
    print(f"{'Language':<14} {'Idioms':>8} {'Senses':>8} {'w/ Examples':>12} {'Examples':>10}")
    print("─" * 70)
    for s in all_stats:
        print(
            f"{s['language']:<14} "
            f"{s['unique_idioms']:>8,} "
            f"{s['total_senses']:>8,} "
            f"{s['senses_with_examples']:>12,} "
            f"{s['total_examples']:>10,}"
        )
    print("═" * 70)
 
    # Save stats to JSON
    stats_path = BASE_DIR / "Final_Seed_Dataset" / "merge_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(all_stats, f, indent=2, ensure_ascii=False)
    print(f"\nStats saved → {stats_path}")
 
 
if __name__ == "__main__":
    main()