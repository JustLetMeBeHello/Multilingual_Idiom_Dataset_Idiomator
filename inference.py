import spacy
import json
from pathlib import Path

class IdiomMatcher:
    def __init__(self, idiom_file: str):
        self.idiom_file = idiom_file
        self.models = {
            "en": spacy.load("en_core_web_sm"),
            "es": spacy.load("es_core_news_sm")
        }
        self.idioms_by_lang = {
            "en": [],
            "es": []
        }
        self._load_idioms()

    def _lemmatize(self, text: str, lang: str) -> str:
        doc = self.models[lang](text)
        return " ".join([token.lemma_ for token in doc])

    def _load_idioms(self):
        path = Path(self.idiom_file)
        if not path.exists():
            raise FileNotFoundError(f"Idiom file not found: {self.idiom_file}")

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                lang = entry.get("language")
                if lang not in ["en", "es"]:
                    continue
                idiom_text = entry.get("idiom", "").strip()
                if not idiom_text:
                    continue
                entry["lemmatized"] = self._lemmatize(idiom_text, lang)
                self.idioms_by_lang[lang].append(entry)

    def match(self, sentence: str, lang: str):
        if lang not in self.models:
            raise ValueError(f"Unsupported language: {lang}")
        sent_lemma = self._lemmatize(sentence, lang)
        matches = []
        for idiom in self.idioms_by_lang[lang]:
            if idiom["lemmatized"] in sent_lemma:
                matches.append(idiom)
        return matches
