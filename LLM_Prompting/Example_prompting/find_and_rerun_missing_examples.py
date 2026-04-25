"""
find_and_rerun_missing_examples.py

Finds idiom senses that are missing examples and reruns the Example_Prompting
pipeline on just those senses.

For each language:
  1. Loads all senses from the meanings file
  2. Loads already-generated examples from Examples_{lang}.jsonl
  3. Finds senses with no examples (or not present at all)
  4. Writes a temp meanings file containing only the missing senses
  5. Wipes Missing_Batch_Requests and Missing_Batch_Results to ensure a clean run
  6. Calls example_prompting.run() directly with the correct paths
  7. Merges the newly generated examples back into the main Examples_{lang}.jsonl

Run from the root of your project:
  python find_and_rerun_missing_examples.py

You can restrict to specific languages by editing LANGUAGES below.
"""

import json
import os
import sys
import shutil
from pathlib import Path
from collections import defaultdict

# ── Add the prompting script's directory to sys.path so it can be imported ───

PROMPTING_SCRIPT = "LLM_Prompting/Example_prompting/Example_Prompting.py"

script_dir = str(Path(PROMPTING_SCRIPT).parent.resolve())
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import Example_Prompting as example_prompting  # clean import, no exec_module hacks

# ── Config ────────────────────────────────────────────────────────────────────

LANGUAGES = ["English", "Spanish", "Indonesian", "Telugu", "Hindi"]

MEANINGS_TEMPLATE = "idioms_structured/Idiom_meanings/Labelled_Meanings/{lang}/Merged_Meanings_{lang}_FINAL.jsonl"
EXAMPLES_TEMPLATE = "idioms_structured/Idiom_meanings/Example_Sentences/{lang}/Examples_{lang}.jsonl"
MISSING_TEMPLATE  = "idioms_structured/Idiom_meanings/Labelled_Meanings/{lang}/MISSING_Meanings_{lang}.jsonl"

# ── Step 1: Find missing senses ───────────────────────────────────────────────

def load_all_senses(meanings_path: Path) -> dict:
    senses = {}
    if not meanings_path.exists():
        print(f"  [WARN] Meanings file not found: {meanings_path}")
        return senses
    with open(meanings_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idiom_id, sense_list = json.loads(line)
            for s in sense_list:
                key = (idiom_id, s.get("sense_number"))
                senses[key] = s
    return senses


def load_existing_example_keys(examples_path: Path) -> set:
    keys = set()
    if not examples_path.exists():
        return keys
    with open(examples_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            exs = record.get("examples") or []
            if exs:
                keys.add((record["idiom_id"], record["sense_number"]))
    return keys


def find_missing(lang: str) -> list:
    meanings_path = Path(MEANINGS_TEMPLATE.format(lang=lang))
    examples_path = Path(EXAMPLES_TEMPLATE.format(lang=lang))

    all_senses    = load_all_senses(meanings_path)
    existing_keys = load_existing_example_keys(examples_path)

    missing_keys = [k for k in all_senses if k not in existing_keys]

    print(f"  Total senses  : {len(all_senses):,}")
    print(f"  Have examples : {len(existing_keys):,}")
    print(f"  Missing       : {len(missing_keys):,}")

    if not missing_keys:
        return []

    grouped = defaultdict(list)
    for key in missing_keys:
        idiom_id, _ = key
        grouped[idiom_id].append(all_senses[key])

    for idiom_id in grouped:
        grouped[idiom_id].sort(key=lambda s: s.get("sense_number", 0))

    return list(grouped.items())


# ── Step 2: Write temp meanings file ─────────────────────────────────────────

def write_temp_meanings(lang: str, missing_groups: list) -> Path:
    temp_path = Path(MISSING_TEMPLATE.format(lang=lang))
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_path, "w", encoding="utf-8") as f:
        for idiom_id, sense_list in missing_groups:
            f.write(json.dumps([idiom_id, sense_list], ensure_ascii=False) + "\n")
    print(f"  Temp meanings file → {temp_path}  ({len(missing_groups)} idioms)")
    return temp_path


# ── Step 3: Run prompting via clean run() call ────────────────────────────────

def run_prompting_for_missing(lang: str, temp_meanings_path: Path) -> Path:
    missing_output      = f"idioms_structured/Idiom_meanings/Example_Sentences/{lang}/Missing_Examples_{lang}.jsonl"
    missing_request_dir = f"idioms_structured/Idiom_meanings/Example_Sentences/{lang}/Missing_Batch_Requests"
    missing_result_dir  = f"idioms_structured/Idiom_meanings/Example_Sentences/{lang}/Missing_Batch_Results"

    # Wipe leftover batch files from any previous recovery run
    for folder in [missing_request_dir, missing_result_dir]:
        folder_path = Path(folder)
        if folder_path.exists():
            shutil.rmtree(folder_path)
            print(f"  [CLEAN] Wiped old folder: {folder_path}")
        folder_path.mkdir(parents=True, exist_ok=True)

    # Wipe old Missing_Examples output so merge starts fresh
    missing_output_path = Path(missing_output)
    if missing_output_path.exists():
        missing_output_path.unlink()
        print(f"  [CLEAN] Wiped old output: {missing_output_path}")

    print(f"  Running prompting for {lang} missing senses...")

    example_prompting.run(
        language=lang,
        input_path=str(temp_meanings_path),
        request_dir=missing_request_dir,
        result_dir=missing_result_dir,
        output_path=missing_output,
    )

    return missing_output_path


# ── Step 4: Merge new examples back into main file ───────────────────────────

def merge_new_examples_back(lang: str, new_examples_path: Path):
    main_path = Path(EXAMPLES_TEMPLATE.format(lang=lang))

    if not new_examples_path.exists():
        print(f"  [WARN] New examples file not found: {new_examples_path}")
        return

    existing_keys = load_existing_example_keys(main_path)

    new_count = 0
    with open(main_path, "a", encoding="utf-8") as out:
        with open(new_examples_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                key = (record.get("idiom_id"), record.get("sense_number"))
                if key not in existing_keys:
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    existing_keys.add(key)
                    new_count += 1

    print(f"  ✓ Merged {new_count} new senses into {main_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    for lang in LANGUAGES:
        print(f"\n{'═' * 60}")
        print(f"  Language: {lang}")
        print(f"{'═' * 60}")

        missing_groups = find_missing(lang)

        if not missing_groups:
            print(f"  ✓ No missing examples — skipping.\n")
            continue

        temp_path = write_temp_meanings(lang, missing_groups)
        new_examples_path = run_prompting_for_missing(lang, temp_path)
        merge_new_examples_back(lang, new_examples_path)

        temp_path.unlink(missing_ok=True)
        print(f"  Cleaned up temp file: {temp_path}")

    print(f"\n{'═' * 60}")
    print("  All languages processed.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()