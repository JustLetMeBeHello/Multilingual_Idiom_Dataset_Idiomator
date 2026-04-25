import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# ---------------- SETUP ----------------

load_dotenv()

language = "Telugu"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BATCH_SIZE = 20  # optimal balance for cost + context

INPUT_PATH = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Reprompt_Literal_Idioms.jsonl"
REQUEST_DIR = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Reprompted_literal_meaning_Batch_requests/{language}"
RESULT_DIR = f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Reprompted_literal_meaning_Batch_Results/{language}"

os.makedirs(REQUEST_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# ---------------- LOAD DATA ----------------

def get_idiom_list(path):
    """
    Load reprompt idioms. Each line is:
    {"idiom_id": "...", "idiom": "...", "senses": {"1": [...], "2": [...], ...}}

    Returns a list of (idiom_id, senses_list) tuples matching the format
    expected by build_user_prompt, where senses_list contains dicts with
    keys 'sense_number' and 'definitions'.
    """
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            idiom_id = obj["idiom_id"]
            senses_dict = obj.get("senses", {})
            # Convert {"1": ["def1", ...], "2": [...]} → list of sense dicts
            senses_list = [
                {
                    "sense_number": int(k),
                    "definitions": v if isinstance(v, list) else [v]
                }
                for k, v in sorted(senses_dict.items(), key=lambda x: int(x[0]))
            ]
            records.append((idiom_id, senses_list))
    return records

idioms = get_idiom_list(INPUT_PATH)
total_batches = (len(idioms) + BATCH_SIZE - 1) // BATCH_SIZE


# ---------------- PROMPT ----------------

SYSTEM_PROMPT = f"""
You are an expert {language} linguistic annotation system.

Task:
For each idiom, determine whether a literal meaning is already present in the provided senses or needs to be extracted.

Step 1 - Check for an existing literal sense:
- If one of the input senses is already literal (describes the physical/compositional meaning of the words), copy that sense into "relabelled_senses" as {{"sense_number": "...", "definition": "..."}}.
- Set "literal" to "no literal meaning" in this case — it is already captured in "relabelled_senses".

Step 2 - Extract a literal meaning if none exists:
- If NO input sense is literal, derive a literal meaning from the word-for-word translation of the idiom and place it in "literal".
- If no literal meaning can be derived, set "literal" to exactly: "no literal meaning".
- Leave "relabelled_senses" as null in this case.

Rules:
- Use ONLY the given data and the idiom text itself
- Output ONLY valid JSON — no explanations, no markdown
- Format:
[
  {{"idiom_id": "...", "relabelled_senses": {{"sense_number": 1, "definition": "..."}}, "literal": "no literal meaning"}},
  {{"idiom_id": "...", "relabelled_senses": null, "literal": "..."}}
]
"""

def build_user_prompt(batch):
    lines = ["DATA:\n"]

    for idiom_id, senses in batch:
        lines.append(f"{idiom_id}:")
        for s in senses:
            sn = s.get("sense_number")
            defs = s.get("definitions", [])
            if isinstance(defs, str):
                defs = [defs]
            defs_text = " | ".join(defs)
            lines.append(f"{sn}: {defs_text}")
        lines.append("")  # spacing

    return "\n".join(lines)

# ---------------- CREATE BATCH FILE ----------------

def create_batch_file(i):
    offset = i * BATCH_SIZE
    chunk = idioms[offset:offset + BATCH_SIZE]

    user_prompt = build_user_prompt(chunk)

    request = {
        "custom_id": f"batch_{i}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-4.1-mini",
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        }
    }

    path = os.path.join(REQUEST_DIR, f"batch_{i}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(request, ensure_ascii=False) + "\n")

    print(f"[Batch {i}] Created request file")
    return path

# ---------------- SUBMIT + WAIT ----------------

def submit_and_wait(batch_file, i):
    with open(batch_file, "rb") as f:
        file = client.files.create(file=f, purpose="batch")

    batch = client.batches.create(
        input_file_id=file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    print(f"[Batch {i}] Submitted → {batch.id}")

    while True:
        status = client.batches.retrieve(batch.id)
        print(f"[Batch {i}] Status: {status.status}")

        if status.status == "completed":
            return status, batch.id
        elif status.status in ["failed", "cancelled", "expired"]:
            print(f"[Batch {i}] Failed with status: {status.status}")
            return None, batch.id

        time.sleep(60)

# ---------------- DOWNLOAD RESULTS ----------------

def download_results(batch, i, batch_id):
    output = client.files.content(batch.output_file_id)

    output_file = os.path.join(RESULT_DIR, f"labeled_results_batch_{i}.jsonl")

    results = []

    for line in output.text.splitlines():
        if not line.strip():
            continue

        data = json.loads(line)

        try:
            content = data["response"]["body"]["choices"][0]["message"]["content"]
            parsed = json.loads(content)  # expecting list of idioms

            for item in parsed:
                item["batch_id"] = batch_id
                results.append(item)

        except Exception as e:
            print(f"[Batch {i}] Parse error:", e)

    with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # log batch ids
    with open("batch_ids.log", "a") as log:
        log.write(f"batch_{i}: {batch_id}\n")

    print(f"[Batch {i}] Saved {len(results)} idioms → {output_file}")

# ---------------- MAIN LOOP ----------------

for i in range(total_batches):
    output_file = os.path.join(RESULT_DIR, f"labeled_results_batch_{i}.jsonl")

    if os.path.exists(output_file):
        print(f"[Batch {i}] Already done, skipping.")
        continue

    print(f"\n--- Starting batch {i + 1}/{total_batches} ---")

    batch_file = create_batch_file(i)
    batch, batch_id = submit_and_wait(batch_file, i)

    print(f"[Batch {i}] Batch ID: {batch_id}")

    if batch:
        download_results(batch, i, batch_id)

print("\nAll batches complete.")