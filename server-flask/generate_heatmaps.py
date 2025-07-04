# server-flask/generate_heatmaps.py
import os
import pandas as pd
import json
import logging
import numpy as np  # <-- SOLUCIÓ 1: IMPORTACIÓ DE NUMPY
from matplotlib import pyplot as plt
import matplotlib # <-- AFEGIM AIXÒ
matplotlib.use('Agg') # <-- SOLUCIÓ 2: FORÇAR EL BACKEND NO INTERACTIU
from mplsoccer import Pitch, VerticalPitch
from scipy.ndimage import gaussian_filter
from matplotlib import patheffects
from ast import literal_eval

# --- Configuració ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_DATA_DIR = os.path.join(_PROJECT_ROOT, 'data')
_OUTPUT_IMG_DIR = os.path.join(_PROJECT_ROOT, 'server-flask', 'generated_images')

os.makedirs(_OUTPUT_IMG_DIR, exist_ok=True)

def safe_literal_eval(val):
    try:
        return literal_eval(val) if isinstance(val, str) else val
    except Exception:
        return None

def generate_and_save_pass_completion(df, player_id, season):
    try:
        df_passes = df[df.get("type") == "Pass"].copy()
        if df_passes.empty or not all(c in df_passes.columns for c in ["location", "pass_outcome"]):
            return

        df_passes["location_eval"] = df_passes["location"].apply(safe_literal_eval)
        df_valid_loc = df_passes.dropna(subset=['location_eval'])
        if df_valid_loc.empty: return

        df_valid_loc["x"] = df_valid_loc["location_eval"].apply(lambda loc: loc[0])
        df_valid_loc["y"] = df_valid_loc["location_eval"].apply(lambda loc: loc[1])
        df_valid_loc["completed"] = df_valid_loc["pass_outcome"].isna()

        pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='white')
        fig, ax = pitch.draw(figsize=(4.125, 6))
        fig.set_facecolor('#22312b')
        bin_statistic = pitch.bin_statistic_positional(df_valid_loc.x, df_valid_loc.y, values=df_valid_loc.completed, statistic='mean', positional='full')
        
        for section_data in bin_statistic:
            if 'statistic' in section_data and isinstance(section_data['statistic'], np.ndarray):
                section_data['statistic'] = np.nan_to_num(section_data['statistic'], nan=0.0)
            elif 'statistic' not in section_data or section_data['statistic'] is None: 
                if 'x_grid' in section_data and 'y_grid' in section_data and section_data['x_grid'] is not None and section_data['y_grid'] is not None:
                    section_data['statistic'] = np.zeros((section_data['y_grid'].shape[0]-1, section_data['x_grid'].shape[1]-1), dtype=float)
                else: section_data['statistic'] = np.array([[0.0]])

        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='Blues', edgecolors='#22312b', vmin=0, vmax=1)
        path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')]
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)
        
        output_path = os.path.join(_OUTPUT_IMG_DIR, f"{player_id}_{season}_pass_completion_heatmap.png")
        fig.savefig(output_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=100)
        plt.close(fig)
        logging.info(f"  Saved: pass completion heatmap for {player_id}_{season}")
    except Exception as e:
        logging.error(f"  Failed generating pass completion for {player_id}_{season}: {e}")

def generate_and_save_position(df, player_id, season):
    try:
        if "location" not in df.columns:
            return
        
        df["location_eval"] = df["location"].apply(safe_literal_eval)
        df_valid_loc = df.dropna(subset=['location_eval'])
        if df_valid_loc.empty: return

        df_valid_loc["x"] = df_valid_loc["location_eval"].apply(lambda loc: loc[0])
        df_valid_loc["y"] = df_valid_loc["location_eval"].apply(lambda loc: loc[1])
        
        pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='white')
        fig, ax = pitch.draw(figsize=(4.125, 6))
        fig.set_facecolor('#22312b')
        bin_statistic = pitch.bin_statistic_positional(df_valid_loc.x, df_valid_loc.y, statistic='count', positional='full', normalize=True)
        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='coolwarm', edgecolors='#22312b')
        path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')]
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)

        output_path = os.path.join(_OUTPUT_IMG_DIR, f"{player_id}_{season}_position_heatmap.png")
        fig.savefig(output_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=100)
        plt.close(fig)
        logging.info(f"  Saved: position heatmap for {player_id}_{season}")
    except Exception as e:
        logging.error(f"  Failed generating position heatmap for {player_id}_{season}: {e}")

def generate_and_save_pressure(df, player_id, season):
    try:
        df_pressure = df[df.get("type") == "Pressure"].copy()
        if df_pressure.empty or "location" not in df_pressure.columns:
            return

        df_pressure["location_eval"] = df_pressure["location"].apply(safe_literal_eval)
        df_valid_loc = df_pressure.dropna(subset=['location_eval'])
        if df_valid_loc.empty: return
        
        df_valid_loc["x"] = df_valid_loc["location_eval"].apply(lambda loc: loc[0])
        df_valid_loc["y"] = df_valid_loc["location_eval"].apply(lambda loc: loc[1])
        
        pitch = Pitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#000000', line_color='#efefef')
        fig, ax = pitch.draw(figsize=(6.6, 4.125))
        fig.set_facecolor('#000000')

        if not df_valid_loc.empty and not df_valid_loc['x'].empty:
            bin_statistic = pitch.bin_statistic(df_valid_loc.x, df_valid_loc.y, statistic='count', bins=(25, 25))
            if 'statistic' in bin_statistic and np.any(bin_statistic['statistic']):
                bin_statistic['statistic'] = gaussian_filter(bin_statistic['statistic'], 1)
                pcm = pitch.heatmap(bin_statistic, ax=ax, cmap='hot', edgecolors='#000000')
                cbar = fig.colorbar(pcm, ax=ax, shrink=0.6)
                cbar.outline.set_edgecolor('#efefef')
                cbar.ax.yaxis.set_tick_params(color='#efefef')
                plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#efefef')
        
        output_path = os.path.join(_OUTPUT_IMG_DIR, f"{player_id}_{season}_pressure_heatmap.png")
        fig.savefig(output_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), dpi=100)
        plt.close(fig)
        logging.info(f"  Saved: pressure heatmap for {player_id}_{season}")
    except Exception as e:
        logging.error(f"  Failed generating pressure heatmap for {player_id}_{season}: {e}")

def generate_all_heatmaps():
    try:
        with open(os.path.join(_DATA_DIR, 'player_index.json'), 'r', encoding='utf-8') as f:
            player_index = json.load(f)
    except FileNotFoundError:
        logging.error("player_index.json not found. Cannot proceed.")
        return

    player_items = player_index.items() if isinstance(player_index, dict) else [(p.get("name", ""), p) for p in player_index]

    for player_name, p_info in player_items:
        player_id = p_info.get("player_id")
        seasons = p_info.get("seasons", [])
        
        if not player_id: continue

        for season in seasons:
            logging.info(f"Processing {player_name} ({player_id}) - Season {season}")
            event_file = os.path.join(_DATA_DIR, season, 'players', f"{player_id}_{season}.csv")
            if not os.path.exists(event_file):
                logging.warning(f"  Event file not found, skipping: {event_file}")
                continue

            try:
                df = pd.read_csv(event_file, low_memory=False)
            except Exception as e:
                logging.error(f"  Could not read {event_file}: {e}")
                continue

            # Generar i guardar cada heatmap
            generate_and_save_pass_completion(df.copy(), player_id, season)
            generate_and_save_position(df.copy(), player_id, season)
            generate_and_save_pressure(df.copy(), player_id, season)

if __name__ == "__main__":
    generate_all_heatmaps()