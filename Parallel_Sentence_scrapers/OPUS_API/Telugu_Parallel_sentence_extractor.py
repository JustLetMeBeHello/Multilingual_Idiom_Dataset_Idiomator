import json
import ahocorasick
from pathlib import Path
from collections import defaultdict
import string

# Paths for Telugu idioms and parallel corpus
idioms_path = Path("idioms_structured/seed_idioms_te_cleaned.jsonl")
telugu_file = Path("Parallel_Sentence_scrapers/OPUS_API/en-te.txt/NLLB.en-te.te")
english_file = Path("Parallel_Sentence_scrapers/OPUS_API/en-te.txt/NLLB.en-te.en")

# Load Telugu idioms JSONL
idioms = []
with open(idioms_path, "r", encoding="utf-8") as f:
    for line in f:
        idioms.append(json.loads(line))

idiom_map = {i["idiom"]: i for i in idioms}

# Build Aho–Corasick automaton
A = ahocorasick.Automaton()
for idiom in idiom_map:
    A.add_word(idiom, idiom)
A.make_automaton()

# Track grouped examples by (idiom, source_text)
grouped_examples = defaultdict(lambda: {"translations": []})
# Track total count per idiom
idiom_counts = defaultdict(int)

output_file = Path("Idioms_all_examples_te.jsonl")
with output_file.open("w", encoding="utf-8") as out:
    line_count = 0
    with telugu_file.open("r", encoding="utf-8", errors="ignore") as f_te, \
         english_file.open("r", encoding="utf-8", errors="ignore") as f_en:

        for line_te, line_en in zip(f_te, f_en):
            line_count += 1
            if line_count % 100_000 == 0:
                print(f"Processed {line_count:,} lines ✅")

            for _, idiom in A.iter(line_te):
                start = line_te.find(idiom)
                end = start + len(idiom)

                # Word boundaries check
                before = line_te[start - 1] if start > 0 else " "
                after = line_te[end] if end < len(line_te) else " "
                valid_before = before.isspace() or before in string.punctuation
                valid_after = after.isspace() or after in string.punctuation
                if not (valid_before and valid_after):
                    continue

                # ✅ Enforce max examples per idiom
                if idiom_counts[idiom] >= 15:
                    continue

                entry = idiom_map[idiom]
                key = (idiom, line_te.strip())
                ex = grouped_examples[key]

                # If new example, initialize metadata
                if "id" not in ex:
                    ex.update({
                        "id": entry["id"],
                        "idiom": idiom,
                        "source_language": "te",
                        "source_text": line_te.strip(),
                        "language": entry.get("language"),
                        "dialect": entry.get("dialect"),
                        "url": entry.get("url"),
                        "source": "NLLB",
                    })
                    idiom_counts[idiom] += 1  # count once per source_text

                # Always append English translation
                ex["translations"].append({
                    "language": "en",
                    "text": line_en.strip()
                })

    # Write all grouped examples
    for ex in grouped_examples.values():
        json.dump(ex, out, ensure_ascii=False)
        out.write("\n")

print(f"Done! Saved all Telugu examples to {output_file}")
