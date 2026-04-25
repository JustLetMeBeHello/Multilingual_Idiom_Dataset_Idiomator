"""
merge_literal_reprompt.py
 
Merges recovered literal senses from Stage 3b back into the main
Merged_Meanings_{lang}.jsonl, producing Merged_Meanings_{lang}_FINAL.jsonl.
 
For each idiom in the reprompt results:
  - If "relabelled_senses" is present → one of the existing senses was
    identified as literal; update that sense's Idiomaticity to "literal"
  - If "literal" is a non-empty string (not "no literal meaning") →
    a new literal sense is derived; append it as a new sense
 
Run from the root of your project:
  python merge_literal_reprompt.py
"""
 
import json
import os
from pathlib import Path
from collections import defaultdict
 
# ── Config ────────────────────────────────────────────────────────────────────
 
LANGUAGES = ["English", "Spanish", "Indonesian", "Telugu", "Hindi"]
 
MERGED_TEMPLATE  = "idioms_structured/Idiom_meanings/Labelled_Meanings/{lang}/Merged_Meanings_{lang}_RENUMBERED.jsonl"
RESULTS_TEMPLATE = "idioms_structured/Idiom_meanings/Labelled_Meanings/{lang}/Reprompted_literal_meaning_Batch_Results/{lang}"
OUTPUT_TEMPLATE  = "idioms_structured/Idiom_meanings/Labelled_Meanings/{lang}/Merged_Meanings_{lang}_FINAL.jsonl"
 
# ── Load reprompt results ─────────────────────────────────────────────────────
 
def load_reprompt_results(result_dir: str) -> dict:
    """
    Load all batch result files and key by idiom_id.
    Returns { idiom_id: { relabelled_senses, literal } }
    """
    result_map = {}
    result_path = Path(result_dir)
 
    if not result_path.exists():
        print(f"  [WARN] Result dir not found: {result_path}")
        return result_map
 
    for path in sorted(result_path.glob("labeled_results_batch_*.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                idiom_id = rec.get("idiom_id")
                if idiom_id:
                    result_map[idiom_id] = rec
 
    print(f"  Loaded {len(result_map):,} reprompt results")
    return result_map
 
 
# ── Merge ─────────────────────────────────────────────────────────────────────
 
def merge(lang: str):
    merged_path = Path(MERGED_TEMPLATE.format(lang=lang))
    result_dir  = RESULTS_TEMPLATE.format(lang=lang)
    output_path = OUTPUT_TEMPLATE.format(lang=lang)
 
    if not merged_path.exists():
        print(f"  [WARN] Merged meanings file not found: {merged_path} — skipping.")
        return
 
    reprompt_map = load_reprompt_results(result_dir)
 
    updated = 0
    appended = 0
    unchanged = 0
 
    with open(merged_path, encoding="utf-8") as inp, \
         open(output_path, "w", encoding="utf-8") as out:
 
        for line in inp:
            line = line.strip()
            if not line:
                continue
 
            idiom_id, senses = json.loads(line)
            rec = reprompt_map.get(idiom_id)
 
            if rec is None:
                # No reprompt result for this idiom — write as-is
                unchanged += 1
                out.write(json.dumps([idiom_id, senses], ensure_ascii=False) + "\n")
                continue
 
            relabelled = rec.get("relabelled_senses")
            literal    = rec.get("literal", "")
 
            if relabelled and isinstance(relabelled, dict):
                # An existing sense was identified as literal — update its Idiomaticity
                target_sn = relabelled.get("sense_number")
                for s in senses:
                    if s.get("sense_number") == target_sn:
                        s["Idiomaticity"] = "literal"
                        # Optionally update definition if the model cleaned it
                        if relabelled.get("definition"):
                            existing = s.get("definitions", [])
                            if isinstance(existing, str):
                                existing = [existing]
                            if relabelled["definition"] not in existing:
                                existing.append(relabelled["definition"])
                            s["definitions"] = existing
                        break
                updated += 1
 
            elif literal and literal.strip().lower() != "no literal meaning":
                # Derive a new literal sense and append it
                next_sense_number = max((s.get("sense_number") or 0) for s in senses) + 1
                idiom_text = senses[0].get("idiom", "") if senses else ""
                new_sense = {
                    "idiom":         idiom_text,
                    "sense_number":  next_sense_number,
                    "definitions":   [literal.strip()],
                    "Idiomaticity":  "literal",
                    "Register":      ["neutral"],
                    "Region":        [],
                    "register":      ["neutral"],
                    "region":        [],
                }
                senses.append(new_sense)
                appended += 1
 
            else:
                unchanged += 1
 
            out.write(json.dumps([idiom_id, senses], ensure_ascii=False) + "\n")
 
    print(f"  ✓ Senses relabelled in-place : {updated:,}")
    print(f"  ✓ New literal senses appended: {appended:,}")
    print(f"  — Unchanged                  : {unchanged:,}")
    print(f"  Output → {output_path}")
 
 
# ── Main ──────────────────────────────────────────────────────────────────────
 
def main():
    for lang in LANGUAGES:
        print(f"\n{'═' * 60}")
        print(f"  Language: {lang}")
        print(f"{'═' * 60}")
        merge(lang)
 
    print(f"\n{'═' * 60}")
    print("  All languages merged.")
    print(f"{'═' * 60}\n")
 
 
if __name__ == "__main__":
    main()