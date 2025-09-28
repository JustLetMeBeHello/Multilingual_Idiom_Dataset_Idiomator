from supabase import create_client
import json
from pathlib import Path
import os

# Supabase credentialsSUPABASE_URL = os.getenv("SUPABASE_URL").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
database_service_Key = os.getenv("database_service_Key")
TABLE = os.getenv("TABLE_NAME", "idioms")
SUPABASE_URL = os.getenv("SUPABASE_URL").rstrip("/")
key = database_service_Key
url = SUPABASE_URL


supabase = create_client(url, key)

examples_file = Path("idioms_structured/Idiom_sentences/English_all_idiom_examples.jsonl")
batch_size = 500
batch = []

with examples_file.open("r", encoding="utf-8") as f:
    for line_count, line in enumerate(f, start=1):
        data = json.loads(line)

        # For now, only take first English translation
        en_text = data["translations"][0]["text"] if data.get("translations") else None


        batch.append({
            "idiom_id": data["id"],
            "source_language": data["source_language"],
            "source_text": data["source_text"],
            "translations": data["translations"],  # array of objects
            "dialect": data.get("dialect"),
            "url": data.get("url"),
            "source": data.get("source"),
        })

        if len(batch) >= batch_size:
            supabase.table("examples").insert(batch).execute()
            batch = []
            print(f"Inserted {line_count:,} examples ✅")

# Insert any remaining
if batch:
    supabase.table("examples").insert(batch).execute()
    print(f"Inserted {line_count:,} examples ✅")

print("All examples uploaded successfully!")
