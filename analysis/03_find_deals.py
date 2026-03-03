import pandas as pd
import joblib
import os
from datetime import datetime

def main():
    print("--- Finding the Best Deals ---")
    
    data_path = "cleaned_data.csv"
    model_path = "leaf_model.pkl"
    
    if not os.path.exists(data_path) or not os.path.exists(model_path):
        print("Error: Missing data or model. Run 01 and 02 first.")
        return
        
    df = pd.read_csv(data_path)
    saved = joblib.load(model_path)

    # Expected format going forward is always the dict with metadata
    if not isinstance(saved, dict):
        print("Error: Model format is outdated. Please re-run 02_train_model.py.")
        return
        
    model = saved['model']
    feature_cols = saved['feature_cols']

    # Calculate age for the model
    current_year = datetime.now().year
    df['age'] = current_year - df['year_cleaned']

    # Annonsealder (Fase 3.2)
    if 'first_seen_date' in df.columns:
        first_seen = pd.to_datetime(df['first_seen_date'], errors='coerce')
        df['days_listed'] = (pd.Timestamp.now() - first_seen).dt.days
        df['days_listed'] = df['days_listed'].fillna(0).clip(lower=0)
    else:
        df['days_listed'] = 0

    # One-hot encode kategoriske variable på nytt
    if 'trim_level' in df.columns:
        df = pd.concat([df, pd.get_dummies(df['trim_level'], prefix='trim', dtype=int)], axis=1)
    if 'region' in df.columns:
        df = pd.concat([df, pd.get_dummies(df['region'], prefix='region', dtype=int)], axis=1)

    # Reindex for å sikre nøyaktig samme kolonnestruktur som modellen forventer (fyll missing med 0)
    X = df.reindex(columns=feature_cols, fill_value=0)
    
    print("Predicting Market Value...")
    df['predicted_value'] = model.predict(X)
    
    # Calculate the difference
    df['value_difference'] = df['predicted_value'] - df['price_cleaned']
    
    # Sort by the best deals first
    df_sorted = df.sort_values(by='value_difference', ascending=False)
    
    # Formatting for output
    df_sorted['predicted_value'] = df_sorted['predicted_value'].round(0).astype(int)
    df_sorted['value_difference'] = df_sorted['value_difference'].round(0).astype(int)
    
    # Save the full results to a new CSV
    output_path = "best_deals.csv"
    columns_to_save = ['title', 'year_cleaned', 'mileage_cleaned', 'range_km_cleaned',
                       'months_to_eu_cleaned', 'owners_cleaned',
                       'has_condition_issue', 'has_warranty', 'trim_level', 'region',
                       'is_dealer', 'dealer_name', 'days_listed',
                       'price_cleaned', 'predicted_value', 'value_difference', 'url']
    columns_to_save = [c for c in columns_to_save if c in df_sorted.columns]
    df_sorted[columns_to_save].to_csv(output_path, index=False)
    
    print(f"Results saved to {output_path}!\n")
    
    print("Top 5 Best Deals on Finn.no right now:")
    print("-" * 60)
    for index, row in df_sorted.head(5).iterrows():
        months_eu = int(row['months_to_eu_cleaned']) if pd.notnull(row['months_to_eu_cleaned']) else "?"
        trim = row.get('trim_level', '?')
        region = row.get('region', '?')
        seller_type = f"Forhandler ({row.get('dealer_name', '')})" if row.get('is_dealer', 0) == 1 else 'Privat'
        warn_str = " ⚠️FEIL!" if row.get('has_condition_issue', 0) == 1 else ""
        
        print(f"[{row['year_cleaned']}] {row['title']} ({trim}) - {row['mileage_cleaned']:,.0f} km{warn_str}")
        print(f"  {region} | {seller_type} | EU om {months_eu} mnd")
        print(f"  Prisforslag:  {row['price_cleaned']:,.0f} kr")
        print(f"  Markedsverdi: {row['predicted_value']:,} kr")
        print(f"  Rabatt:      +{row['value_difference']:,} kr")
        print(f"  Link: {row['url']}")
        print("-" * 60)

if __name__ == "__main__":
    main()
