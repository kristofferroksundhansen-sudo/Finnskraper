# 🚗 Finn-scraper Roadmap

> Sist oppdatert: 3. mars 2026

## ✅ Fullført

- [x] Grunnleggende skraper (Playwright + Apify)
- [x] Paginering (alle sider, ikke bare side 1)
- [x] Deduplisering (lag 1: skraper, lag 2: historisk DB)
- [x] Hybrid crawler – Playwright for listesider, Cheerio for detalj (~27x raskere)
- [x] RandomForest-modell med 5-fold CV
- [x] Pipeline: rens → tren → finn kupp → statistikk
- [x] EU-kontroll som feature
- [x] Parse utstyrsnivå fra tittel (Tekna, Acenta, Visia, N-Connecta, e+)
- [x] Lokasjon som feature (8 regioner, one-hot encoded)
- [x] Forhandler-deteksjon (`is_dealer` fra `By ∙ Forhandler AS`-mønster)
- [x] 5-fold cross-validation (CV R²=0.94 ± 0.007)
- [x] Datatap-logging (detaljert per årsak: pris/km/år/outlier)
- [x] Permutation importance + SHAP-analyse (3 uavhengige importance-metoder)

---

## 🟡 Middels prioritet

### Modell

- [ ] **Test XGBoost / LightGBM**
  - Ofte 5-15% bedre enn RandomForest
  - Enkel å implementere med samme data
  - Sammenlign MAE og R² mot nåværende modell

- [ ] **Hyperparameter-tuning**
  - Nåværende RF bruker defaults (100 trær)
  - Test `n_estimators`, `max_depth`, `min_samples_leaf`
  - Bruk `GridSearchCV` eller `RandomizedSearchCV`

### Nye features

- [ ] **Parse rekkevidde-feltet**
  - Bedre indikator for batteritype/tilstand enn kWh alene
  - Finnes i specs fra Finn

- [ ] **Annonsealder som feature**
  - Annonse som har ligget lenge = mulig overpriset
  - `first_seen_date` finnes allerede i historisk DB

- [ ] **Garanti-info**
  - Bil med resterende garanti er mer verdt
  - Skrapes allerede i specs, men brukes ikke

---

## 🟢 Lav prioritet (nice-to-have)

### Datarens

- [ ] **Smartere outlier-fjerning**
  - Nåværende: `price > 10 000` og `year >= 2010` (grovt)
  - Bedre: IQR eller z-score per årsmodell

- [ ] **Feature engineering: pris per km**
  - `price_per_km = price / mileage` kan gi bedre signal

### Analyse

- [ ] **Historisk prisfall-analyse**
  - Spor prisendringer over tid med `first_seen_date`
  - Finn motiverte selgere som senker prisen

- [ ] **Visualiseringer** (matplotlib/plotly)
  - Prisspredning per årsmodell (box plots)
  - Predicted vs. actual scatter plot
  - Feature importance bar chart (Gini vs SHAP)
  - Geografisk prisfordeling (kart)

### Skalering

- [ ] **Utvid til hele Norge** (fjern `location`-filter i søk)
- [ ] **Skrape flere bilmodeller** (Tesla Model 3, VW ID.3, etc.)
- [ ] **Schedulert daglig kjøring** (Apify Schedules)

---

## 📊 Nåværende ytelse

| Metrikk | Verdi |
|---------|-------|
| Skrapetid (100 annonser) | ~1.5 min |
| CU-kostnad per kjøring | ~0.025 CU |
| Modell R² (5-fold CV) | 0.94 ± 0.007 |
| Modell MAE (5-fold CV) | 11 489 ± 1 080 kr |
| Treningsdata | 340 rader |

### Feature importance (SHAP vs Gini)

| Feature | Gini | SHAP |
|---------|-----:|-----:|
| `age` | 85.6% | **70.4%** |
| `mileage` | 7.7% | **16.1%** |
| `effect (kW)` | 4.1% | **6.9%** |
| `months_to_eu` | 0.8% | 2.1% |
| `battery_kWh` | 0.6% | 1.2% |
| `region` | 0.3% | 1.1% |
| `owners` | 0.3% | 0.6% |
