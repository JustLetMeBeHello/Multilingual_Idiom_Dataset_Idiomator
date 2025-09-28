import pandas as pd

# Carga JSONL
df = pd.read_json("idioms_structured/seed_idioms_en_cleaned.jsonl", lines=True)

# Filtra solo inglés
df_en = df[df["language"] == "en"].copy()

# Extrae el número final del id
df_en["counter"] = df_en["id"].str.extract(r"_(\d+)$").astype(int)

# Ordena por el número (no importa dialecto)
df_en = df_en.sort_values("counter")

# Calcula diferencia fila a fila
df_en["diff"] = df_en["counter"].diff()

# Detecta problemas: diferencia != 1
problems = df_en[df_en["diff"] != 1]

if problems.empty:
    print("✅ Todos los IDs en inglés suben de 1 en 1 globalmente.")
else:
    print("⚠️ Problemas encontrados:")
    print(problems[["id", "dialect", "counter", "diff"]])
