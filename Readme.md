# Idiomator Multilingual Idiom Dataset 🗣️✨

This dataset provides **multilingual idiomatic examples** (scraped from OPUS subtitles) alongside **idiom lists** (scraped from Wiktionary).  
⚠️ Note: idioms and examples are **not yet aligned** — examples are idiomatic sentences, but not labeled to specific idioms.

---

## 🌍 Languages Covered

**Idiomatic Examples**
- **English**: ~90,000  
- **Spanish**: ~30,000  
- **Hindi**: ~1,000  
- **Telugu**: ~300  
- **Indonesian**: ~481  

**Idiom Lists**
- **English**: ~9,500 idioms  
- **Spanish**: ~3,000 idioms  
- **Hindi**: ~184 idioms  
- **Telugu**: ~103 idioms  
- **Indonesian**: ~47 idioms  

---

## 📊 Dataset Structure

Examples (JSONL):
```json
{
  "id": "en_example_000123",
  "sentence": "She really let the cat out of the bag.",
  "language": "en",
  "source": "OPUS OpenSubtitles"
}
