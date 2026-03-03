import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

# Konfigurer matplotlib for penere grafer
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("talk")
colors = sns.color_palette("husl", 8)

def ensure_plot_dir():
    plot_dir = "plots"
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    return plot_dir

def plot_depreciation_curve(df, plot_dir):
    """Plotter Verditapskurven (Pris vs. Alder)."""
    print("  -> Genererer Verditapskurve...")
    plt.figure(figsize=(12, 7))
    
    # Filtrer ut helt gale verdier for en mer lesbar graf
    plot_df = df[(df['year_cleaned'] >= 2011) & (df['price_cleaned'] < 400000)].copy()
    plot_df['age'] = 2026 - plot_df['year_cleaned']  # current year baseline
    
    # Dele opp i hovedbatterier (for fargekoding) og konverter til tekst
    common_batteries = [24.0, 30.0, 40.0, 62.0]
    plot_df['battery_capacity_cleaned'] = plot_df['battery_capacity_cleaned'].astype(str)
    plot_df.loc[~plot_df['battery_capacity_cleaned'].isin([str(x) for x in common_batteries]), 'battery_capacity_cleaned'] = 'Annet'
    plot_df['battery_capacity_cleaned'] = plot_df['battery_capacity_cleaned'].apply(lambda x: x if x == 'Annet' else f"{float(x):.0f} kWh")
    
    sns.scatterplot(
        data=plot_df, 
        x='age', 
        y='price_cleaned', 
        hue='battery_capacity_cleaned',
        palette='viridis',
        alpha=0.6,
        s=80
    )
    
    # Legg til en felles trendlinje for markedet generelt (LOWESS for å fange den kurvede minkingen bedre)
    sns.regplot(
        data=plot_df, 
        x='age', 
        y='price_cleaned', 
        scatter=False, 
        color='black', 
        lowess=True, 
        line_kws={'linestyle':'--', 'linewidth': 2, 'alpha': 0.8},
        label="Markedstrend (Gjennomsnitt)"
    )

    plt.title('Verditapskurve - Nissan Leaf på Finn.no', fontsize=16, pad=20)
    plt.xlabel('Bilens Alder (År)', fontsize=14)
    plt.ylabel('Pris (NOK)', fontsize=14)
    plt.gca().get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x)).replace(',', ' ')))
    
    plt.legend(title='Batteristørrelse', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "01_verditapskurve.png"), dpi=300)
    plt.close()

def plot_trim_premium(df, plot_dir):
    """Plotter Utstyrspremie (Boxplot av Pris per Trim)."""
    print("  -> Genererer Utstyrspremie-boxplot...")
    plt.figure(figsize=(12, 7))
    
    # Isolerer nyere biler (2019-2022) for å fjerne støy fra at gamle biler oftere er Visia/Acenta.
    # Da får vi sett isolert på hva markedet vil betale rent for trim-nivået på omtrent like ferske biler.
    plot_df = df[df['year_cleaned'].between(2019, 2022)].copy()
    
    # Sorter i forventet prisrekkefølge rent logisk
    trim_order = ['Tekna', 'N-Connecta', 'Acenta', 'Visia', 'Ukjent']
    # Beholder e+ utenfor for å unngå at batteriet overstyrer trim, men tar den med hvis ønskelig
    valid_trims = [t for t in trim_order if t in plot_df['trim_level'].unique()]
    
    if not valid_trims:
        print("    Ingen gyldige trims funnet for 2019-2022 for boxplot.")
        return

    sns.boxplot(
        data=plot_df, 
        x='trim_level', 
        y='price_cleaned', 
        order=valid_trims,
        palette='Set2',
        width=0.6,
        showfliers=False # Skjul ekstreme outliere for å se selve distribusjonen bedre
    )
    
    # Legg til alle faktiske datapunkter svakt oppå for å vise volumet
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

    plt.title('Hva koster de ulike utstyrspakkene? (Kun 2019-2022 modeller)', fontsize=16, pad=20)
    plt.xlabel('Utstyrsnivå (Trim)', fontsize=14)
    plt.ylabel('Pris (NOK)', fontsize=14)
    plt.gca().get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x)).replace(',', ' ')))
    
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "02_utstyrspremie.png"), dpi=300)
    plt.close()

def plot_deal_radar(deals_df, plot_dir):
    """Plotter "Kupp-radaren" (Forventet Pris vs. Faktisk Pris)."""
    print("  -> Genererer Kupp-radar...")
    plt.figure(figsize=(10, 10))
    
    # La oss kun plotte biler under f.eks 350k for å ikke la feilprisede vrak dra grafen
    plot_df = deals_df[(deals_df['price_cleaned'] < 350000) & (deals_df['predicted_value'] < 350000)].copy()
    
    # Tegn diagonalen (1:1 linjen der markedsverdi == faktisk pris)
    max_val = max(plot_df['price_cleaned'].max(), plot_df['predicted_value'].max())
    min_val = min(plot_df['price_cleaned'].min(), plot_df['predicted_value'].min())
    plt.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='Firkantet Pris (Faktisk = Markedsverdi)')
    
    # Fargekod basert på om det er forhandler eller privat
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
    
    # Marker de "Top 5 beste kjøpene" spesifikt ifølge maskinlæringen ("Discount")
    top_5 = plot_df.sort_values(by='value_difference', ascending=False).head(5)
    plt.scatter(top_5['predicted_value'], top_5['price_cleaned'], color='red', s=150, edgecolor='black', linewidth=2, zorder=5, label='Top 5 Kupper')

    plt.title('Kupp-Radaren: Markedsverdi vs Faktisk Pris', fontsize=16, pad=20)
    plt.xlabel('Forventet Markedsverdi iht. ML-modellen (NOK)', fontsize=14)
    plt.ylabel('Faktisk Listepris på Finn (NOK)', fontsize=14)
    plt.gca().get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x)).replace(',', ' ')))
    plt.gca().get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x)).replace(',', ' ')))
    
    plt.fill_between([min_val, max_val], [min_val, min_val], [min_val, max_val], color='green', alpha=0.05, label="Billigere enn markedet (Gode Kjøp)")
    plt.fill_between([min_val, max_val], [min_val, max_val], [max_val, max_val], color='red', alpha=0.05, label="Dyrere enn markedet (Dårlige Kjøp)")
    
    plt.legend(loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "03_kupp_radar.png"), dpi=300)
    plt.close()

def main():
    print("--- Starting Data Visualization ---")
    plot_dir = ensure_plot_dir()
    
    cleaned_data_path = "cleaned_data.csv"
    deals_data_path = "best_deals.csv"
    
    if not os.path.exists(cleaned_data_path):
        print(f"Error: {cleaned_data_path} not found.")
        sys.exit(1)
        
    if not os.path.exists(deals_data_path):
        print(f"Error: {deals_data_path} not found.")
        sys.exit(1)
        
    df_cleaned = pd.read_csv(cleaned_data_path)
    df_deals = pd.read_csv(deals_data_path)
    
    plot_depreciation_curve(df_cleaned, plot_dir)
    plot_trim_premium(df_cleaned, plot_dir)
    plot_deal_radar(df_deals, plot_dir)
    
    print(f"\nGenererte 3 grafer! Sjekk '{plot_dir}/' mappen for resultatet.")

if __name__ == "__main__":
    main()
