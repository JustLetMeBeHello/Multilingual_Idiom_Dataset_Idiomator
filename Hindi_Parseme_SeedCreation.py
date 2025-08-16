import conllu  # You might need to install this: pip install conllu
import json
import csv
from collections import defaultdict
import os

# --- Configuration ---
PARSEME_HINDI_FILE_PATH = "all_hindi.cupt"
OUTPUT_JSONL_FILE = "hindi_english_idioms_glossary.jsonl"
OUTPUT_CSV_FILE = "hindi_english_idioms_glossary.csv"

# --- Translation Function (MOCK - REPLACE THIS!) ---
def translate_hindi_to_english(text):
    translations = {
        "पाँव उखड़ गए": "to lose ground/courage",
        "हाथ बँधना": "to be helpless",
        "दिल जीत लिया": "to win someone's heart",
        "आँखों का तारा": "apple of one's eye",
        "कान भरना": "to instigate/poison someone's mind",
        "नाकों चने चबाना": "to give a hard time",
        "पेट में चूहे दौड़ना": "to be very hungry (lit. mice running in stomach)",
        "ईद का चाँद होना": "to be seen rarely (lit. to be the moon of Eid)",
        "अंधे की लाठी": "only support (lit. blind man's stick)",
        "ऊँट के मुँह में जीरा": "a drop in the ocean (lit. cumin in camel's mouth)",
        "हाथ मलना": "to regret",
        "दाँत खट्टे करना": "to defeat soundly",
        "लोहा लेना": "to fight bravely",
        "आग बबूला होना": "to be furious",
        "चार चाँद लगाना": "to add to the glory/beauty"
    }
    return translations.get(text, f"TRANSLATION_NEEDED: {text}")

# --- Main Extraction Pipeline ---
def run_extraction_pipeline():
    print(f"Starting idiom extraction pipeline...")
    print(f"Attempting to load dataset from: {PARSEME_HINDI_FILE_PATH}")

    try:
        with open(PARSEME_HINDI_FILE_PATH, "r", encoding="utf-8") as f:
            data = f.read()
        sentences = conllu.parse(data)
        print(f"Successfully loaded {len(sentences)} sentences from the dataset.")
    except FileNotFoundError:
        print(f"ERROR: Dataset file not found at '{PARSEME_HINDI_FILE_PATH}'.")
        return
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while loading/parsing the dataset: {e}")
        return

    extracted_idioms = {}

    print("Iterating through sentences to extract idioms...")
    for sent_idx, sentence in enumerate(sentences):
        current_mwe_groups = defaultdict(list)
        mwe_types_in_sentence = {}

        original_sentence_text = sentence.metadata.get('text', '')

        for token in sentence:
            mwe_field = token["misc"]
            if mwe_field and mwe_field != "*":
                mwe_entries = mwe_field.split('|')
                for entry in mwe_entries:
                    if ':' in entry:
                        mwe_id, mwe_type = entry.split(':', 1)
                        mwe_type = mwe_type.replace('.full', '')
                        current_mwe_groups[mwe_id].append(token["form"])
                        mwe_types_in_sentence[mwe_id] = mwe_type

        for mwe_id, forms in current_mwe_groups.items():
            hindi_idiom_form = " ".join(forms)
            mwe_type = mwe_types_in_sentence.get(mwe_id, "UNKNOWN_TYPE")
            if hindi_idiom_form not in extracted_idioms:
                extracted_idioms[hindi_idiom_form] = {
                    "mwe_type": mwe_type,
                    "example_sentence_hindi": original_sentence_text,
                    "english_translation": ""
                }

    print(f"Extracted {len(extracted_idioms)} unique Hindi idioms based on PARSEME annotations.")

    # --- Build Bilingual Glossary ---
    final_glossary_data = []
    print("Beginning translation phase (using MOCK translation function)...")
    print("REMINDER: Replace 'translate_hindi_to_english' with a real MT API for production use.")

    for hindi_idiom, details in extracted_idioms.items():
        english_translation = translate_hindi_to_english(hindi_idiom)
        english_example_sentence = translate_hindi_to_english(details["example_sentence_hindi"])
        final_glossary_data.append({
            "hindi_idiom": hindi_idiom,
            "mwe_type": details["mwe_type"],
            "english_translation": english_translation,
            "example_sentence_hindi": details["example_sentence_hindi"],
            "example_sentence_english": english_example_sentence
        })
    print("Translation phase complete.")

    # --- Output to JSONL ---
    print(f"Writing glossary to {OUTPUT_JSONL_FILE}...")
    try:
        with open(OUTPUT_JSONL_FILE, "w", encoding="utf-8") as f:
            for entry in final_glossary_data:
                json.dump(entry, f, ensure_ascii=False)
                f.write("\n")
        print(f"JSONL output complete: {OUTPUT_JSONL_FILE}")
    except Exception as e:
        print(f"ERROR: Could not write JSONL file: {e}")

    # --- Output to CSV ---
    print(f"Writing glossary to {OUTPUT_CSV_FILE}...")
    fieldnames = ["hindi_idiom", "mwe_type", "english_translation", "example_sentence_hindi", "example_sentence_english"]
    try:
        with open(OUTPUT_CSV_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(final_glossary_data)
        print(f"CSV output complete: {OUTPUT_CSV_FILE}")
    except Exception as e:
        print(f"ERROR: Could not write CSV file: {e}")

    print("Pipeline finished.")

if __name__ == "__main__":
    run_extraction_pipeline()
