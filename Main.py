from inference import IdiomMatcher

matcher = IdiomMatcher("idioms_structured/seed_idioms_es_cleaned.jsonl")
text = "Está viviendo por encima de sus posibilidades"
matches = matcher.match(text, lang="es")

for m in matches:
    print(f"- {m['idiom']} ({m['dialect']}) → {m['gloss']}")