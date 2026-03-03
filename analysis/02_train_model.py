import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.inspection import permutation_importance
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
import shap
import joblib
import os
import warnings
from datetime import datetime

warnings.filterwarnings('ignore', category=UserWarning)

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

    # --- Fase 3.2: Annonsealder (DOM - Days on Market) ---
    if 'first_seen_date' in df.columns:
        first_seen = pd.to_datetime(df['first_seen_date'], errors='coerce')
        if 'last_seen_date' in df.columns:
            last_seen = pd.to_datetime(df['last_seen_date'], errors='coerce')
            # Fyll inn manglende last_seen med dagens dato
            last_seen = last_seen.fillna(pd.Timestamp.now())
        else:
            last_seen = pd.Timestamp.now()
            
        df['days_listed'] = (last_seen - first_seen).dt.days
        df['days_listed'] = df['days_listed'].fillna(0).clip(lower=0)
    else:
        df['days_listed'] = 0

    # --- One-hot encode trim_level og region ---
    trim_dummies = pd.DataFrame()
    region_dummies = pd.DataFrame()

    if 'trim_level' in df.columns:
        trim_dummies = pd.get_dummies(df['trim_level'], prefix='trim', dtype=int)
        if 'trim_Ukjent' in trim_dummies.columns:
            trim_dummies = trim_dummies.drop(columns=['trim_Ukjent'])
        df = pd.concat([df, trim_dummies], axis=1)

    if 'region' in df.columns:
        region_dummies = pd.get_dummies(df['region'], prefix='region', dtype=int)
        if 'region_Annet' in region_dummies.columns:
            region_dummies = region_dummies.drop(columns=['region_Annet'])
        df = pd.concat([df, region_dummies], axis=1)

    # Base numeric features (inkl. nye Fase 3 features)
    numeric_features = ['age', 'mileage_cleaned', 'battery_capacity_cleaned',
                        'effect_cleaned', 'range_km_cleaned',
                        'months_to_eu_cleaned', 'owners_cleaned',
                        'has_condition_issue', 'has_warranty',
                        'is_dealer', 'days_listed']
    numeric_features = [c for c in numeric_features if c in df.columns]

    trim_cols = list(trim_dummies.columns)
    region_cols = list(region_dummies.columns)
    feature_cols = numeric_features + trim_cols + region_cols

    X = df[feature_cols]
    y = df['price_cleaned']

    # =====================================================================
    # MODEL COMPARISON: RF vs XGBoost vs LightGBM
    # =====================================================================
    print("\n" + "="*60)
    print("  MODELLSAMMENLIGNING (5-fold CV)")
    print("="*60)

    models = {
        'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42),
        'XGBoost': XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.1,
                                random_state=42, verbosity=0),
        'LightGBM': LGBMRegressor(n_estimators=200, max_depth=6, learning_rate=0.1,
                                   random_state=42, verbose=-1),
    }

    best_model_name = None
    best_mae = float('inf')
    cv_results = {}

    for name, model in models.items():
        cv_r2 = cross_val_score(model, X, y, cv=5, scoring='r2')
        cv_mae = cross_val_score(model, X, y, cv=5, scoring='neg_mean_absolute_error')
        avg_r2 = cv_r2.mean()
        avg_mae = -cv_mae.mean()
        cv_results[name] = {'r2': avg_r2, 'r2_std': cv_r2.std(),
                            'mae': avg_mae, 'mae_std': cv_mae.std()}
        marker = ""
        if avg_mae < best_mae:
            best_mae = avg_mae
            best_model_name = name
            marker = " <-- best"
        print(f"  {name:15s}  R2={avg_r2:.4f}+/-{cv_r2.std():.4f}  MAE={avg_mae:,.0f}+/-{cv_mae.std():,.0f} kr{marker}")

    # =====================================================================
    # HYPERPARAMETER TUNING for best model
    # =====================================================================
    print(f"\n--- Hyperparameter-tuning ({best_model_name}) ---")

    if best_model_name == 'XGBoost':
        param_dist = {
            'n_estimators': [100, 200, 300, 500],
            'max_depth': [3, 5, 6, 8, 10],
            'learning_rate': [0.01, 0.05, 0.1, 0.15],
            'min_child_weight': [1, 3, 5],
            'subsample': [0.7, 0.8, 0.9, 1.0],
            'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
        }
        base_model = XGBRegressor(random_state=42, verbosity=0)
    elif best_model_name == 'LightGBM':
        param_dist = {
            'n_estimators': [100, 200, 300, 500],
            'max_depth': [3, 5, 6, 8, -1],
            'learning_rate': [0.01, 0.05, 0.1, 0.15],
            'num_leaves': [15, 31, 50, 80],
            'min_child_samples': [5, 10, 20],
            'subsample': [0.7, 0.8, 0.9, 1.0],
        }
        base_model = LGBMRegressor(random_state=42, verbose=-1)
    else:
        param_dist = {
            'n_estimators': [50, 100, 200, 300, 500],
            'max_depth': [5, 10, 15, 20, 30, None],
            'min_samples_leaf': [1, 2, 5, 10],
            'min_samples_split': [2, 5, 10],
            'max_features': ['sqrt', 'log2', None],
        }
        base_model = RandomForestRegressor(random_state=42)

    search = RandomizedSearchCV(
        base_model, param_dist, n_iter=40, cv=5,
        scoring='neg_mean_absolute_error', random_state=42,
        n_jobs=-1, verbose=0
    )
    search.fit(X, y)
    tuned_model = search.best_estimator_
    tuned_mae = -search.best_score_

    print(f"  Beste parametere: {search.best_params_}")
    print(f"  Tunet MAE (CV): {tuned_mae:,.0f} kr (vs. default: {best_mae:,.0f} kr)")
    improvement = best_mae - tuned_mae
    print(f"  Forbedring: {improvement:,.0f} kr ({improvement/best_mae*100:.1f}%)")

    # =====================================================================
    # FINAL MODEL: train on 80/20 split for evaluation
    # =====================================================================
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    tuned_model.fit(X_train, y_train)
    predictions = tuned_model.predict(X_test)
    test_mae = mean_absolute_error(y_test, predictions)
    test_r2 = r2_score(y_test, predictions)

    print(f"\n--- Final Model ({best_model_name} tunet) - Test Set ---")
    print(f"  MAE: {test_mae:,.0f} kr")
    print(f"  R2:  {test_r2:.4f}")

    # =====================================================================
    # FEATURE IMPORTANCE: Gini/Gain, Permutation, SHAP
    # =====================================================================

    # 1. Native importance
    importances = tuned_model.feature_importances_

    # 2. Permutation
    print("\n--- Permutation Importance ---")
    perm_result = permutation_importance(
        tuned_model, X_test, y_test, n_repeats=10, random_state=42, n_jobs=-1
    )
    perm_imp = sorted(
        zip(feature_cols, perm_result.importances_mean, perm_result.importances_std),
        key=lambda x: x[1], reverse=True
    )
    for feat, mean_imp, std_imp in perm_imp:
        if mean_imp > 0.001:
            print(f"  {feat}: {mean_imp:.4f} +/- {std_imp:.4f}")

    # 3. SHAP
    print("\n--- SHAP Feature Importance ---")
    explainer = shap.TreeExplainer(tuned_model)
    shap_values = explainer.shap_values(X_test)
    shap_imp = np.abs(shap_values).mean(axis=0)
    shap_sorted = sorted(zip(feature_cols, shap_imp), key=lambda x: x[1], reverse=True)
    total_shap = sum(s for _, s in shap_sorted)
    for feat, s in shap_sorted:
        pct = (s / total_shap) * 100 if total_shap > 0 else 0
        if pct > 0.5:
            print(f"  {feat}: {s:,.0f} kr ({pct:.1f}%)")

    # Comparison table
    print(f"\n--- Sammenligning: Permutation vs SHAP ---")
    print(f"  {'Feature':<30} {'Perm':>8} {'SHAP':>8}")
    print(f"  {'-'*30} {'-'*8} {'-'*8}")
    perm_dict = {f: m for f, m, _ in perm_imp}
    perm_total = sum(max(0, v) for v in perm_dict.values())
    shap_dict = {f: s for f, s in shap_sorted}
    for feat in [f for f, _ in shap_sorted]:
        p = (perm_dict.get(feat, 0) / perm_total * 100) if perm_total > 0 else 0
        s = (shap_dict.get(feat, 0) / total_shap * 100) if total_shap > 0 else 0
        if p > 0.5 or s > 0.5:
            print(f"  {feat:<30} {p:>7.1f}% {s:>7.1f}%")

    # Save
    model_path = "leaf_model.pkl"
    joblib.dump({
        'model': tuned_model,
        'model_name': best_model_name,
        'feature_cols': feature_cols,
        'numeric_features': numeric_features,
        'trim_cols': trim_cols,
        'region_cols': region_cols,
        'cv_results': cv_results,
        'best_params': search.best_params_,
    }, model_path)
    print(f"\nModel saved: {best_model_name} (tunet) -> {model_path}")

if __name__ == "__main__":
    main()
