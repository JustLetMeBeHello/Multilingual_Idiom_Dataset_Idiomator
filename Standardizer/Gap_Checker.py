import json
 
# ---------------------------------------------------------------------------
# Configure paths here
# ---------------------------------------------------------------------------
 
INPUT_PATH  = "idioms_structured/Idiom_meanings/Unlabelled_Meanings/English/Raw_Meanings_Ordered_Flattened.jsonl"
OUTPUT_PATH = "idioms_structured/Idiom_meanings/Idiom_ID_Gaps.txt"
 
# ---------------------------------------------------------------------------
 
gaps = []
prev_num = None
prev_id  = None
 
with open(INPUT_PATH, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
 
        idiom_id, _ = json.loads(line)
        num = int(idiom_id[-4:])
 
        if prev_num is not None and num != prev_num + 1:
            gaps.append(f"{prev_id} -> {idiom_id}  (expected {prev_id[:-4]}{prev_num + 1:04d}, got {idiom_id})")
 
        prev_num = num
        prev_id  = idiom_id
 
with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
    if gaps:
        out.write(f"Found {len(gaps)} gap(s):\n\n")
        out.write("\n".join(gaps) + "\n")
    else:
        out.write("No gaps found — all idiom IDs are sequential.\n")
 
print(f"Done. {len(gaps)} gap(s) found. Output: {OUTPUT_PATH}")