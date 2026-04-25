"""
clean_all_languages.py

Cleans Final_{lang}.jsonl for all languages and produces per-language:
  - Final_{lang}_CLEAN.jsonl         → fixed records (issues 2, 4, 6 resolved)
  - Final_{lang}_CORRUPTED.jsonl     → truncated-definition senses for repair
  - Final_{lang}_NULL_EXAMPLES.jsonl → senses with null examples for re-attachment
  - clean_report_{lang}.txt          → per-language summary

And a combined:
  - clean_report_ALL.txt             → summary across all languages

Fixes applied automatically:
  [2] Duplicate sense numbers with different content → renumbered sequentially
  [4] Non-sequential sense numbers → renumbered after dedup fix
  [6] idiom field is int not string → cast to str

Flagged for manual repair (written to separate files, removed from CLEAN output):
  [1] Definitions truncated to single character → CORRUPTED file
  [3] examples field is null → NULL_EXAMPLES file

Does NOT modify meaning_id duplicates (issue 5) — these require upstream investigation.

Usage:
  python clean_all_languages.py

  Expects input files at:
    {BASE_INPUT_DIR}/{lang}/Final_{lang}.jsonl

  Writes output files to:
    {BASE_OUTPUT_DIR}/{lang}/
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# ── Config — update these paths to match your project structure ───────────────

LANGUAGES = ["English", "Spanish", "Indonesian", "Telugu", "Hindi"]

BASE_INPUT_DIR  = "idioms_structured/Final_Seed_Dataset/Cleaned"
BASE_OUTPUT_DIR = "idioms_structured/Final_Seed_Dataset/Cleaned2Test"

# ── Core cleaning function ────────────────────────────────────────────────────

def clean_language(lang: str) -> dict:
    """
    Cleans Final_{lang}.jsonl and writes output files.
    Returns a stats dict for the combined report.
    """
    input_path   = Path(BASE_INPUT_DIR) / lang / f"Final_{lang}_CLEAN.jsonl"
    output_dir   = Path(BASE_OUTPUT_DIR) / lang
    clean_path   = output_dir / f"Final_{lang}_CLEAN.jsonl"
    corrupt_path = output_dir / f"Final_{lang}_CORRUPTED.jsonl"
    null_ex_path = output_dir / f"Final_{lang}_NULL_EXAMPLES.jsonl"
    report_path  = output_dir / f"clean_report_{lang}.txt"

    print(f"\n{'═' * 65}")
    print(f"  Language: {lang}")
    print(f"{'═' * 65}")

    if not input_path.exists():
        print(f"  [SKIP] Input file not found: {input_path}")
        return {"lang": lang, "skipped": True}

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Load ──────────────────────────────────────────────────────────────────

    raw_records = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                raw_records.append(json.loads(line))

    print(f"  Loaded {len(raw_records):,} records")

    # ── Counters ──────────────────────────────────────────────────────────────

    count_corrupted       = 0
    count_null_examples   = 0
    count_int_idiom_fixed = 0
    count_dup_renumbered  = 0
    count_gap_renumbered  = 0
    corrupted_records     = []
    null_example_records  = []

    # ── Fix 6: cast int idiom → string ────────────────────────────────────────

    for r in raw_records:
        if isinstance(r.get("idiom"), int):
            r["idiom"] = str(r["idiom"])
            count_int_idiom_fixed += 1

    # ── Fix 1: separate corrupted records (single-char definition) ────────────

    clean_records = []
    for r in raw_records:
        defs = r.get("definitions", [])
        is_corrupted = (
            isinstance(defs, list)
            and len(defs) == 1
            and isinstance(defs[0], str)
            and len(defs[0]) == 1
        )
        if is_corrupted:
            corrupted_records.append(r)
            count_corrupted += 1
        else:
            clean_records.append(r)

    print(f"  Corrupted (single-char def): {count_corrupted:,}")
    print(f"  Clean candidates:            {len(clean_records):,}")

    # ── Flag 3: null examples (kept in clean output, also written separately) ──

    for r in clean_records:
        if r.get("examples") is None:
            null_example_records.append(r)
            count_null_examples += 1

    print(f"  Null examples:               {count_null_examples:,}")

    # ── Fix 2 + 4: renumber duplicate and non-sequential sense numbers ─────────

    idiom_groups = defaultdict(list)
# Add idiom_id if missing
    for r in clean_records:
        if "idiom_id" not in r or not r["idiom_id"]:
            r["idiom_id"] = f"hindi_{r['idiom']}"
        idiom_groups[r["idiom_id"]].append(r)
        
    final_clean = []
    for idiom_id, senses in idiom_groups.items():
        senses.sort(key=lambda s: (s.get("sense_number") or 0))

        sns      = [s.get("sense_number") for s in senses]
        has_dups = len(sns) != len(set(sns))
        has_gaps = sorted(sns) != list(range(1, len(sns) + 1))

        if has_dups:
            count_dup_renumbered += 1

        if has_dups or has_gaps:
            for new_sn, sense in enumerate(senses, start=1):
                sense["sense_number"] = new_sn
            if has_gaps and not has_dups:
                count_gap_renumbered += 1

        final_clean.extend(senses)

    print(f"  Dup sense idioms renumbered: {count_dup_renumbered:,}")
    print(f"  Gap-only idioms renumbered:  {count_gap_renumbered:,}")

    # ── Write outputs ──────────────────────────────────────────────────────────

    with open(clean_path, "w", encoding="utf-8") as f:
        for r in final_clean:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(corrupt_path, "w", encoding="utf-8") as f:
        for r in corrupted_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(null_ex_path, "w", encoding="utf-8") as f:
        for r in null_example_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"  ✓ CLEAN          → {clean_path}")
    print(f"  ✓ CORRUPTED      → {corrupt_path}")
    print(f"  ✓ NULL_EXAMPLES  → {null_ex_path}")

    # ── Verify ────────────────────────────────────────────────────────────────

    verify_records = []
    with open(clean_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                verify_records.append(json.loads(line))

    verify_groups = defaultdict(list)
    for r in verify_records:
        verify_groups[r["idiom_id"]].append(r["sense_number"])

    rem_corrupted  = [r for r in verify_records if r.get("definitions") and len(r["definitions"]) == 1 and len(r["definitions"][0]) == 1]
    rem_int_idiom  = [r for r in verify_records if isinstance(r.get("idiom"), int)]
    rem_dups       = [(iid, sns) for iid, sns in verify_groups.items() if len(sns) != len(set(sns))]
    rem_gaps       = [(iid, sorted(sns)) for iid, sns in verify_groups.items() if sorted(sns) != list(range(1, len(sns)+1))]
    rem_null_ex    = [r for r in verify_records if r.get("examples") is None]

    # ── Per-language report ────────────────────────────────────────────────────

    report_lines = [
        "=" * 65,
        f"  CLEANING REPORT — {lang.upper()}",
        "=" * 65,
        "",
        f"  Input file      : {input_path}",
        f"  Input records   : {len(raw_records):,}",
        "",
        "── FIXES APPLIED ────────────────────────────────────────────",
        "",
        f"  [6] int → str cast on 'idiom' field     : {count_int_idiom_fixed:,} senses fixed",
        f"  [2] Duplicate sense numbers renumbered  : {count_dup_renumbered:,} idioms",
        f"  [4] Gap-only sense numbers renumbered   : {count_gap_renumbered:,} idioms",
        "",
        "── FLAGGED FOR MANUAL REPAIR ────────────────────────────────",
        "",
        f"  [1] Corrupted (single-char definition)  : {count_corrupted:,} senses → {corrupt_path.name}",
        f"  [3] Null examples                       : {count_null_examples:,} senses → {null_ex_path.name}",
        "",
        "── NOT MODIFIED ─────────────────────────────────────────────",
        "",
        "  [5] Duplicate meaning_id UUIDs: require upstream investigation.",
        "      Do not use meaning_id as a unique key until resolved.",
        "",
        "── OUTPUT FILES ─────────────────────────────────────────────",
        "",
        f"  {clean_path.name:<40}: {len(final_clean):,} senses",
        f"  {corrupt_path.name:<40}: {len(corrupted_records):,} senses",
        f"  {null_ex_path.name:<40}: {len(null_example_records):,} senses",
        "",
        "── VERIFICATION ─────────────────────────────────────────────",
        "",
        f"  Remaining single-char defs      : {len(rem_corrupted)}",
        f"  Remaining int idiom fields      : {len(rem_int_idiom)}",
        f"  Remaining dup sense numbers     : {len(rem_dups)}",
        f"  Remaining gap sense numbers     : {len(rem_gaps)}",
        f"  Remaining null examples         : {len(rem_null_ex)}",
        "",
        "=" * 65,
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    print(f"  ✓ Report         → {report_path}")

    return {
        "lang":                  lang,
        "skipped":               False,
        "input_records":         len(raw_records),
        "clean_senses":          len(final_clean),
        "corrupted":             count_corrupted,
        "null_examples":         count_null_examples,
        "int_idiom_fixed":       count_int_idiom_fixed,
        "dup_renumbered":        count_dup_renumbered,
        "gap_renumbered":        count_gap_renumbered,
        "rem_corrupted":         len(rem_corrupted),
        "rem_int_idiom":         len(rem_int_idiom),
        "rem_dups":              len(rem_dups),
        "rem_gaps":              len(rem_gaps),
        "rem_null_ex":           len(rem_null_ex),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_stats = []
    for lang in LANGUAGES:
        stats = clean_language(lang)
        all_stats.append(stats)

    # ── Combined report ───────────────────────────────────────────────────────

    combined_report_path = Path(BASE_OUTPUT_DIR) / "clean_report_ALL.txt"
    Path(BASE_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    col = 14  # language column width
    w   = 10  # number column width

    header = (
        f"\n{'═' * 65}\n"
        f"  COMBINED CLEANING REPORT — ALL LANGUAGES\n"
        f"{'═' * 65}\n\n"
        f"  {'Language':<{col}} {'Input':>{w}} {'Clean':>{w}} {'Corrupt':>{w}} {'NullEx':>{w}} {'DupFix':>{w}} {'GapFix':>{w}}\n"
        f"  {'-'*col} {'-'*w} {'-'*w} {'-'*w} {'-'*w} {'-'*w} {'-'*w}"
    )

    rows = []
    totals = defaultdict(int)
    for s in all_stats:
        if s.get("skipped"):
            rows.append(f"  {s['lang']:<{col}} {'SKIPPED'}")
            continue
        rows.append(
            f"  {s['lang']:<{col}}"
            f" {s['input_records']:>{w},}"
            f" {s['clean_senses']:>{w},}"
            f" {s['corrupted']:>{w},}"
            f" {s['null_examples']:>{w},}"
            f" {s['dup_renumbered']:>{w},}"
            f" {s['gap_renumbered']:>{w},}"
        )
        for key in ["input_records","clean_senses","corrupted","null_examples","dup_renumbered","gap_renumbered"]:
            totals[key] += s[key]

    total_row = (
        f"\n  {'TOTAL':<{col}}"
        f" {totals['input_records']:>{w},}"
        f" {totals['clean_senses']:>{w},}"
        f" {totals['corrupted']:>{w},}"
        f" {totals['null_examples']:>{w},}"
        f" {totals['dup_renumbered']:>{w},}"
        f" {totals['gap_renumbered']:>{w},}"
    )

    footer = (
        f"\n\n  Column guide:\n"
        f"    Input   = total input senses\n"
        f"    Clean   = senses in CLEAN output\n"
        f"    Corrupt = senses flagged (single-char definition)\n"
        f"    NullEx  = senses with null examples (kept in clean, also in NULL_EXAMPLES file)\n"
        f"    DupFix  = idioms where duplicate sense numbers were renumbered\n"
        f"    GapFix  = idioms where gap-only sense numbers were renumbered\n"
        f"\n  NOTE: Duplicate meaning_id UUIDs not modified — upstream fix required.\n"
        f"\n{'═' * 65}\n"
    )

    combined = header + "\n" + "\n".join(rows) + total_row + footer

    with open(combined_report_path, "w", encoding="utf-8") as f:
        f.write(combined)

    print(f"\n{'═' * 65}")
    print(combined)
    print(f"  ✓ Combined report → {combined_report_path}")
    print(f"{'═' * 65}\n")


if __name__ == "__main__":
    main()