import pandas as pd
import json

# Carga JSONL
file_path = "idioms_structured/seed_idioms_en_cleaned.jsonl"
records = []

with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            print("⚠ Línea inválida ignorada:", line[:100])

df = pd.DataFrame(records)

# Extrae los últimos 4 dígitos del ID como entero
df["counter"] = df["id"].str.extract(r"_(\d{4})$").astype(int)

# Resta 1 solo si el número es mayor que 1278
mask = df["counter"] >= 7712
df.loc[mask, "counter"] = df.loc[mask, "counter"] - 1

# Reconstruye el ID
# Reconstruye el ID
def build_id(row):
    parts = row["id"].rsplit("_", 1)  # separa todo menos el número
    return f"{parts[0]}_{str(row['counter']).zfill(4)}"

df["id"] = df.apply(build_id, axis=1)

# Elimina la columna temporal antes de guardar
df = df.drop(columns=["counter"])

# Guardar de nuevo como JSONL
with open(file_path, "w", encoding="utf-8") as f:
    for record in df.to_dict(orient="records"):
        f.write(json.dumps(record, ensure_ascii=False) + "\n")