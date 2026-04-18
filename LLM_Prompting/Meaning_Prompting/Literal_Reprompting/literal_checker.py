import json
from pathlib import Path
language = "Indonesian"
INPUT_PATH  = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Merged_Meanings_{language}.jsonl"
OUTPUT_PATH = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/No_Literal_Idioms.txt"

# ensure output directory exists
Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)

count_total = 0
count_flagged = 0

with open(INPUT_PATH, encoding="utf-8") as inp, \
     open(OUTPUT_PATH, "w", encoding="utf-8") as out:

    for line in inp:
        line = line.strip()
        if not line:
            continue

        idiom_id, senses = json.loads(line)
        count_total += 1

        # check if ANY sense is labeled "literal"
        has_literal = any(
            (s.get("Idiomaticity") or "").lower() == "literal"
            for s in senses
        )

        # if NONE are literal → write idiom_id only
        if not has_literal:
            out.write(idiom_id + "\n")
            count_flagged += 1

print(f"Done. {count_flagged}/{count_total} idioms have NO literal senses.")