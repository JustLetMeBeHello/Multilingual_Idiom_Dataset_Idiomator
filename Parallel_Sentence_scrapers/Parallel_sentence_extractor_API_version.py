#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
from collections import defaultdict
from time import sleep

# --------- Config ----------
SEED_PATH = "idioms_structured/seed_idioms_es_cleaned_copy.jsonl"
OUT_PATH  = "idioms_with_examples_es_os.jsonl"
MAX_EXAMPLES = 5
API_KEY = "tpI8TOdWNmOSn7jRfVR9t9W1veS66kcF"  # reemplaza con tu API key
# ---------------------------

HEADERS = {"Api-Key": API_KEY, "User-Agent": "Idiomatorv1"}
SEARCH_URL = "https://api.opensubtitles.com/api/v1/subtitles"
DL_URL     = "https://api.opensubtitles.com/api/v1/download"
import time, random

def safe_request(func, *args, retries=3, **kwargs):
    for i in range(retries):
        try:
            resp = func(*args, **kwargs)
            if resp.status_code == 200:
                return resp
            else:
                print(f"Status {resp.status_code}, intento {i+1}")
        except Exception as e:
            print(f"Error {e}, intento {i+1}")
        time.sleep(2**i + random.random())  # backoff exponencial
    return None

def download_and_extract(file_id, idiom):
    """Descarga el srt y devuelve líneas con el idiom"""
    try:
        r = resp = safe_request(requests.post, DL_URL, headers=HEADERS, json={"file_id": file_id})

        if r.status_code != 200:
            print(f"Error {r.status_code} al pedir descarga file_id={file_id}")
            return []
        link = r.json().get("link")
        if not link:
            return []

        # bajar subtítulo
        srt = requests.get(link, timeout=30).text

        # extraer frases con el idiom
        matches = []
        for line in srt.splitlines():
            if idiom.lower() in line.lower():
                matches.append(line.strip())
        return matches
    except Exception as e:
        print(f"Error en download_and_extract: {e}")
        return []


# Cargar idioms
idioms = []
with open(SEED_PATH, "r", encoding="utf-8") as f:
    for line in f:
        try:
            idiom = json.loads(line)["idiom"].strip()
            if idiom:
                idioms.append(idiom)
        except:
            continue

print(f"Cargados {len(idioms)} modismos del seed.")

examples = defaultdict(list)

for idiom in idioms:
    params = {
        "languages": "es",
        "query": idiom,
        "order_by": "download_count",
        "order_direction": "desc",
        "limit": 10
    }
    try:
        resp = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=10)
        if resp.status_code != 200:
            print(f"Error {resp.status_code} buscando idiom '{idiom}'")
            continue

        data = resp.json().get("data", [])
        for item in data:
            if len(examples[idiom]) >= MAX_EXAMPLES:
                break

            file_id = item["attributes"].get("files", [{}])[0].get("file_id")
            if not file_id:
                continue

            lines = download_and_extract(file_id, idiom)
            for line in lines:
                if len(examples[idiom]) < MAX_EXAMPLES:
                    examples[idiom].append({"es": line, "en": ""})

        print(f"Ejemplos para '{idiom}': {len(examples[idiom])}")

    except Exception as e:
        print(f"Error buscando idiom '{idiom}': {e}")

    sleep(1)  # respeta la API
# Guardar JSONL
with open(OUT_PATH, "w", encoding="utf-8") as out:
    for idiom in idioms:
        out.write(json.dumps({
            "idiom": idiom,
            "examples": examples.get(idiom, [])
        }, ensure_ascii=False) + "\n")

print(f"Guardado en {OUT_PATH}")
