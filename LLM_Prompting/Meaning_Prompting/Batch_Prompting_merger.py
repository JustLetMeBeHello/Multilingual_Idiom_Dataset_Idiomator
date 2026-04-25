import glob
import json
import os
import sys
 
# ---------------------------------------------------------------------------
# Configure paths here
# ---------------------------------------------------------------------------
language = "Spanish"
RAW_PATH    = f"idioms_structured/Idiom_meanings/Unlabelled_Meanings/{language}/Raw_Meanings_Ordered_Flattened.jsonl"
LABELED_DIR = f"idioms_structured/Idiom_meanings/Batch_Results/{language}"
OUTPUT_PATH = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Merged_Meanings_{language}.jsonl"
 
# ---------------------------------------------------------------------------
 
def clean_sense(sense):
    cleaned = {}
    for k, v in sense.items():
        clean_key = k.rstrip("\r")
        clean_val = v.rstrip("\r") if isinstance(v, str) else v
        cleaned[clean_key] = clean_val
    return cleaned
 
 
def load_labeled_files(labeled_dir):
    pattern = os.path.join(labeled_dir, "labeled_results_batch_*.jsonl")
    paths = sorted(glob.glob(pattern))
    if not paths:
        sys.exit(f"No labeled batch files found at: {pattern}")
 
    index = {}
    total = 0
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                key = (rec["Idiom_id"], rec["Sense_number"])
                index[key] = rec
                total += 1
 
    print(f"Loaded {total} labeled records from {len(paths)} file(s).")
    return index
 
 
def merge(raw_path, labeled_index, output_path):
    matched = 0
    unmatched = 0
    total_senses = 0
 
    with open(raw_path, encoding="utf-8") as raw_fh, \
         open(output_path, "w", encoding="utf-8") as out_fh:
 
        for line in raw_fh:
            line = line.strip()
            if not line:
                continue
 
            idiom_id, senses = json.loads(line)
            merged_senses = []
 
            for sense in senses:
                sense = clean_sense(sense)
                total_senses += 1
 
                key = (idiom_id, sense["sense_number"])
                label = labeled_index.get(key)
 
                if label is not None:
                    sense["Idiomaticity"] = label.get("Idiomaticity")
                    sense["Register"]     = label.get("Register", sense.get("register"))
                    sense["Region"]       = label.get("Region",   sense.get("region"))
                    matched += 1
                else:
                    sense["Idiomaticity"] = None
                    unmatched += 1
 
                merged_senses.append(sense)
 
            out_fh.write(json.dumps([idiom_id, merged_senses], ensure_ascii=False) + "\n")
 
    print(f"Done.  Total senses: {total_senses}  |  Labeled: {matched}  |  Unlabeled: {unmatched}")
    print(f"Output written to: {output_path}")
 
os.makedirs(f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}", exist_ok=True)
labeled_index = load_labeled_files(LABELED_DIR)
merge(RAW_PATH, labeled_index, OUTPUT_PATH)