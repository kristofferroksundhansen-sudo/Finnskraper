import pandas as pd
import joblib
import os

def main():
    print("--- Finding the Best Deals ---")
    
    data_path = "cleaned_data.csv"
    model_path = "leaf_model.pkl"
    
    if not os.path.exists(data_path) or not os.path.exists(model_path):
        print("Error: Missing data or model. Run 01 and 02 first.")
        return
        
    df = pd.read_csv(data_path)
    model = joblib.load(model_path)
    
    # Calculate age for the model 
    current_year = 2026
    df['age'] = current_year - df['year_cleaned']
    
    X = df[['age', 'mileage_cleaned', 'battery_capacity_cleaned', 'effect_cleaned', 'months_to_eu_cleaned']]
    
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
    columns_to_save = ['title', 'year_cleaned', 'mileage_cleaned', 'months_to_eu_cleaned', 'price_cleaned', 'predicted_value', 'value_difference', 'url']
    df_sorted[columns_to_save].to_csv(output_path, index=False)
    
    print(f"Results saved to {output_path}!\n")
    
    print("Top 5 Best Deals on Finn.no right now:")
    print("-" * 50)
    for index, row in df_sorted.head(5).iterrows():
        months_eu = int(row['months_to_eu_cleaned']) if pd.notnull(row['months_to_eu_cleaned']) else "?"
        print(f"[{row['year_cleaned']}] {row['title']} - {row['mileage_cleaned']:,} km (EU in {months_eu} months)")
        print(f"Asking Price:  {row['price_cleaned']:,} kr")
        print(f"Market Value:  {row['predicted_value']:,} kr")
        print(f"Difference:   +{row['value_difference']:,} kr (Discount vs Market Value)")
        print(f"Link: {row['url']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
