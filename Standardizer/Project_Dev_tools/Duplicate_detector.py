import json
import regex

def Structure_Senses(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
        for line in data:
            appearances = 0
            if 
                appearances + 1
            if appearances >= 2:
                print(line)


if __name__ == "__main__":
    name = "English"
    Structure_Senses(f"idioms_structured/Meanings/{name}/Raw_Meanings_Ordered_Flattened.jsonl")