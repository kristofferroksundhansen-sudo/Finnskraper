import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
import json
import argparse

# Konfigurer matplotlib for penere grafer
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("talk")


def load_car_profile(profile_name):
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config', 'cars', f'{profile_name}.json'
    )
    if not os.path.exists(config_path):
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def ensure_plot_dir(profile_name):
    plot_dir = os.path.join("plots", profile_name)
    os.makedirs(plot_dir, exist_ok=True)
    return plot_dir


def plot_depreciation_curve(df, plot_dir, label):
    """Plotter Verditapskurven (Pris vs. Alder)."""
    print("  -> Genererer Verditapskurve...")
    plt.figure(figsize=(12, 7))

    max_price = df['price_cleaned'].quantile(0.97)  # Dynamisk øverste grense
    plot_df = df[(df['year_cleaned'] >= 2014) & (df['price_cleaned'] < max_price)].copy()
    plot_df['age'] = 2026 - plot_df['year_cleaned']

    # Grupper batteristørrelser dynamisk – behold topp 4 og samle resten som "Annet"
    top_batteries = plot_df['battery_capacity_cleaned'].value_counts().nlargest(4).index.tolist()
    plot_df['batteri_label'] = plot_df['battery_capacity_cleaned'].apply(
        lambda x: f"{x:.0f} kWh" if x in top_batteries else 'Annet'
    )

    sns.scatterplot(
        data=plot_df,
        x='age',
        y='price_cleaned',
        hue='batteri_label',
        palette='viridis',
        alpha=0.6,
        s=80
    )

    sns.regplot(
        data=plot_df,
        x='age',
        y='price_cleaned',
        scatter=False,
        color='black',
        lowess=True,
        line_kws={'linestyle': '--', 'linewidth': 2, 'alpha': 0.8},
        label="Markedstrend (Gjennomsnitt)"
    )

    plt.title(f'Verditapskurve – {label} på Finn.no', fontsize=16, pad=20)
    plt.xlabel('Bilens Alder (År)', fontsize=14)
    plt.ylabel('Pris (NOK)', fontsize=14)
    plt.gca().get_yaxis().set_major_formatter(
        plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x)).replace(',', ' '))
    )
    plt.legend(title='Batteristørrelse', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "01_verditapskurve.png"), dpi=300)
    plt.close()


def plot_trim_premium(df, plot_dir, label, trim_order=None):
    """Plotter Utstyrspremie (Boxplot av Pris per Trim)."""
    print("  -> Genererer Utstyrspremie-boxplot...")
    plt.figure(figsize=(12, 7))

    # Isoler et relevant årsintervall
    min_year = max(df['year_cleaned'].min(), 2019)
    max_year = min(df['year_cleaned'].max(), 2023)
    plot_df = df[df['year_cleaned'].between(min_year, max_year)].copy()

    if trim_order is None:
        trim_order = sorted(plot_df['trim_level'].unique().tolist())
    valid_trims = [t for t in trim_order if t in plot_df['trim_level'].unique()]

    if not valid_trims:
        print("    Ingen gyldige trims funnet for boxplot.")
        return

    sns.boxplot(
        data=plot_df,
        x='trim_level',
        y='price_cleaned',
        order=valid_trims,
        palette='Set2',
        width=0.6,
        showfliers=False
    )
    sns.stripplot(
        data=plot_df,
        x='trim_level',
        y='price_cleaned',
        order=valid_trims,
        color='black',
        alpha=0.3,
        jitter=True,
        size=4
    )

    plt.title(f'Hva koster de ulike utstyrspakkene? – {label} ({int(min_year)}-{int(max_year)})', fontsize=16, pad=20)
    plt.xlabel('Utstyrsnivå (Trim)', fontsize=14)
    plt.ylabel('Pris (NOK)', fontsize=14)
    plt.gca().get_yaxis().set_major_formatter(
        plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x)).replace(',', ' '))
    )
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "02_utstyrspremie.png"), dpi=300)
    plt.close()


def plot_deal_radar(deals_df, plot_dir, label):
    """Plotter Kupp-radaren (Forventet Pris vs. Faktisk Pris)."""
    print("  -> Genererer Kupp-radar...")
    plt.figure(figsize=(10, 10))

    # Filtrer ut leasing/auksjon (ekstremt lave priser allerede ekskludert fra deals_df via min_price_filter)
    price_cap = deals_df['price_cleaned'].quantile(0.97)
    plot_df = deals_df[
        (deals_df['price_cleaned'] < price_cap) &
        (deals_df['predicted_value'] < price_cap)
    ].copy()

    max_val = max(plot_df['price_cleaned'].max(), plot_df['predicted_value'].max())
    min_val = min(plot_df['price_cleaned'].min(), plot_df['predicted_value'].min())
    plt.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='Faktisk = Markedsverdi')

    plot_df['Selger Type'] = plot_df['is_dealer'].apply(lambda x: 'Forhandler' if x == 1 else 'Privat')
    sns.scatterplot(
        data=plot_df,
        x='predicted_value',
        y='price_cleaned',
        hue='Selger Type',
        style='Selger Type',
        palette={'Forhandler': '#ff7f0e', 'Privat': '#1f77b4'},
        s=80,
        alpha=0.7
    )

    top_5 = plot_df.sort_values(by='value_difference', ascending=False).head(5)
    plt.scatter(top_5['predicted_value'], top_5['price_cleaned'],
                color='red', s=150, edgecolor='black', linewidth=2, zorder=5, label='Top 5 Kupper')

    plt.title(f'Kupp-Radaren: Markedsverdi vs Faktisk Pris – {label}', fontsize=16, pad=20)
    plt.xlabel('Forventet Markedsverdi (NOK)', fontsize=14)
    plt.ylabel('Faktisk Listepris på Finn (NOK)', fontsize=14)
    fmt = plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x)).replace(',', ' '))
    plt.gca().get_xaxis().set_major_formatter(fmt)
    plt.gca().get_yaxis().set_major_formatter(fmt)
    plt.fill_between([min_val, max_val], [min_val, min_val], [min_val, max_val],
                     color='green', alpha=0.05, label="Billigere enn markedet")
    plt.fill_between([min_val, max_val], [min_val, max_val], [max_val, max_val],
                     color='red', alpha=0.05, label="Dyrere enn markedet")
    plt.legend(loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "03_kupp_radar.png"), dpi=300)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Finn.no datavisualisering')
    parser.add_argument('--profile', default='nissan_leaf',
                        help='Bilprofil fra config/cars/ (uten .json). Standard: nissan_leaf')
    args = parser.parse_args()

    car_profile = load_car_profile(args.profile)
    if car_profile:
        car_make  = car_profile['make']
        car_model = car_profile['model']
        label     = f"{car_make} {car_model}"
        trim_order = [t['name'] for t in car_profile.get('trims', [])] + ['Ukjent']
        deals_path = f"best_deals_{args.profile}.csv"
    else:
        label = "Alle biler"
        trim_order = None
        deals_path = "best_deals.csv"

    print(f"--- Data Visualization: {label} ---")
    plot_dir = ensure_plot_dir(args.profile)

    cleaned_path = "cleaned_data.csv"
    if not os.path.exists(cleaned_path):
        print(f"Error: {cleaned_path} not found.")
        sys.exit(1)
    if not os.path.exists(deals_path):
        print(f"Error: {deals_path} not found. Run 03_find_deals.py --profile {args.profile} first.")
        sys.exit(1)

    df_cleaned = pd.read_csv(cleaned_path)
    df_deals   = pd.read_csv(deals_path)

    # Filtrer cleaned data til aktuell bilmodell
    if car_profile and 'car_make' in df_cleaned.columns:
        df_cleaned = df_cleaned[
            (df_cleaned['car_make'] == car_make) & (df_cleaned['car_model'] == car_model)
        ]
        print(f"Filtrert cleaned data til {len(df_cleaned)} rader for {label}.")

    plot_depreciation_curve(df_cleaned, plot_dir, label)
    plot_trim_premium(df_cleaned, plot_dir, label, trim_order=trim_order)
    plot_deal_radar(df_deals, plot_dir, label)

    print(f"\nGenererte 3 grafer i 'plots/{args.profile}/'!")


if __name__ == "__main__":
    main()
