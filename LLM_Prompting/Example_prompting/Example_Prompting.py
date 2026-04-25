import json
import os
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

POLL_INTERVAL = 60
BATCH_SIZE = 30


def run(
    language: str,
    input_path: str,
    request_dir: str,
    result_dir: str,
    output_path: str,
):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    os.makedirs(request_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)

    # ---------------- LOAD DATA ----------------

    def load_senses(path):
        senses = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                idiom_id, sense_list = json.loads(line)
                for s in sense_list:
                    senses.append({
                        "idiom_id": idiom_id,
                        "idiom": s.get("idiom", ""),
                        "sense_number": s.get("sense_number"),
                        "definitions": s.get("definitions", ""),
                        "Idiomaticity": s.get("Idiomaticity", "")
                    })
        return senses

    senses = load_senses(input_path)
    total_batches = (len(senses) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Loaded {len(senses)} senses → {total_batches} batches")

    # ---------------- PROMPT ----------------

    SYSTEM_PROMPT = f"""
You are an expert {language} linguist generating natural, varied example sentences for idiom senses.

Task:
For each sense, generate example sentences in {language} with English translations.

Rules:
- Generate 3 sentences for idiomatic senses, 4 sentences for literal senses
- Each sentence must embed the idiom naturally with realistic surrounding context
- Context should feel like real speech or writing — include names, situations, backstory where natural.
  For example, rather than just "He let the cat out of the bag", write something like:
  "I told Mark not to say anything, but of course he let the cat out of the bag before I could surprise her."
- Vary morphology across sentences. Explicitly use different forms such as:
  - Different tenses (past, present, future, conditional)
  - Different persons (1st, 2nd, 3rd person)
  - Passive and active voice
  - Negation
  - Question forms
- Sentences should feel natural, not mechanical or repetitive
- Output ONLY valid JSON — no explanations, no markdown
- Format:
[
  {{
    "idiom_id": "...",
    "sense_number": 1,
    "examples": [
      {{"sentence": "...", "translation": "..."}},
      ...
    ]
  }}
]
"""

    def build_user_prompt(batch):
        lines = ["DATA:\n"]
        for s in batch:
            defs = s["definitions"]
            defs_text = " | ".join(defs) if isinstance(defs, list) else defs
            sentence_count = 4 if "literal" in str(s["Idiomaticity"]).lower() else 3
            lines.append(f"{s['idiom_id']} | sense {s['sense_number']} | idiom: {s['idiom']} | type: {s['Idiomaticity']} | sentences: {sentence_count}")
            lines.append(f"Definition: {defs_text}")
            lines.append("")
        return "\n".join(lines)

    # ---------------- CREATE ALL BATCH FILES ----------------

    def create_all_batch_files():
        paths = []
        for i in range(total_batches):
            path = os.path.join(request_dir, f"batch_{i}.jsonl")
            if not os.path.exists(path):
                chunk = senses[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
                request = {
                    "custom_id": f"batch_{i}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4.1-mini",
                        "temperature": 0.7,
                        "max_tokens": 16000,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": build_user_prompt(chunk)}
                        ]
                    }
                }
                with open(path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(request, ensure_ascii=False) + "\n")
            paths.append((i, path))
        print(f"All batch request files ready.")
        return paths

    # ---------------- SUBMIT ALL ----------------

    def submit_all(batch_paths):
        submitted = []
        for i, path in batch_paths:
            result_file = os.path.join(result_dir, f"examples_batch_{i}.jsonl")
            if os.path.exists(result_file):
                print(f"[Batch {i}] Already done, skipping.")
                continue
            with open(path, "rb") as f:
                file = client.files.create(file=f, purpose="batch")
            batch = client.batches.create(
                input_file_id=file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )
            print(f"[Batch {i}] Submitted → {batch.id}")
            submitted.append((i, batch.id))
            time.sleep(0.5)
        return submitted

    # ---------------- POLL ALL ----------------

    def poll_all(submitted):
        pending = dict(submitted)
        while pending:
            still_pending = {}
            for i, batch_id in pending.items():
                status = client.batches.retrieve(batch_id)
                print(f"[Batch {i}] Status: {status.status}")
                if status.status == "completed":
                    download_results(status, i, batch_id)
                elif status.status in ["failed", "cancelled", "expired"]:
                    print(f"[Batch {i}] Failed with status: {status.status}")
                else:
                    still_pending[i] = batch_id
            pending = still_pending
            if pending:
                print(f"\n{len(pending)} batches still pending, waiting {POLL_INTERVAL}s...\n")
                time.sleep(POLL_INTERVAL)

    # ---------------- DOWNLOAD RESULTS ----------------

    def download_results(batch, i, batch_id):
        output = client.files.content(batch.output_file_id)
        output_file = os.path.join(result_dir, f"examples_batch_{i}.jsonl")

        results = []
        for line in output.text.splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            try:
                content = data["response"]["body"]["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                for item in parsed:
                    item["batch_id"] = batch_id
                    results.append(item)
            except Exception as e:
                print(f"[Batch {i}] Parse error: {e}")

        with open(output_file, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        with open("batch_ids.log", "a") as log:
            log.write(f"examples_{language}_batch_{i}: {batch_id}\n")

        print(f"[Batch {i}] Saved {len(results)} senses → {output_file}")

    # ---------------- MERGE ----------------

    def merge_results():
        seen = set()
        all_items = []

        for path in sorted(Path(result_dir).glob("examples_batch_*.jsonl")):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    key = (item.get("idiom_id"), item.get("sense_number"))
                    if key not in seen:
                        seen.add(key)
                        all_items.append(item)

        def sort_key(item):
            idiom_id = item.get("idiom_id", "")
            last_four = int(idiom_id[-4:]) if idiom_id[-4:].isdigit() else 0
            sense_number = item.get("sense_number", 0)
            return (last_four, sense_number)

        all_items.sort(key=sort_key)

        with open(output_path, "w", encoding="utf-8") as out:
            for item in all_items:
                out.write(json.dumps(item, ensure_ascii=False) + "\n")

        print(f"\nMerged output → {output_path} ({len(all_items)} senses)")

    # ---------------- MAIN ----------------

    batch_paths = create_all_batch_files()
    submitted = submit_all(batch_paths)
    poll_all(submitted)
    print("\nAll batches complete. Merging results...")
    merge_results()


# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":
    language = "English"
    run(
        language=language,
        input_path=f"idioms_structured/Idiom_meanings/Labelled_Meanings/{language}/Merged_Meanings_{language}_FINAL.jsonl",
        request_dir=f"idioms_structured/Idiom_meanings/Example_Sentences/{language}/Unfullfilled_Batch_Requests",
        result_dir=f"idioms_structured/Idiom_meanings/Example_Sentences/{language}/Unfullfilled_Batch_Results",
        output_path=f"idioms_structured/Idiom_meanings/Example_Sentences/{language}/Examples_{language}.jsonl",
    )