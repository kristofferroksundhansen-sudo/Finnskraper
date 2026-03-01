import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os
from datetime import datetime

def main():
    print("--- Starting Model Training ---")
    data_path = "cleaned_data.csv"
    
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found. Run 01_clean_data.py first.")
        return
        
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} rows for training.")
    
    # Define our Features (X) and Target (y)
    current_year = datetime.now().year
    df['age'] = current_year - df['year_cleaned']

    feature_cols = ['age', 'mileage_cleaned', 'battery_capacity_cleaned',
                    'effect_cleaned', 'months_to_eu_cleaned',
                    'owners_cleaned', 'has_condition_issue']
    # Only use features that exist in the data (backwards compatibility)
    feature_cols = [c for c in feature_cols if c in df.columns]
    X = df[feature_cols]
    y = df['price_cleaned']
    
    # Split into training and testing sets (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Initialize the Random Forest Regressor
    # n_estimators=100 means it builds 100 decision trees and averages them
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    
    print("Training model...")
    model.fit(X_train, y_train)
    
    # Evaluate the model
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    
    print("\n--- Model Evaluation ---")
    print(f"Mean Absolute Error: {mae:.2f} kr")
    print(f"R-squared Score: {r2:.4f} (1.0 is perfect prediction)")
    
    # Feature Importance
    importances = model.feature_importances_
    print("\n--- Feature Importance ---")
    for feat, imp in zip(feature_cols, importances):
        print(f"{feat}: {imp*100:.2f}% impact on price")
    
    # Save model AND feature list so 03_find_deals.py uses the same columns
    model_path = "leaf_model.pkl"
    joblib.dump({'model': model, 'feature_cols': feature_cols}, model_path)
    print(f"\nModel saved successfully to {model_path}!")

if __name__ == "__main__":
    main()
