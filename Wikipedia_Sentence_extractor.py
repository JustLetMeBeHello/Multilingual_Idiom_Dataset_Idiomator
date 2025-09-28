import requests
import re
import json
import time

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"

def fetch_page_text(idiom):
    params = {
        "action": "parse",
        "page": idiom,
        "prop": "text",
        "format": "json",
        "redirects": True
    }
    resp = requests.get(WIKI_API_URL, params=params)
    data = resp.json()
    html = data.get("parse", {}).get("text", {}).get("*", "")
    # Remove HTML tags
    text = re.sub(r'<.*?>', ' ', html)
    return text

def extract_sentences_with_idiom(text, idiom, max_sentences=5):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    matches = [s.strip() for s in sentences if idiom.lower() in s.lower()]
    # Evita duplicados y limita
    unique = list(dict.fromkeys(matches))
    return unique[:max_sentences]

def get_idiom_contexts(idioms, max_per_idiom=5, delay=1.0):
    result = {}
    for idiom in idioms:
        try:
            text = fetch_page_text(idiom)
        except Exception as e:
            print(f"Error fetching '{idiom}': {e}")
            continue
        examples = extract_sentences_with_idiom(text, idiom, max_per_idiom)
        if examples:
            result[idiom] = examples
        time.sleep(delay)  # polite with the API
    return result

if __name__ == "__main__":
    idioms_list = [
        "kick the bucket",
        "spill the beans",
        "break the ice"
    ]
    contexts = get_idiom_contexts(idioms_list, max_per_idiom=5)
    with open("idiom_contexts.json", "w", encoding="utf-8") as f:
        json.dump(contexts, f, ensure_ascii=False, indent=2)
    print("✅ Idiom contexts saved to idiom_contexts.json")
