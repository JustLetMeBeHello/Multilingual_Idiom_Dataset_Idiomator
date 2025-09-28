#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import stanza
stanza.download("te")

import xml.etree.ElementTree as ET
import unicodedata as ud
import json
from collections import defaultdict

# --------- Config ----------
SEED_PATH = "idioms_structured/seed_idioms_te_cleaned.jsonl"
TMX_PATH  = "en-te.tmx"
OUT_PATH  = "idioms_with_examples_te.jsonl"
MAX_EXAMPLES = 3
# ---------------------------

def nfc(s: str) -> str:
    return ud.normalize("NFC", (s or "").strip())

def seg_text(seg_el) -> str:
    # Toma TODO el texto (incluye hijos)
    return nfc("".join(seg_el.itertext()))

def is_word_char(ch: str) -> bool:
    # Considera letras, marcas (matras), números como "parte de palabra".
    if not ch:
        return False
    cat = ud.category(ch)
    return cat[0] in ("L", "M", "N")  # Letter, Mark, Number

def is_boundary(text: str, start: int, end: int) -> bool:
    # Asegura que el idiom esté separado por no-palabras a ambos lados
    left_ok  = (start == 0) or not is_word_char(text[start - 1])
    right_ok = (end   == len(text)) or not is_word_char(text[end])
    return left_ok and right_ok

# Lee idioms
idioms = []
with open(SEED_PATH, "r", encoding="utf-8") as f:
    for line in f:
        try:
            idiom = nfc(json.loads(line)["idiom"])
        except Exception:
            continue
        if idiom:
            idioms.append(idiom)

print(f"Cargados {len(idioms)} modismos del seed.")

# Construye automáton Aho–Corasick
try:
    import ahocorasick
except ImportError as e:
    raise SystemExit(
        "Falta pyahocorasick. Instálalo primero:\n"
        "  pip install pyahocorasick"
    )

A = ahocorasick.Automaton()
for idx, idiom in enumerate(idioms):
    # Guardamos el índice para acceso rápido
    A.add_word(idiom, (idx, idiom))
A.make_automaton()

# Estructura para ejemplos
examples = defaultdict(list)
filled = 0  # cuántos idioms ya alcanzaron MAX_EXAMPLES

# Para saber cuándo dejar de buscar
remaining_needed = {i: MAX_EXAMPLES for i in idioms}

# Namespaces posibles para xml:lang
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# Parseo en streaming
tu_count = 0
for event, elem in ET.iterparse(TMX_PATH, events=("end",)):
    if not elem.tag.endswith("tu"):
        continue

    te_text, en_text = "", ""
    # Obtén pares en/en-hi
    for tuv in elem.findall("./tuv"):
        lang = tuv.attrib.get(XML_LANG) or tuv.attrib.get("lang") or ""
        seg = tuv.find("seg")
        if seg is None:
            continue
        s = seg_text(seg)
        if lang.lower().startswith("te"):
            te_text = s
        elif lang.lower().startswith("en"):
            en_text = s

    if te_text:
        # Busca TODOS los matches en hindi
        # Aho–Corasick devuelve (end_index, payload). Calculamos inicio.
        matched_idxs = set()  # evita duplicados del mismo idiom en el mismo TU
        for end_pos, (idx, idiom) in A.iter(te_text):
            if remaining_needed.get(idiom, 0) <= 0:
                continue  # ya tenemos MAX_EXAMPLES de ese idiom
            start_pos = end_pos - len(idiom) + 1
            # Verifica límites de palabra Unicode
            if not is_boundary(te_text, start_pos, end_pos + 1):
                continue
            matched_idxs.add(idx)

        # Guarda hasta MAX_EXAMPLES por idiom
        for idx in matched_idxs:
            idiom = idioms[idx]
            if remaining_needed[idiom] > 0:
                examples[idiom].append({"te": te_text, "en": en_text})
                remaining_needed[idiom] -= 1
                if remaining_needed[idiom] == 0:
                    filled += 1

    # Limpia el nodo para liberar memoria
    elem.clear()
    tu_count += 1
    if tu_count % 100000 == 0:
        print(f"Procesados {tu_count} TUs… Idioms completos: {filled}")

    # Si ya completaste todos los idioms posibles, puedes cortar temprano
    # (comentado por si quieres barrer todo el corpus igualmente)
    # if filled == len(idioms):
    #     print("Todos los idioms alcanzaron el máximo de ejemplos. Cortando.")
    #     break

print(f"Procesados {tu_count} TUs en total.")
print(f"Idioms con al menos 1 ejemplo: {sum(1 for k in examples if examples[k])}")

# Escribe salida: 1 línea por idiom (aunque no tenga ejemplos para mantener paridad)
with open(OUT_PATH, "w", encoding="utf-8") as out:
    for idiom in idioms:
        out.write(json.dumps({
            "idiom": idiom,
            "examples": examples.get(idiom, [])
        }, ensure_ascii=False) + "\n")

print(f"Escrito: {OUT_PATH}")
