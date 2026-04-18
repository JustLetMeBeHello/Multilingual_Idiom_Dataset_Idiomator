import json
from pathlib import Path
from datetime import datetime

language = "Hindi"

MERGED_PATH = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Merged_Meanings_{language}.jsonl"
RESULTS_DIR = Path(f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Reprompted_literal_meaning_Batch_Results/{language}")
OUTPUT_PATH = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Merged_Meanings_{language}_FINAL.jsonl"

# ---------------- LOAD BATCH RESULTS ----------------

def load_reprompt_results(results_dir):
    """
    Reads all labeled_results_batch_*.jsonl files and returns a dict:
    { idiom_id: { "relabelled_senses": {...} | None, "literal": "..." | None } }
    """
    results = {}
    for path in sorted(results_dir.glob("labeled_results_batch_*.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                idiom_id = item["idiom_id"]
                results[idiom_id] = {
                    "relabelled_senses": item.get("relabelled_senses"),
                    "literal": item.get("literal")
                }
    return results

reprompt_results = load_reprompt_results(RESULTS_DIR)

# ---------------- MERGE ----------------

def get_next_sense_number(senses):
    return max(s["sense_number"] for s in senses) + 1

def make_literal_sense(idiom_id, idiom_text, sense_number, definition):
    return {
        "idiom_id": idiom_id,
        "sense_number": sense_number,
        "register": [],
        "region": [],
        "definitions": definition,
        "version": 1,
        "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "idiom": idiom_text,
        "meaning_id": "",
        "Idiomaticity": "literal",
        "Register": ["literal_translation"],
        "Region": []
    }

updated = 0
added = 0

with open(MERGED_PATH, encoding="utf-8") as inp, \
     open(OUTPUT_PATH, "w", encoding="utf-8") as out:

    for line in inp:
        if not line.strip():
            continue

        idiom_id, senses = json.loads(line)
        result = reprompt_results.get(idiom_id)

        if result:
            relabelled = result.get("relabelled_senses")
            literal = result.get("literal")

            # Case 1: literal sense already existed — update in place
            if relabelled and isinstance(relabelled, dict):
                target_snum = relabelled.get("sense_number")
                for s in senses:
                    if s["sense_number"] == target_snum:
                        s["Idiomaticity"] = "literal_tentative"
                        s["Register"] = ["literal_translation"]
                        updated += 1
                        break

            # Case 2: freshly extracted literal — add as new sense
            elif literal and literal != "no literal meaning":
                idiom_text = senses[0].get("idiom", "") if senses else ""
                next_snum = get_next_sense_number(senses)
                new_sense = make_literal_sense(idiom_id, idiom_text, next_snum, literal)
                senses.append(new_sense)
                added += 1

        out.write(json.dumps([idiom_id, senses], ensure_ascii=False) + "\n")

print(f"Done. Updated in place: {updated} | New literal senses added: {added}")
print(f"Output → {OUTPUT_PATH}")