import json
import ahocorasick
from pathlib import Path
from collections import defaultdict
import string

# -----------------------------
# Config: language pairs
# -----------------------------
# Each entry: target language -> (source_file, target_file)
language_pairs = {
    "es": ("Parallel_Sentence_scrapers/OPUS_API/en-es/OpenSubtitles.en-es.en",
           "Parallel_Sentence_scrapers/OPUS_API/en-es/OpenSubtitles.en-es.es"),
    "hi": ("Parallel_Sentence_scrapers/OPUS_API/en-hi/NLLB.en-hi.en",
           "Parallel_Sentence_scrapers/OPUS_API/en-hi/NLLB.en-hi.hi"),
    "id": ("Parallel_Sentence_scrapers/OPUS_API/en-id/OpenSubtitles.en-id.en",
           "Parallel_Sentence_scrapers/OPUS_API/en-id/OpenSubtitles.en-id.id"),
    "te": ("Parallel_Sentence_scrapers/OPUS_API/en-te.txt/NLLB.en-te.en",
           "Parallel_Sentence_scrapers/OPUS_API/en-te.txt/NLLB.en-te.te"),
}

# Path to your idioms
idioms_path = Path("idioms_structured/seed_idioms_en_cleaned.jsonl")

# Output file
output_file = Path("English_all_idiom_examples.jsonl")
MAX_EXAMPLES_PER_IDIOM = 15

# -----------------------------
# Load idioms
# -----------------------------
idioms = []
with open(idioms_path, "r", encoding="utf-8") as f:
    for line in f:
        idioms.append(json.loads(line))

idiom_map = {i["idiom"]: i for i in idioms}

# Build Aho-Corasick automaton
A = ahocorasick.Automaton()
for idiom in idiom_map:
    A.add_word(idiom, idiom)
A.make_automaton()

# -----------------------------
# Prepare example collection
# -----------------------------
grouped_examples = defaultdict(lambda: {"translations": []})
idiom_counts = defaultdict(int)

# -----------------------------
# Process each language pair
# -----------------------------
for lang, (src_path, tgt_path) in language_pairs.items():
    print(f"Processing {lang} pair...")

    with open(src_path, "r", encoding="utf-8", errors="ignore") as f_src, \
         open(tgt_path, "r", encoding="utf-8", errors="ignore") as f_tgt:

        for line_count, (source_line, target_line) in enumerate(zip(f_src, f_tgt), start=1):
            if line_count % 100_000 == 0:
                print(f"Processed {line_count:,} lines ✅")

            source_line = source_line.strip()
            target_line = target_line.strip()
            if not source_line or not target_line:
                continue

            # Search for idioms in the source line
            for end_idx, idiom in A.iter(source_line):
                start_idx = end_idx - len(idiom) + 1

                # Word boundaries check
                before = source_line[start_idx - 1] if start_idx > 0 else " "
                after = source_line[end_idx + 1] if end_idx + 1 < len(source_line) else " "
                if not (before.isspace() or before in string.punctuation):
                    continue
                if not (after.isspace() or after in string.punctuation):
                    continue

                # Max examples per idiom
                if idiom_counts[idiom] >= MAX_EXAMPLES_PER_IDIOM:
                    continue

                entry = idiom_map[idiom]
                key = (idiom, source_line)
                ex = grouped_examples[key]

                # Initialize example metadata if new
                if "id" not in ex:
                    ex.update({
                        "id": entry["id"],
                        "idiom": idiom,
                        "source_language": "en",
                        "source_text": source_line,
                        "language": entry.get("language"),
                        "dialect": entry.get("dialect"),
                        "url": entry.get("url"),
                        "source": ", ".join(language_pairs.keys()),
                    })
                    idiom_counts[idiom] += 1

                # Append translation
                ex["translations"].append({
                    "language": lang,
                    "text": target_line
                })

# -----------------------------
# Write JSONL
# -----------------------------
with output_file.open("w", encoding="utf-8") as out:
    for ex in grouped_examples.values():
        json.dump(ex, out, ensure_ascii=False)
        out.write("\n")

print(f"Done! Saved all examples to {output_file}")
