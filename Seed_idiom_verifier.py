# pip install googlesearch-python tqdm
import json
from googlesearch import search
from tqdm import tqdm
import asyncio
import random

INPUT_FILE = "./idioms_structured/seed_idioms_te_cleaned.jsonl"

OUTPUT_FILE = "./idioms_structured/telugu_idioms_verified.jsonl"

import json
from pathlib import Path
from tqdm import tqdm

# ------------------------------
# CONFIG
# ------------------------------
INPUT_FILE = "./idioms_structured/seed_idioms_te_cleaned.jsonl"
CORPUS_FOLDER = "./idioms_structured/Idiom_sentences/telugu_corpus_texts"       # folder with plain .txt files of Telugu sentences
OUTPUT_FILE = "./idioms_structured/telugu_idioms_verified.jsonl"

# Minimum occurrences to consider "modern"
MIN_OCCURRENCES_MODERN = 2

# ------------------------------
# Load corpus
# ------------------------------
def load_corpus(corpus_folder):
    corpus_sentences = []
    folder = Path(corpus_folder)
    for txt_file in folder.glob("*.txt"):
        with open(txt_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    corpus_sentences.append(line)
    return corpus_sentences

# ------------------------------
# Count occurrences
# ------------------------------
def count_idiom_occurrences(idiom, corpus_sentences):
    count = 0
    for sent in corpus_sentences:
        if idiom in sent:
            count += 1
    return count

# ------------------------------
# Main verification
# ------------------------------
def main():
    corpus_sentences = load_corpus(CORPUS_FOLDER)
    print(f"Loaded {len(corpus_sentences)} corpus sentences.")

    verified_idioms = []

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Processing idioms"):
            idiom_data = json.loads(line)
            idiom_text = idiom_data['idiom']

            count = count_idiom_occurrences(idiom_text, corpus_sentences)

            if count >= MIN_OCCURRENCES_MODERN:
                idiom_data['time_period'] = 'modern'
                idiom_data['usage_frequency'] = 'high' if count > 5 else 'medium'
                idiom_data['quality'] = 'verified'
            else:
                idiom_data['time_period'] = 'archaic'
                idiom_data['usage_frequency'] = 'low'
                idiom_data['quality'] = idiom_data.get('quality', 'seed')

            verified_idioms.append(idiom_data)

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for idiom_data in verified_idioms:
            f.write(json.dumps(idiom_data, ensure_ascii=False) + "\n")

    print(f"Verified idioms saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
