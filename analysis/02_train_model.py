import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os

def main():
    print("--- Starting Model Training ---")
    data_path = "cleaned_data.csv"
    
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found. Run 01_clean_data.py first.")
        return
        
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} rows for training.")
    
    # Define our Features (X) and Target (y)
    # Features: age (current year - model year) and mileage
    current_year = 2026 # Or dynamically fetch
    df['age'] = current_year - df['year_cleaned']
    
    X = df[['age', 'mileage_cleaned', 'battery_capacity_cleaned', 'effect_cleaned', 'months_to_eu_cleaned']]
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
    print(f"Age: {importances[0]*100:.2f}% impact on price")
    print(f"Mileage: {importances[1]*100:.2f}% impact on price")
    print(f"Battery Capacity: {importances[2]*100:.2f}% impact on price")
    print(f"Horsepower: {importances[3]*100:.2f}% impact on price")
    print(f"Months to EU-control: {importances[4]*100:.2f}% impact on price")
    
    # Save the model to disk so we can use it to find deals later
    model_path = "leaf_model.pkl"
    joblib.dump(model, model_path)
    print(f"\nModel saved successfully to {model_path}!")

if __name__ == "__main__":
    main()
