import json
from pathlib import Path

language = "Indonesian"
INPUT_JSONL = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Merged_Meanings_{language}.jsonl"
FLAGGED_IDS = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/No_Literal_Idioms.txt"
OUTPUT_PATH = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Reprompt_Literal_Idioms.jsonl"

Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)

with open(FLAGGED_IDS, encoding="utf-8") as f:
    flagged = set(line.strip() for line in f if line.strip())

count_written = 0

with open(INPUT_JSONL, encoding="utf-8") as inp, \
     open(OUTPUT_PATH, "w", encoding="utf-8") as out:
    for line in inp:
        line = line.strip()
        if not line:
            continue
        idiom_id, senses = json.loads(line)
        if idiom_id not in flagged:
            continue

        idiom_text = senses[0].get("idiom") if senses else ""

        sense_dict = {}
        for s in senses:
            snum = s.get("sense_number")
            defs = s.get("definitions", [])
            if isinstance(defs, str):       # ← fix: wrap bare string
                defs = [defs]
            cleaned_defs = [d.strip() for d in defs if d.strip()]
            sense_dict[snum] = cleaned_defs

        record = {
            "idiom_id": idiom_id,
            "idiom": idiom_text,
            "senses": sense_dict
        }
        out.write(json.dumps(record, ensure_ascii=False) + "\n")
        count_written += 1

print(f"Done. Wrote {count_written} idioms for re-prompting.")