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
    # Support both old (bare model) and new (dict) format
    if isinstance(saved, dict):
        model = saved['model']
        feature_cols = saved['feature_cols']
    else:
        model = saved
        feature_cols = ['age', 'mileage_cleaned', 'battery_capacity_cleaned',
                        'effect_cleaned', 'months_to_eu_cleaned']
    
    # Calculate age for the model
    current_year = datetime.now().year
    df['age'] = current_year - df['year_cleaned']

    # Only use columns that exist in both feature_cols and the dataframe
    feature_cols = [c for c in feature_cols if c in df.columns]
    X = df[feature_cols]
    
    print("Predicting Market Value...")
    # Get the algorithm's prediction for every car
    df['predicted_value'] = model.predict(X)
    
    # Calculate the difference: 
    # Positive difference = "Good Deal" (Predicted value is higher than asking price)
    # Negative difference = "Bad Deal" (Asking price is higher than predicted value)
    df['value_difference'] = df['predicted_value'] - df['price_cleaned']
    
    # Sort by the best deals first (largest positive difference)
    df_sorted = df.sort_values(by='value_difference', ascending=False)
    
    # Formatting for output
    df_sorted['predicted_value'] = df_sorted['predicted_value'].round(0).astype(int)
    df_sorted['value_difference'] = df_sorted['value_difference'].round(0).astype(int)
    
    # Save the full results to a new CSV
    output_path = "best_deals.csv"
    columns_to_save = ['title', 'year_cleaned', 'mileage_cleaned', 'months_to_eu_cleaned',
                       'owners_cleaned', 'has_condition_issue',
                       'price_cleaned', 'predicted_value', 'value_difference', 'url']
    # Only save columns that actually exist
    columns_to_save = [c for c in columns_to_save if c in df_sorted.columns]
    df_sorted[columns_to_save].to_csv(output_path, index=False)
    
    print(f"Results saved to {output_path}!\n")
    
    print("Top 5 Best Deals on Finn.no right now:")
    print("-" * 50)
    for index, row in df_sorted.head(5).iterrows():
        months_eu = int(row['months_to_eu_cleaned']) if pd.notnull(row['months_to_eu_cleaned']) else "?"
        owners = int(row['owners_cleaned']) if 'owners_cleaned' in row and pd.notnull(row['owners_cleaned']) else "?"
        issue = "⚠️ Har feil" if row.get('has_condition_issue', 0) == 1 else "OK"
        print(f"[{row['year_cleaned']}] {row['title']} - {row['mileage_cleaned']:,} km (EU om {months_eu} mnd | {owners} eier(e) | {issue})")
        print(f"Prisforespørsel: {row['price_cleaned']:,} kr")
        print(f"Markedsverdi:   {row['predicted_value']:,} kr")
        print(f"Differanse:    +{row['value_difference']:,} kr (rabatt vs. markedsverdi)")
        print(f"Link: {row['url']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
