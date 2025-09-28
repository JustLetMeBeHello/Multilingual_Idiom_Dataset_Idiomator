import json
import ahocorasick
from pathlib import Path
from collections import defaultdict
import string

idioms_path = Path("idioms_structured/seed_idioms_es_cleaned.jsonl")
spanish_file = Path("Parallel_Sentence_scrapers/OPUS_API/en-es/OpenSubtitles.en-es.es")
english_file = Path("Parallel_Sentence_scrapers/OPUS_API/en-es/OpenSubtitles.en-es.en")

# Load idioms JSONL
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

output_file = Path("Idioms_all_examples.jsonl")
with output_file.open("w", encoding="utf-8") as out:
    line_count = 0
    with spanish_file.open("r", encoding="utf-8", errors="ignore") as f_es, \
         english_file.open("r", encoding="utf-8", errors="ignore") as f_en:

        for line_es, line_en in zip(f_es, f_en):
            line_count += 1
            if line_count % 100_000 == 0:
                print(f"Processed {line_count:,} lines ✅")

            for _, idiom in A.iter(line_es):
                start = line_es.find(idiom)
                end = start + len(idiom)

                # Word boundaries check
                before = line_es[start - 1] if start > 0 else " "
                after = line_es[end] if end < len(line_es) else " "
                valid_before = before.isspace() or before in string.punctuation
                valid_after = after.isspace() or after in string.punctuation
                if not (valid_before and valid_after):
                    continue

                # ✅ Enforce max examples per idiom
                if idiom_counts[idiom] >= 15:
                    continue

                entry = idiom_map[idiom]
                key = (idiom, line_es.strip())
                ex = grouped_examples[key]

                # If new example, initialize metadata
                if "id" not in ex:
                    ex.update({
                        "id": entry["id"],
                        "idiom": idiom,
                        "source_language": "es",
                        "source_text": line_es.strip(),
                        "language": entry.get("language"),
                        "dialect": entry.get("dialect"),
                        "url": entry.get("url"),
                        "source": "OpenSubtitles",
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

print(f"Done! Saved all examples to {output_file}")
