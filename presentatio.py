import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

MODEL_BASE_DIR = "ml_models/ml_model_files_peak_potential/peak_potential_v2_15_16"
MODEL_ID = "peak_potential_v2_15_16"
OUTPUT_DIR = "presentation_extras"

os.makedirs(OUTPUT_DIR, exist_ok=True)

positions_config = {    
    "Atacant": os.path.join(MODEL_BASE_DIR, "attacker", f"model_config_attacker_{MODEL_ID}.json"),
    "Migcampista": os.path.join(MODEL_BASE_DIR, "midfielder", f"model_config_midfielder_{MODEL_ID}.json"),
    "Defensor": os.path.join(MODEL_BASE_DIR, "defender", f"model_config_defender_{MODEL_ID}.json"),
}

def generate_and_save_chart(weights_dict, position, output_path):
    """
    Genera un gràfic de barres horitzontal amb els pesos dels KPI i el desa.
    """
    if not weights_dict:
        print(f"No s'han trobat pesos per a la posició: {position}")
        return

    df_weights = pd.DataFrame(list(weights_dict.items()), columns=['KPI', 'Weight'])
    
    df_weights = df_weights.sort_values('Weight', ascending=False).head(15)

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 8))

    bars = ax.barh(df_weights['KPI'], df_weights['Weight'], color='#005f73')
    
    ax.invert_yaxis()
    
    ax.set_title(f'Top 15 KPIs Més Influents per a: {position}', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Pes Normalitzat (Importància Relativa)', fontsize=12)
    ax.tick_params(axis='y', labelsize=10)

    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.001, bar.get_y() + bar.get_height()/2,
                f'{width:.3f}', va='center', ha='left', fontsize=9)
    
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Gràfic per a '{position}' desat a: {output_path}")

if __name__ == "__main__":
    for position, config_path in positions_config.items():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            weights = config_data.get("target_variable_generation", {}).get("derived_kpi_weights_for_target", {})
            
            output_file = os.path.join(OUTPUT_DIR, f"pesos_kpi_{position.lower()}.png")
            generate_and_save_chart(weights, position, output_file)
            
        except FileNotFoundError:
            print(f"ERROR: No s'ha trobat el fitxer de configuració: {config_path}")
        except KeyError:
            print(f"ERROR: La clau 'derived_kpi_weights_for_target' no es troba a {config_path}")
        except Exception as e:
            print(f"Ha ocorregut un error inesperat processant {position}: {e}")