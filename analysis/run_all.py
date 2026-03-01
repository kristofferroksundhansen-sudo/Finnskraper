"""
run_all.py – Kjør hele analyse-pipelinen i riktig rekkefølge.

Bruk:
    cd analysis
    python run_all.py
"""

import subprocess
import sys
import os

SCRIPTS = [
    ("01_clean_data.py",   "Renser og flater ut rådata fra Apify"),
    ("02_train_model.py",  "Trener RandomForest-modellen"),
    ("03_find_deals.py",   "Finner de beste kuppene"),
    ("04_descriptive_stats.py", "Lager deskriptiv statistikk"),
]

def run_script(script, description):
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"  → python {script}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, script],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    if result.returncode != 0:
        print(f"\n[FEIL] {script} feilet med kode {result.returncode}. Avbryter.")
        sys.exit(result.returncode)

if __name__ == "__main__":
    print("=== Finn-scraper analyse-pipeline ===")
    for script, desc in SCRIPTS:
        run_script(script, desc)
    print("\n✅ Pipeline fullført! Sjekk best_deals.csv for resultatene.")
