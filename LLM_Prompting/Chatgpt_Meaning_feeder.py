import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()  # ← loads .env into environment before os.getenv is called

language = "Spanish"
client = OpenAI(api_key = os.getenv("OPENAI_API_KEY"))

BATCH_SIZE = 30

def Get_idiom_list(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        return [json.loads(line) for line in json_file if line.strip()]

List_of_idioms = Get_idiom_list(f"idioms_structured/Idiom_meanings/Unlabelled_Meanings/{language}/Raw_Meanings_Ordered_Flattened.jsonl")

total_batches = (len(List_of_idioms) + BATCH_SIZE - 1) // BATCH_SIZE


def prompt_builder(definitions, idiom, sense_number, regions, register, idiom_id):
    system_prompt = f"""
        You are an expert {language} linguistic annotator that labels idiom senses.
        You will receive one idiom sense per request. Your task is to produce a structured JSON object that normalizes and labels the input.
        TASK OBJECTIVES
        For each input:
        Determine whether the sense is idiomatic or literal.
        Normalize register into standardized categories.
        Normalize region into standardized linguistic or geographic categories.
        LABELING RULES

        1. Idiomaticity
        Return exactly one value:
        "idiomatic" → meaning is non-compositional or metaphorical usage for example kick the bucket as a synonym for dying
        "literal" → meaning is directly compositional or directly decipherable for example let the cat out of the bag when a cat is literally inside of a bag
        Base decision strictly on semantic interpretation and general usage of the sense meaning.

        2. Sense Number and Idiom_id
        Copy exactly from input.


        3. Register normalization
        Based on input and internal reasoning cap input register into one or more of:
        formal
        informal
        slang
        neutral
        literary
        archaic
        technical
        if input is marked with _tentative disregard the input register and relabel the register using internal reasoning
        Always output as a list.

        4. Region normalization
        Based on input and internal reasoning convert region into standardized linguistic or geographic labels.
        Allowed forms include:
        American English
        British English
        Indian English
        Australian English
        Global English
        Origin-based labels when relevant (e.g., Biblical, Latin origin)
        If input is marked with _tentative disregard the input register and relabel the region using internal reasoning.
        Always output as a list.
        OUTPUT FORMAT (STRICT)
        Return ONLY valid JSON.
        No explanations.
        No markdown.
        No additional text.


        OUTPUT SCHEMA
        {{
        "Idiom_id": "en_undefined_0001",
        "Idiom": "",
        "Sense_number": 0,
        "Idiomaticity": "idiomatic | literal",
        "Register": [],
        "Region": []
        }} """
    input_prompt = f"""
        "Idiom": {idiom},
        "Idiom_id": {idiom_id},
        "Sense meaning": {definitions},
        "Sense Number": {sense_number},
        "Register": {register},
        "Region": {regions},
        """
    print(input_prompt)
    return {"system_prompt": system_prompt, "input_prompt": input_prompt}


def create_batch_jsonl_file(i):
    output_path = f"idioms_structured/Idiom_meanings/Batch_requests/{language}/"
    os.makedirs(output_path, exist_ok=True)
    offset = i * BATCH_SIZE
    chunk = List_of_idioms[offset:offset + BATCH_SIZE]

    requests = []
    for idiom in chunk:
        idiom_id = idiom[0]
        for sense in idiom[1]:
            custom_id = idiom_id + "_sense_" + str(sense.get("sense_number"))
            prompt = prompt_builder(
                definitions=sense.get("definitions"),
                idiom=sense.get("idiom"),
                sense_number=sense.get("sense_number"),
                regions=sense.get("region"),
                register=sense.get("register"),
                idiom_id=idiom_id
            )
            requests.append({
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4.1",
                    "messages": [
                        {"role": "system", "content": prompt["system_prompt"]},
                        {"role": "user", "content": prompt["input_prompt"]}
                    ],
                     "temperature": 0

                }
            })

    output_file = os.path.join(output_path, f"batch_{i}.jsonl")
    with open(output_file, 'w', encoding='utf-8') as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")

    print(f"[Batch {i}] Wrote {len(requests)} requests")
    return output_file

def submit_and_wait(batch_file_path, i):
    with open(batch_file_path, "rb") as f:
        response = client.files.create(file=f, purpose="batch")
    file_id = response.id
    print(f"[Batch {i}] Uploaded — file_id: {file_id}")

    batch = client.batches.create(
        input_file_id=file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )
    print(f"[Batch {i}] Submitted — batch_id: {batch.id}")

    batch_id = batch.id
    while True:
        batch = client.batches.retrieve(batch_id)
        print(f"[Batch {i}] Status: {batch.status}")
        if batch.status == "completed":
            print(f"[Batch {i}] Done!")
            return batch, batch_id        # ← fix 1: return both on success too
        elif batch.status in ["failed", "expired", "cancelled"]:
            print(f"[Batch {i}] Ended with status: {batch.status}")
            return None, batch_id
        time.sleep(60)


def download_results(batch, i, batch_id):   # ← fix 2: accept batch_id as param
    output = client.files.content(batch.output_file_id)
    results = []
    for line in output.text.splitlines():
        if line.strip():
            result = json.loads(line)
            custom_id = result["custom_id"]
            content = result["response"]["body"]["choices"][0]["message"]["content"]
            try:
                labeled_sense = json.loads(content)
                labeled_sense["custom_id"] = custom_id
                results.append(labeled_sense)
            except json.JSONDecodeError:
                print(f"[Batch {i}] Failed to parse response for {custom_id}")

    output_file = f"idioms_structured/Idiom_meanings/Batch_Results/{language}/labeled_results_batch_{i}.jsonl"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)  # ← add this

    with open("batch_ids.log", "a") as log:         # ← fix 3: separate file handles
        log.write(f"batch_{i}: {batch_id}\n")

    with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"[Batch {i}] Saved {len(results)} senses to {output_file}")


# --- Main loop ---
for i in range(total_batches):
    output_file = f"idioms_structured/Idiom_meanings/Batch_Results/{language}/labeled_results_batch_{i}.jsonl"
    if os.path.exists(output_file):
        print(f"[Batch {i}] Already done, skipping.")
        continue
    print(f"\n--- Starting batch {i + 1} of {total_batches} ---")
    batch_file = create_batch_jsonl_file(i)
    batch, batch_id = submit_and_wait(batch_file, i)
    print(f"Batch {i} had id: {batch_id}")
    if batch:
        download_results(batch, i, batch_id)           # ← pass batch_id through

print("\nAll done!")