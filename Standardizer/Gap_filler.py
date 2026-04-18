import json
language = "Spanish"
INPUT_PATH  = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Merged_Meanings_{language}.jsonl"
OUTPUT_PATH = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Merged_Meanings_{language}_RENUMBERED.jsonl"

records = []

# Load all records
with open(INPUT_PATH, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))

# Sort by current numeric suffix (important!)
records.sort(key=lambda x: int(x[0][-4:]))

# Renumber
for i, (old_id, senses) in enumerate(records):
    new_id = f"en_unspecified_{i:04d}"

    for sense in senses:
        sense["idiom_id"] = new_id  # update inside each sense

    records[i][0] = new_id  # update top-level ID

# Write output
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"Done. Renumbered {len(records)} idioms with no gaps.")