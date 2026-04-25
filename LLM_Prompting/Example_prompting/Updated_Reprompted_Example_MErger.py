import json
from pathlib import Path
from collections import defaultdict

FINAL_PATH = Path("idioms_structured/Final_Seed_Dataset/Cleaned/Spanish/Final_Spanish_CLEAN.jsonl")
EXAMPLES_PATH = Path("idioms_structured/Idiom_meanings/Example_Sentences/Spanish/Examples_Missing_Final_Spanish.jsonl")

OUTPUT_PATH = FINAL_PATH  # overwrite (or change if you want backup)


# ── Load new examples ─────────────────────────────────────────

def load_examples(path):
    index = defaultdict(list)

    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)

            key = (r["idiom_id"], r["sense_number"])
            index[key].extend(r.get("examples") or [])

    return index


# ── Update final dataset ─────────────────────────────────────

def update():
    examples = load_examples(EXAMPLES_PATH)

    updated = 0
    total = 0

    output_lines = []

    with open(FINAL_PATH, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            r = json.loads(line)
            total += 1

            key = (r.get("idiom_id"), r.get("sense_number"))

            if key in examples:
                r["examples"] = examples[key]
                updated += 1

            output_lines.append(r)

    # write back
    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        for r in output_lines:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nUpdated {updated}/{total} senses with new examples.")


if __name__ == "__main__":
    update()