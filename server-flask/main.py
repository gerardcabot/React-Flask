from flask import Flask, jsonify, request, send_file
import os
import pandas as pd
from flask_cors import CORS
import matplotlib
from matplotlib import pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from ast import literal_eval
import json
from scipy.ndimage import gaussian_filter
from matplotlib import patheffects
import logging
import numpy as np
import joblib
import datetime
import uuid 
import boto3
from io import BytesIO, StringIO

from model_trainer.trainer_v2 import (
    build_and_train_model_from_script_logic,
    get_trainer_kpi_definitions_for_weight_derivation,
    # get_trainer_composite_impact_kpis_definitions,
    get_general_position as trainer_get_general_position, 
    # parse_location as trainer_parse_location,
    get_feature_names_for_extraction as trainer_get_feature_names,
    extract_season_features as trainer_extract_base_features,
    trainer_construct_ml_features_for_player_season, 
    safe_division as trainer_safe_division, 
    get_trainer_all_possible_ml_feature_names 
)


# --- CONFIGURACIÓN DE CONEXIÓN A R2 (CORRECTO) ---
R2_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_client = None
if R2_ENDPOINT_URL and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME:
    logger.info("R2 environment variables found. Initializing S3 client.")
    s3_client = boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name='auto'  # 'auto' is correct for R2
    )
else:
    logger.warning("R2 environment variables not set. S3 client not initialized. App will likely fail.")



BASE_DIR_SERVER_FLASK = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "..", "data")

# V14_MODEL_BASE_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "..", "ml_models", "ml_model_files_v14_rebuild_trainer", "v14_rebuild") # Ruta ajustada
# V14_MODEL_BASE_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "..", "ml_models", "ml_model_files_peak_potential", "peak_potential_v1")
V14_MODEL_BASE_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "..", "ml_models", "ml_model_files_peak_potential", "peak_potential_v2_15_16")

PLAYER_MINUTES_PATH = os.path.join(DATA_DIR, "player_season_minutes_with_names.csv")
# LOADED_V14_MODELS = {}

STATIC_IMG_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "static", "images")
os.makedirs(STATIC_IMG_DIR, exist_ok=True)

CUSTOM_MODELS_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "ml_models", "custom_models")
os.makedirs(CUSTOM_MODELS_DIR, exist_ok=True)

matplotlib.use("Agg")

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError, AttributeError): 
        return default

def safe_literal_eval(val):
    try:
        return literal_eval(val) if isinstance(val, str) else val
    except Exception:
        return None


def _format_value_counts(series, sort_index=False):
    if series is None or series.empty: return []
    counts = series.value_counts()
    if sort_index: counts = counts.sort_index()
    return [{"name": str(idx), "value": int(val)} for idx, val in counts.items()]

# def load_player_data(player_id, season, data_dir):
#     def try_load_one(player_id, season, data_dir):
#         file_path_json = os.path.join(data_dir, str(season), f"{player_id}.json")
#         if os.path.exists(file_path_json):
#             try:
#                 logger.debug(f"Loading JSON: {file_path_json}")
#                 return pd.read_json(file_path_json, convert_dates=False)
#             except Exception as e:
#                 logger.error(f"Error loading JSON {file_path_json}: {e}")
#                 pass

#         file_path_csv = os.path.join(data_dir, str(season), "players", f"{player_id}_{season}.csv")
#         if os.path.exists(file_path_csv):
#             try:
#                 logger.debug(f"Loading CSV: {file_path_csv}")
#                 df = pd.read_csv(file_path_csv, low_memory=False)
#                 loc_cols = [col for col in df.columns if 'location' in col or 'end_location' in col]
#                 for col in loc_cols:
#                     if col in df.columns: df[col] = df[col].apply(lambda x: safe_literal_eval(x) if pd.notna(x) else None)

#                 bool_cols_to_check = [
#                     'counterpress', 
#                     'offensive', 
#                     'recovery_failure',
#                     'deflection',
#                     'save_block',
#                     'aerial_won',
#                     'nutmeg',
#                     'overrun',
#                     'no_touch', 
#                     'leads_to_shot',
#                     'advantage', 
#                     'penalty',   
#                     'defensive',
#                     'backheel',
#                     'deflected', 
#                     'miscommunication',
#                     'cross',
#                     'cut_back',
#                     'switch',
#                     'shot_assist',
#                     'goal_assist',
#                     'follows_dribble',
#                     'first_time',
#                     'open_goal',
#                     'deflected',
#                     'under_pressure',
#                     'out'
#                 ]
#                 bool_cols_to_check = sorted(list(set(bool_cols_to_check)))


#                 for col in bool_cols_to_check:
#                     if col in df.columns:
#                         if df[col].dtype == 'object':
#                             df[col] = df[col].astype(str).str.lower().map(
#                                 {'true': True, 'false': False, 'nan': pd.NA, '': pd.NA}
#                             ).astype('boolean') 
#                         elif pd.api.types.is_numeric_dtype(df[col]):
#                             df[col] = df[col].map({1.0: True, 1: True, 0.0: False, 0: False}).astype('boolean')
                
#                 numeric_cols_to_check = ['duration', 'pass_length', 'pass_angle', 'shot_statsbomb_xg', 'statsbomb_xg'] 
#                 for col in numeric_cols_to_check:
#                     if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
#                 return df
#             except Exception as e: logger.error(f"Error loading CSV {file_path_csv}: {e}"); pass
#         logger.warning(f"No data file found for player {player_id} in season {season} (tried JSON: {file_path_json}, CSV: {file_path_csv})")
#         return None

#     if season == "all":
#         dfs = []
#         for season_folder_name in os.listdir(data_dir):
#             season_folder_path = os.path.join(data_dir, season_folder_name)
#             if os.path.isdir(season_folder_path) and '_' in season_folder_name:
#                 df_season = try_load_one(player_id, season_folder_name, data_dir)
#                 if df_season is not None and not df_season.empty: dfs.append(df_season)
#         if dfs: return pd.concat(dfs, ignore_index=True)
#         else: logger.info(f"No data found for player {player_id} across any seasons."); return pd.DataFrame()
#     else:
#         return try_load_one(player_id, season, data_dir)

def load_player_data(player_id, season, data_dir): # El parámetro data_dir ya no se usa, pero lo dejamos
    def try_load_one_from_r2(player_id, season):
        if not s3_client:
            logger.error("Cannot load from R2: S3 client not initialized.")
            return None
            
        # La ruta al archivo dentro del bucket
        file_key_csv = f"data/{season}/players/{player_id}_{season}.csv"
        
        try:
            logger.debug(f"Attempting to load from R2: {R2_BUCKET_NAME}/{file_key_csv}")
            response = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=file_key_csv)
            
            # Leer el contenido en un DataFrame de pandas
            csv_content = response['Body'].read().decode('utf-8')
            df = pd.read_csv(StringIO(csv_content), low_memory=False)

            # --- TU LÓGICA DE PROCESADO SE MANTIENE EXACTAMENTE IGUAL ---
            loc_cols = [col for col in df.columns if 'location' in col or 'end_location' in col]
            for col in loc_cols:
                if col in df.columns: df[col] = df[col].apply(lambda x: safe_literal_eval(x) if pd.notna(x) else None)
            
            bool_cols_to_check = [
                'counterpress', 'offensive', 'recovery_failure', 'deflection', 'save_block', 'aerial_won', 'nutmeg', 'overrun',
                'no_touch', 'leads_to_shot', 'advantage', 'penalty', 'defensive', 'backheel', 'deflected', 'miscommunication',
                'cross', 'cut_back', 'switch', 'shot_assist', 'goal_assist', 'follows_dribble', 'first_time', 'open_goal',
                'under_pressure', 'out'
            ]
            bool_cols_to_check = sorted(list(set(bool_cols_to_check)))

            for col in bool_cols_to_check:
                if col in df.columns:
                    if df[col].dtype == 'object':
                        df[col] = df[col].astype(str).str.lower().map({'true': True, 'false': False, 'nan': pd.NA, '': pd.NA}).astype('boolean')
                    elif pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = df[col].map({1.0: True, 1: True, 0.0: False, 0: False}).astype('boolean')
            
            numeric_cols_to_check = ['duration', 'pass_length', 'pass_angle', 'shot_statsbomb_xg', 'statsbomb_xg']
            for col in numeric_cols_to_check:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        except s3_client.exceptions.NoSuchKey:
            logger.warning(f"R2 object not found: {R2_BUCKET_NAME}/{file_key_csv}")
            return None
        except Exception as e:
            logger.error(f"Error loading {file_key_csv} from R2: {e}", exc_info=True)
            return None

    # El modo "all" es ineficiente y no funcionará sin listar el bucket.
    # Por ahora, lo simplificamos para que la app funcione.
    if season == "all":
        logger.warning("Loading 'all' seasons is not fully supported in production environment. Returning empty DataFrame.")
        return pd.DataFrame()
    else:
        return try_load_one_from_r2(player_id, season)

app = Flask(__name__, static_folder=os.path.join(BASE_DIR_SERVER_FLASK, 'static'), static_url_path='/static')
# CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
CORS(app, resources={r"/*": {"origins": "*"}})


def _calculate_goalkeeper_metrics(player_df, player_id_str):
    empty_results = {
        "player_id": player_id_str, "error": None,
        "summary_text_stats": {
            "total_actions_recorded": 0,
            "total_passes": 0, "passes_completed": 0, "passes_incomplete_explicit": 0, "pass_accuracy_percentage": 0.0,
            "total_gk_specific_actions": 0,
            "saves_from_gk_events_colab_def": 0, 
            "goals_conceded_from_gk_events_colab_def": 0, 
            "shots_faced_in_gk_events_colab_def": 0, 
            "save_percentage_from_gk_events_colab_def": 0.0,
            "total_shots_faced_on_target_direct": 0, 
            "saves_direct_involvement": 0, 
            "goals_conceded_direct_involvement": 0, 
            "save_percentage_direct_involvement": 0.0,
            "carries_count": 0, "receipts_count": 0
        },
        "charts_data": {
            "overall_action_type_distribution": [],
            "pass_height_distribution": [],
            "pass_outcome_pie_chart_data": [],
            "gk_event_type_distribution": [],
        },
        "raw_data_points": {
            "shots_faced_map_data": [] 
        }
    }

    if player_df.empty:
        empty_results["error"] = f"No data provided for player {player_id_str}."
        return empty_results
    if 'player_id' not in player_df.columns:
        empty_results["error"] = "'player_id' column missing."
        return empty_results

    df_player_events = player_df[player_df['player_id'].astype(str) == str(player_id_str)].copy()
    if df_player_events.empty:
        empty_results["error"] = f"No events found for player_id {player_id_str} in filtered DataFrame."
        return empty_results

    results = json.loads(json.dumps(empty_results))
    results.pop("error", None)
    results["player_id"] = player_id_str
    summary_stats = results["summary_text_stats"]

    summary_stats["total_actions_recorded"] = len(df_player_events)
    results["charts_data"]["overall_action_type_distribution"] = _format_value_counts(df_player_events.get('type'))

    df_passes = df_player_events[df_player_events.get('type') == 'Pass'].copy() if 'type' in df_player_events else pd.DataFrame()
    if not df_passes.empty:
        summary_stats["total_passes"] = len(df_passes)
        colab_pass_failure_outcomes = ['Incomplete', 'Out', 'Pass Offside', 'Injury Clearance', 'Unknown']
        if 'pass_outcome' in df_passes.columns:
            summary_stats["passes_completed"] = int(len(df_passes[~df_passes['pass_outcome'].astype(str).isin(colab_pass_failure_outcomes)]))
            summary_stats["passes_incomplete_explicit"] = int((df_passes['pass_outcome'] == 'Incomplete').sum())
            pass_outcome_for_pie = df_passes['pass_outcome'].fillna('Completed (Implied)')
            results["charts_data"]["pass_outcome_pie_chart_data"] = _format_value_counts(pass_outcome_for_pie)
        else:
            summary_stats["passes_completed"] = summary_stats["total_passes"]
            results["charts_data"]["pass_outcome_pie_chart_data"] = [{"name": "Unknown Outcome", "value": summary_stats["total_passes"]}]

        if summary_stats["total_passes"] > 0:
            summary_stats["pass_accuracy_percentage"] = round((summary_stats["passes_completed"] / summary_stats["total_passes"]) * 100, 2)
        results["charts_data"]["pass_height_distribution"] = _format_value_counts(df_passes.get('pass_height'))

    df_gk_actions = df_player_events[df_player_events.get('type') == 'Goal Keeper'].copy() if 'type' in df_player_events else pd.DataFrame()
    summary_stats["total_gk_specific_actions"] = len(df_gk_actions)
    results["charts_data"]["gk_event_type_distribution"] = _format_value_counts(df_gk_actions.get('goalkeeper_type'))
    
    if not df_gk_actions.empty and 'goalkeeper_type' in df_gk_actions.columns and 'goalkeeper_outcome' in df_gk_actions.columns:
        colab_save_types = ['Shot Saved', 'Penalty Saved', 'Save', 'Smother']
        sb_v11_success_outcomes_for_saves = ['Success', 'Success In Play', 'Success Out', 'Collected', 'Claim']
        
        summary_stats["saves_from_gk_events_colab_def"] = int(len(df_gk_actions[
            (df_gk_actions['goalkeeper_type'].isin(colab_save_types)) &
            (df_gk_actions['goalkeeper_outcome'].isin(sb_v11_success_outcomes_for_saves))
        ]))
        summary_stats["goals_conceded_from_gk_events_colab_def"] = int((df_gk_actions['goalkeeper_type'] == 'Goal Conceded').sum())
        summary_stats["shots_faced_in_gk_events_colab_def"] = int((df_gk_actions['goalkeeper_type'] == 'Shot Faced').sum())
        
        shots_on_target_colab_def = summary_stats["saves_from_gk_events_colab_def"] + summary_stats["goals_conceded_from_gk_events_colab_def"]
        if shots_on_target_colab_def > 0:
            summary_stats["save_percentage_from_gk_events_colab_def"] = round(
                (summary_stats["saves_from_gk_events_colab_def"] / shots_on_target_colab_def) * 100, 2)

    shots_faced_map_data_list = []
    goals_conceded_direct = 0
    saves_direct = 0

    shot_related_gk_types_for_direct_analysis = ['Shot Saved', 'Penalty Saved', 'Goal Conceded', 'Save', 'Shot Faced']
    df_direct_shot_interactions = df_gk_actions[df_gk_actions.get('goalkeeper_type', pd.Series(dtype=str)).isin(shot_related_gk_types_for_direct_analysis)]

    # Attempt to find an xG column on GK events (though unlikely as per spec)
    xg_col_on_gk_event = None
    if not df_direct_shot_interactions.empty:
        potential_xg_cols = ['shot_statsbomb_xg', 'goalkeeper.shot_statsbomb_xg', 'xg']
        for col in potential_xg_cols:
            if col in df_direct_shot_interactions.columns:
                xg_col_on_gk_event = col
                break

    for _, row in df_direct_shot_interactions.iterrows():
        shot_loc = safe_literal_eval(row.get('location'))
        shot_end_loc = safe_literal_eval(row.get('shot_end_location'))
        
        is_goal_flag = None
        shot_outcome_for_map = row.get('goalkeeper_type')

        if row.get('goalkeeper_type') == 'Goal Conceded':
            is_goal_flag = True
            goals_conceded_direct += 1
        elif row.get('goalkeeper_type') in ['Shot Saved', 'Penalty Saved', 'Save']:
            save_outcomes_sb = ['Success', 'Success In Play', 'Success Out', 'Collected', 'Claim', 'In Play Safe', 'Saved Twice', 'Touched Out']
            if row.get('goalkeeper_outcome') in save_outcomes_sb:
                is_goal_flag = False
                saves_direct += 1
            shot_outcome_for_map = 'Saved' if is_goal_flag is False else shot_outcome_for_map
        elif row.get('goalkeeper_type') == 'Shot Faced':
             shot_outcome_for_map = 'Faced'


        map_entry = {
            "origin": shot_loc[:2] if shot_loc and len(shot_loc) >=2 else None,
            "end_location": shot_end_loc[:3] if shot_end_loc and len(shot_end_loc) >=3 else None,
            "outcome": shot_outcome_for_map, "is_goal": is_goal_flag,
            "minute": int(safe_float(row.get("minute"))), "second": int(safe_float(row.get("second")))
        }
        if map_entry["origin"]: 
            shots_faced_map_data_list.append(map_entry)
            
    results["raw_data_points"]["shots_faced_map_data"] = shots_faced_map_data_list
    
    summary_stats["total_shots_faced_on_target_direct"] = saves_direct + goals_conceded_direct
    summary_stats["saves_direct_involvement"] = saves_direct
    summary_stats["goals_conceded_direct_involvement"] = goals_conceded_direct
    if summary_stats["total_shots_faced_on_target_direct"] > 0:
        summary_stats["save_percentage_direct_involvement"] = round(
            (saves_direct / summary_stats["total_shots_faced_on_target_direct"]) * 100, 2
        )

    df_carries = df_player_events[df_player_events.get('type') == 'Carry'] if 'type' in df_player_events else pd.DataFrame()
    summary_stats["carries_count"] = len(df_carries)
    df_receipts = df_player_events[df_player_events.get('type') == 'Ball Receipt*'] if 'type' in df_player_events else pd.DataFrame()
    summary_stats["receipts_count"] = len(df_receipts)
    
    return results

def get_age_at_fixed_point_in_season(dob_str, season_str):
    try:
        birth_date = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date()
        season_end_year = int(str(season_str).split('_')[1])
        fixed_date_in_season = datetime.date(season_end_year, 1, 1)
        age = fixed_date_in_season.year - birth_date.year - \
              ((fixed_date_in_season.month, fixed_date_in_season.day) < (birth_date.month, birth_date.day))
        return age
    except Exception as e: logger.error(f"Error calculating age for DOB {dob_str}, season {season_str}: {e}"); return None


def structure_kpis_for_frontend(kpi_definitions_by_position):
    """
    Transforma el diccionari de KPIs per posició en una estructura més amigable
    per al frontend, agrupant mètriques base amb les seves variants.
    També genera una llista plana de tots els noms de kpi tècnics per a la validació.
    """
    structured_kpis = []
    all_technical_kpi_names = set()
    metric_map = {} 

    raw_kpis_flat = set()
    for pos_kpis in kpi_definitions_by_position.values():
        raw_kpis_flat.update(pos_kpis)

    for kpi_name in sorted(list(raw_kpis_flat)):
        all_technical_kpi_names.add(kpi_name)
        base_name = kpi_name
        variant_type = "total" 
        label_suffix = ""

        if kpi_name.endswith("_p90_sqrt_"):
            base_name = kpi_name.replace("_p90_sqrt_", "")
            variant_type = "p90_sqrt"
            label_suffix = " (per 90 min, arrel quadrada)"
        elif kpi_name.endswith("_sqrt_"):
            base_name = kpi_name.replace("_sqrt_", "")
            variant_type = "sqrt"
            label_suffix = " (arrel quadrada)"
        elif kpi_name.endswith("_p90"):
            base_name = kpi_name.replace("_p90", "")
            variant_type = "p90"
            label_suffix = " (per 90 min)"
        elif kpi_name.endswith("_kpi"): 
             base_name = kpi_name
             variant_type = "direct_kpi" 
        elif kpi_name.endswith("_base") and "_inv_kpi_base" in kpi_name: 
             base_name = kpi_name.replace("_p90_inv_kpi_base", "_turnovers") 
             variant_type = "p90_inv_base"
             label_suffix = " (Pèrdues p90, invertit, valor base)"
        
        label_base = base_name.replace('_', ' ').replace("count ", "").replace("sum ", "")
        label_base = ' '.join(word.capitalize() for word in label_base.split(' '))
        if variant_type == "direct_kpi":
            label = label_base
        else:
            label = f"{label_base}{label_suffix}"

        if base_name not in metric_map:
            metric_map[base_name] = {"id_base": base_name, "label_base": label_base, "variants": {}}
        
        metric_map[base_name]["variants"][variant_type] = {
            "id": kpi_name,
            "label_variant": label_suffix.strip(" ()"), 
            "full_label": label 
        }
        if not label_suffix and variant_type == "total":
             metric_map[base_name]["variants"][variant_type]["label_variant"] = "Total / Recompte"


    for base_info in metric_map.values():
        if base_info["variants"]:
            variants_list = []
            order = ["total", "p90", "p90_sqrt", "sqrt", "direct_kpi", "p90_inv_base"]
            for variant_key in order:
                if variant_key in base_info["variants"]:
                    variants_list.append(base_info["variants"][variant_key])
            if variants_list: 
                 structured_kpis.append({
                    "metric_base_id": base_info["id_base"],
                    "metric_base_label": base_info["label_base"],
                    "options": variants_list
                })
    
    structured_kpis.sort(key=lambda x: x["metric_base_label"]) 

    return structured_kpis, sorted(list(all_technical_kpi_names))

# --- API Routes ---

@app.route("/")
def home(): return jsonify({"message": "Welcome to the Player Stats API."})

# player_index_path_main = os.path.join(DATA_DIR, "player_index.json")
# player_index_main_data = {}
# if os.path.exists(player_index_path_main):
#     try:
#         with open(player_index_path_main, "r", encoding="utf-8") as f: player_index_main_data = json.load(f)
#     except Exception as e: logger.error(f"Error loading player_index.json for main: {e}")
# else: logger.warning("main.py: player_index.json not found.")

player_index_main_data = {}
if s3_client:
    try:
        logger.info(f"Loading player_index.json from R2 bucket: {R2_BUCKET_NAME}")
        response = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key="data/player_index.json")
        content = response['Body'].read().decode('utf-8')
        player_index_main_data = json.loads(content)
        logger.info("Successfully loaded player_index.json from R2.")
    except Exception as e:
        logger.error(f"Error loading player_index.json from R2: {e}")

@app.route("/players")
def players_route():
    try:
        return jsonify([
            {"name": name, "player_id": data["player_id"], "seasons": data.get("seasons", []), "dob": data.get("dob", "")}
            for name, data in sorted(player_index_main_data.items()) if isinstance(data, dict) and "player_id" in data
        ])
    except Exception as e: logger.error(f"Error in /players: {e}", exc_info=True); return jsonify({"error": str(e)}), 500

@app.route("/player_seasons")
def player_seasons_route():
    player_id = request.args.get("player_id")
    if not player_id: return jsonify({"error": "Missing player_id"}), 400
    try:
        player_data = next((data for data in player_index_main_data.values() if isinstance(data, dict) and str(data.get("player_id")) == str(player_id)), None)
        if not player_data: return jsonify({"error": "Player not found"}), 404
        return jsonify({"player_id": player_id, "seasons": player_data.get("seasons", [])})
    except Exception as e: logger.error(f"Error in /player_seasons: {e}", exc_info=True); return jsonify({"error": str(e)}), 500

@app.route("/player_events")
def player_events_route():
    player_id = request.args.get("player_id"); season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"error": "No data found"}), 404
        return df.to_json(orient="records", date_format="iso", default_handler=str)
    except Exception as e: logger.error(f"Error in /player_events: {e}", exc_info=True); return jsonify({"error": str(e)}), 500

# @app.route("/pass_completion_heatmap")
# def pass_completion_heatmap_route():
#     player_id = request.args.get("player_id")
#     season = request.args.get("season")
#     if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
#     try:
#         player_dir = os.path.join(STATIC_IMG_DIR, str(player_id))
#         os.makedirs(player_dir, exist_ok=True)
#         image_filename = f"{str(player_id)}_{season}_pass_compl_heatmap.png"
#         image_path = os.path.join(player_dir, image_filename)
#         image_url = f"/static/images/{str(player_id)}/{image_filename}"

#         df = load_player_data(player_id, season, DATA_DIR)
#         if df is None or df.empty:
#             logger.warning(f"No data for pass completion heatmap {player_id}/{season}")
#             return jsonify({"error": "No data found"}), 404

#         df_passes = df[df.get("type") == "Pass"].copy() if "type" in df.columns else pd.DataFrame()

#         if df_passes.empty or not all(c in df_passes.columns for c in ["location", "pass_outcome"]):
#             logger.warning(f"Required columns missing for pass completion heatmap {player_id}/{season}")
#             return jsonify({"error": "Required columns for pass completion missing"}), 400

#         df_passes["location_eval"] = df_passes["location"].apply(safe_literal_eval)
#         df_valid_loc = df_passes[df_passes["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)].copy()

#         if df_valid_loc.empty:
#             logger.warning(f"No valid pass location data for pass completion heatmap {player_id}/{season}")
#             return jsonify({"error": "No valid pass location data"}), 404

#         df_valid_loc["x"] = df_valid_loc["location_eval"].apply(lambda loc: loc[0])
#         df_valid_loc["y"] = df_valid_loc["location_eval"].apply(lambda loc: loc[1])
#         df_valid_loc["completed"] = df_valid_loc["pass_outcome"].isna() 

#         pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='white')
#         fig, ax = pitch.draw(figsize=(4.125, 6))
#         fig.set_facecolor('#22312b')

#         bin_statistic = pitch.bin_statistic_positional(df_valid_loc.x, df_valid_loc.y, values=df_valid_loc.completed, statistic='mean', positional='full')

#         for section_data in bin_statistic:
#             if 'statistic' in section_data and isinstance(section_data['statistic'], np.ndarray):
#                 section_data['statistic'] = np.nan_to_num(section_data['statistic'], nan=0.0)
#             elif 'statistic' not in section_data or section_data['statistic'] is None : 
#                 if 'x_grid' in section_data and 'y_grid' in section_data and section_data['x_grid'] is not None and section_data['y_grid'] is not None:
#                     section_data['statistic'] = np.zeros((section_data['y_grid'].shape[0]-1, section_data['x_grid'].shape[1]-1), dtype=float)
#                 else:
#                     logger.warning(f"Missing grid info for a section in pass completion heatmap for {player_id}/{season}, section: {section_data.get('pos_section')}")
#                     section_data['statistic'] = np.array([[0.0]])


#         pitch.heatmap_positional(bin_statistic, ax=ax, cmap='Blues', edgecolors='#22312b', vmin=0, vmax=1)
#         path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')]
#         pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)

#         # plt.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
#         fig.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
#         plt.close(fig)
#         return jsonify({"image_url": image_url})
#     except Exception as e:
#         logger.error(f"Error in /pass_completion_heatmap for {player_id}/{season}: {e}", exc_info=True)
#         return jsonify({"error": f"Failed to generate pass completion heatmap: {str(e)}"}), 500

# @app.route("/pass_completion_heatmap")
# def pass_completion_heatmap_route():
#     return jsonify({"error": "Heatmap generation is temporarily disabled in production."}), 503

# @app.route("/position_heatmap")
# def position_heatmap_route():
#     return jsonify({"error": "Heatmap generation is temporarily disabled in production."}), 503

# @app.route("/pressure_heatmap")
# def pressure_heatmap_route():
#     return jsonify({"error": "Heatmap generation is temporarily disabled in production."}), 503

@app.route("/pass_completion_heatmap")
def pass_completion_heatmap_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"error": "No data found for this player/season"}), 404
        
        df_passes = df[df.get("type") == "Pass"].copy()
        if df_passes.empty or not all(c in df_passes.columns for c in ["location", "pass_outcome"]):
            return jsonify({"error": "Required pass columns are missing"}), 400

        df_passes["location_eval"] = df_passes["location"].apply(safe_literal_eval)
        df_valid_loc = df_passes[df_passes["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)].copy()
        if df_valid_loc.empty: return jsonify({"error": "No valid pass location data found"}), 404

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
            elif 'statistic' not in section_data or section_data['statistic'] is None : 
                if 'x_grid' in section_data and 'y_grid' in section_data and section_data['x_grid'] is not None and section_data['y_grid'] is not None:
                    section_data['statistic'] = np.zeros((section_data['y_grid'].shape[0]-1, section_data['x_grid'].shape[1]-1), dtype=float)
                else:
                    logger.warning(f"Missing grid info for a section in pass completion heatmap for {player_id}/{season}, section: {section_data.get('pos_section')}")
                    section_data['statistic'] = np.array([[0.0]])

        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='Blues', edgecolors='#22312b', vmin=0, vmax=1)
        path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')]
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)
        
        img_io = BytesIO()
        fig.savefig(img_io, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        img_io.seek(0)
        plt.close(fig)
        
        return send_file(img_io, mimetype='image/png')
        
    except Exception as e:
        logger.error(f"Error in /pass_completion_heatmap: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/position_heatmap")
def position_heatmap_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty or "location" not in df.columns:
            return jsonify({"error": "No data or location column missing for heatmap"}), 404
        
        df["location_eval"] = df["location"].apply(safe_literal_eval)
        df_valid_loc = df[df["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)].copy()
        if df_valid_loc.empty: return jsonify({"error": "No valid location data for heatmap"}), 404

        df_valid_loc["x"] = df_valid_loc["location_eval"].apply(lambda loc: loc[0])
        df_valid_loc["y"] = df_valid_loc["location_eval"].apply(lambda loc: loc[1])
        
        pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='white')
        fig, ax = pitch.draw(figsize=(4.125, 6))
        fig.set_facecolor('#22312b')
        
        bin_statistic = pitch.bin_statistic_positional(df_valid_loc.x, df_valid_loc.y, statistic='count', positional='full', normalize=True)
        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='coolwarm', edgecolors='#22312b')
        path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')]
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)

        img_io = BytesIO()
        fig.savefig(img_io, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        img_io.seek(0)
        plt.close(fig)
        
        return send_file(img_io, mimetype='image/png')
        
    except Exception as e:
        logger.error(f"Error generating position heatmap for {player_id}/{season}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate position heatmap: {str(e)}"}), 500

@app.route("/pressure_heatmap")
def pressure_heatmap_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df_events = load_player_data(player_id, season, DATA_DIR)
        df_pressure = pd.DataFrame()
        if df_events is not None and 'type' in df_events.columns:
            df_pressure = df_events[df_events["type"] == "Pressure"].copy()

        df_valid_loc = pd.DataFrame({"x": [], "y": []}) 
        if not df_pressure.empty and "location" in df_pressure.columns:
            df_pressure["location_eval"] = df_pressure["location"].apply(safe_literal_eval)
            temp_df_valid_loc = df_pressure[df_pressure["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)].copy()
            if not temp_df_valid_loc.empty:
                df_valid_loc["x"] = temp_df_valid_loc["location_eval"].apply(lambda loc: loc[0])
                df_valid_loc["y"] = temp_df_valid_loc["location_eval"].apply(lambda loc: loc[1])
        
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
        
        img_io = BytesIO()
        fig.savefig(img_io, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        img_io.seek(0)
        plt.close(fig)
        
        return send_file(img_io, mimetype='image/png')
        
    except Exception as e:
        logger.error(f"Error generating pressure heatmap for {player_id}/{season}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate pressure heatmap: {str(e)}"}), 500


@app.route("/pass_map_zona_stats")
def pass_map_zona_stats_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"zonas": []})

        passes_df = df[df.get("type") == "Pass"].copy() if "type" in df.columns else pd.DataFrame()
        if passes_df.empty or 'pass_end_location' not in passes_df.columns:
             return jsonify({"zonas": []})

        passes_df["end_loc_eval"] = passes_df["pass_end_location"].apply(safe_literal_eval)
        passes_df = passes_df[passes_df["end_loc_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)]
        if passes_df.empty: return jsonify({"zonas": []})

        def get_pitch_third(x_coord):
            if x_coord < 40: return "Defensive Third" 
            elif x_coord < 80: return "Middle Third"
            else: return "Attacking Third"

        def get_pitch_channel(y_coord):
            if y_coord < 26.67: return "Left Channel"
            elif y_coord < 53.33: return "Central Channel"
            else: return "Right Channel"

        passes_df["end_third"] = passes_df["end_loc_eval"].apply(lambda loc: get_pitch_third(loc[0]))
        passes_df["end_channel"] = passes_df["end_loc_eval"].apply(lambda loc: get_pitch_channel(loc[1]))
        passes_df["zona"] = passes_df["end_third"] + " - " + passes_df["end_channel"]

        zonas_data = []
        for zona_name, group in passes_df.groupby("zona"):
            total_passes = len(group)
            completed_passes = group["pass_outcome"].isna().sum()
            completion_pct = (completed_passes / total_passes * 100) if total_passes > 0 else 0.0
            zonas_data.append({
                "name": zona_name,
                "total_passes": int(total_passes),
                "completed_passes": int(completed_passes),
                "completion_pct": round(completion_pct, 1)
            })
        zonas_data = sorted(zonas_data, key=lambda z: z["name"])
        return jsonify({"zonas": zonas_data})
    except Exception as e:
        logger.error(f"Error in /pass_map_zona_stats for {player_id}/{season}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/shot_map")
def shot_map_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    try:
        if not player_id or not season:
            return jsonify({"shots": []})
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"shots": []})

        df_shots = df[df.get("type") == "Shot"].copy() if "type" in df.columns else pd.DataFrame()

        if df_shots.empty or not all(c in df_shots.columns for c in ["location"]):
            return jsonify({"shots": []})

        df_shots["location_eval"] = df_shots["location"].apply(safe_literal_eval)
        df_shots = df_shots[df_shots["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)]
        if df_shots.empty: return jsonify({"shots": []})

        df_shots["x"] = df_shots["location_eval"].apply(lambda loc: loc[0])
        df_shots["y"] = df_shots["location_eval"].apply(lambda loc: loc[1])

        if 'shot_outcome' in df_shots.columns:
            df_shots["is_goal"] = df_shots["shot_outcome"].astype(str) == "Goal"
        else:
            df_shots["is_goal"] = False

        shot_data = []
        for _, row in df_shots.iterrows():
            shot_data.append({
                "x": row["x"],
                "y": row["y"],
                "xg": safe_float(row.get("shot_statsbomb_xg", 0.0)),
                "goal": bool(row["is_goal"])
            })
        return jsonify({"shots": shot_data})
    except Exception as e:
        logger.error(f"Error in /shot_map for {player_id}/{season}: {e}", exc_info=True)
        return jsonify({"shots": [], "error": str(e)})


@app.route("/api/custom_model/available_kpis")
def available_kpis_for_custom_model():
    try:
        kpi_definitions_from_trainer = get_trainer_kpi_definitions_for_weight_derivation()
        structured_kpis_for_frontend, all_technical_names = structure_kpis_for_frontend(kpi_definitions_from_trainer)
        
        return jsonify({
            "structured_kpis": structured_kpis_for_frontend,
            "selectable_kpis_flat": all_technical_names, 
            "default_kpi_definitions_for_target": kpi_definitions_from_trainer 
            })
    except Exception as e:
        logger.error(f"Error fetching available KPIs for custom model: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/custom_model/build", methods=['POST'])
def handle_build_custom_model():
    data = request.get_json()
    if not data: return jsonify({"error": "Missing JSON payload"}), 400

    position_group = data.get("position_group")
    user_impact_kpis_list = data.get("impact_kpis")
    user_target_kpis_list = data.get("target_kpis")
    custom_model_name_prefix = data.get("model_name", f"custom_{position_group.lower() if position_group else 'model'}")
    
    user_ml_feature_selection = data.get("ml_features", None)

    if not all([position_group, user_impact_kpis_list, user_target_kpis_list]):
        return jsonify({"error": "Missing required fields: position_group, impact_kpis (for correlation), target_kpis (for weighting)"}), 400
    if position_group not in ["Attacker", "Midfielder", "Defender"]:
        return jsonify({"error": f"Invalid position_group: {position_group}"}), 400
    
    if user_ml_feature_selection is not None and not (isinstance(user_ml_feature_selection, list) and all(isinstance(item, str) for item in user_ml_feature_selection)):
        return jsonify({"error": "Invalid format for ml_features. Must be a list of strings."}), 400


    custom_model_id = f"{custom_model_name_prefix.replace(' ', '_').replace('-', '_')}_{uuid.uuid4().hex[:6]}"

    user_impact_kpis_config = {position_group: user_impact_kpis_list}
    user_target_kpis_for_weight_derivation_config = {position_group: user_target_kpis_list}

    try:
        success, message = build_and_train_model_from_script_logic(
            custom_model_id=custom_model_id,
            position_group_to_train=position_group,
            user_composite_impact_kpis=user_impact_kpis_config,
            user_kpi_definitions_for_weight_derivation=user_target_kpis_for_weight_derivation_config,
            user_ml_feature_subset=user_ml_feature_selection,
            base_output_dir_for_custom_model=CUSTOM_MODELS_DIR
        )
        if success:
            return jsonify({"message": message, "custom_model_id": custom_model_id}), 201
        else:
            return jsonify({"error": message}), 500
    except Exception as e:
        logger.error(f"Error building custom model '{custom_model_id}': {e}", exc_info=True)
        return jsonify({"error": f"Internal server error during custom model build: {str(e)}"}), 500


@app.route("/api/custom_model/list")
def list_custom_models():
    custom_models_list = []
    if not os.path.exists(CUSTOM_MODELS_DIR):
        return jsonify({"custom_models": []})
    for model_id_folder in os.listdir(CUSTOM_MODELS_DIR):
        model_folder_path = os.path.join(CUSTOM_MODELS_DIR, model_id_folder)
        if os.path.isdir(model_folder_path):
            for pos_group_folder_name in os.listdir(model_folder_path): 
                pos_group_folder_path = os.path.join(model_folder_path, pos_group_folder_name)
                if os.path.isdir(pos_group_folder_path):
                    config_file_name = f"model_config_{pos_group_folder_name.lower()}_{model_id_folder}.json"
                    config_path = os.path.join(pos_group_folder_path, config_file_name)
                    if os.path.exists(config_path):
                        try:
                            with open(config_path, 'r') as f_cfg: cfg = json.load(f_cfg)
                            custom_models_list.append({
                                "id": model_id_folder,
                                "name": cfg.get("model_type", f"{model_id_folder} ({pos_group_folder_name.capitalize()})"),
                                "position_group": cfg.get("position_group_trained_for", pos_group_folder_name.capitalize()),
                                "description": cfg.get("description", "Custom Potential Model")
                            })
                        except Exception as e:
                            logger.error(f"Error reading config {config_path}: {e}")
                            custom_models_list.append({"id": model_id_folder, "name": f"{model_id_folder} ({pos_group_folder_name.capitalize()}) - Config Error", "position_group": pos_group_folder_name.capitalize(), "description": "Config Error"})
    return jsonify({"custom_models": custom_models_list})


@app.route("/scouting_predict")
def scouting_predict():
    player_id_str = request.args.get("player_id")
    season_to_predict_for = request.args.get("season")
    model_identifier = request.args.get("model_id", "default_v14") 

    if not player_id_str or not season_to_predict_for:
        return jsonify({"error": "Missing player_id or season"}), 400

    try:
        player_metadata = next((p_data for p_name, p_data in player_index_main_data.items() if isinstance(p_data, dict) and str(p_data.get("player_id")) == player_id_str), None)
        player_name_from_index = next((p_name for p_name, p_data in player_index_main_data.items() if isinstance(p_data, dict) and str(p_data.get("player_id")) == player_id_str), "N/A")

        if not player_metadata: return jsonify({"error": f"Player metadata not found for ID {player_id_str}"}), 404

        primary_pos_str = player_metadata.get("position", "Unknown")
        position_group_for_prediction = trainer_get_general_position(primary_pos_str)
        if position_group_for_prediction not in ["Attacker", "Midfielder", "Defender"]:
             return jsonify({"error": f"Prediction not supported for position group: {position_group_for_prediction}"}), 400

        dob = player_metadata.get("dob")
        if not dob: return jsonify({"error": "Player DOB not found"}), 400
        age_at_season = get_age_at_fixed_point_in_season(dob, season_to_predict_for)
        if age_at_season is None: return jsonify({"error": "Could not calculate age"}), 400

        model_to_load = None; scaler_to_load = None; expected_ml_feature_names_for_model = []
        effective_model_id_for_path = model_identifier
        model_base_path_to_use = "" 
        is_custom_model = True 

        if model_identifier == "default_v14":
            effective_model_id_for_path = "peak_potential_v2_15_16"
            is_custom_model = False 
            model_pos_dir = os.path.join(V14_MODEL_BASE_DIR, position_group_for_prediction.lower())
            model_base_path_to_use = V14_MODEL_BASE_DIR 
        else:
            model_base_path_to_use = CUSTOM_MODELS_DIR
            model_pos_dir = os.path.join(model_base_path_to_use, effective_model_id_for_path, position_group_for_prediction.lower())
        
        logger.info(f"Loading model. Requested: {model_identifier}, Effective ID for filename: {effective_model_id_for_path}, Final Model Dir: {model_pos_dir}, Position: {position_group_for_prediction}")
        
        if not os.path.isdir(model_pos_dir):
            logger.error(f"Model directory not found: {model_pos_dir}")
            return jsonify({"error": f"Model directory not found for ID {effective_model_id_for_path}, Pos {position_group_for_prediction}"}), 404

        model_file_name_suffix = f"_{effective_model_id_for_path}"
        
        model_file = os.path.join(model_pos_dir, f"potential_model_{position_group_for_prediction.lower()}{model_file_name_suffix}.joblib")
        scaler_file = os.path.join(model_pos_dir, f"feature_scaler_{position_group_for_prediction.lower()}{model_file_name_suffix}.joblib")
        config_file = os.path.join(model_pos_dir, f"model_config_{position_group_for_prediction.lower()}{model_file_name_suffix}.json")

        # if not all(os.path.exists(p) for p in [model_file, scaler_file, config_file]):
        #     logger.error(f"Missing files for model {effective_model_id_for_path}, Pos {position_group_for_prediction}.")
        #     logger.error(f"  Checked model: {model_file}")
        #     logger.error(f"  Checked scaler: {scaler_file}")
        #     logger.error(f"  Checked config: {config_file}")
        #     return jsonify({"error": f"Missing files for model ID {effective_model_id_for_path}, Pos {position_group_for_prediction}"}), 404
        
        # model_to_load = joblib.load(model_file); scaler_to_load = joblib.load(scaler_file)
        # with open(config_file, 'r') as f_cfg: model_cfg = json.load(f_cfg)
        # expected_ml_feature_names_for_model = model_cfg.get("features_used_for_ml_model", [])
        # if not expected_ml_feature_names_for_model: return jsonify({"error": f"Feature list missing in config for model {effective_model_id_for_path}"}), 500

        # NUEVO BLOQUE PARA PEGAR EN SU LUGAR

        model_key = f"ml_models/ml_model_files_peak_potential/{effective_model_id_for_path}/{position_group_for_prediction.lower()}/potential_model_{position_group_for_prediction.lower()}{model_file_name_suffix}.joblib"
        scaler_key = f"ml_models/ml_model_files_peak_potential/{effective_model_id_for_path}/{position_group_for_prediction.lower()}/feature_scaler_{position_group_for_prediction.lower()}{model_file_name_suffix}.joblib"
        config_key = f"ml_models/ml_model_files_peak_potential/{effective_model_id_for_path}/{position_group_for_prediction.lower()}/model_config_{position_group_for_prediction.lower()}{model_file_name_suffix}.json"

        try:
            if not s3_client:
                return jsonify({"error": "S3 client not initialized. Check server configuration."}), 500
                
            # Cargar modelo
            logger.info(f"Loading model from R2: {model_key}")
            with BytesIO() as f_model:
                s3_client.download_fileobj(Bucket=R2_BUCKET_NAME, Key=model_key, Fileobj=f_model)
                f_model.seek(0)
                model_to_load = joblib.load(f_model)

            # Cargar scaler
            logger.info(f"Loading scaler from R2: {scaler_key}")
            with BytesIO() as f_scaler:
                s3_client.download_fileobj(Bucket=R2_BUCKET_NAME, Key=scaler_key, Fileobj=f_scaler)
                f_scaler.seek(0)
                scaler_to_load = joblib.load(f_scaler)

            # Cargar config
            logger.info(f"Loading config from R2: {config_key}")
            response_cfg = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=config_key)
            config_content = response_cfg['Body'].read().decode('utf-8')
            model_cfg = json.loads(config_content)
            
            expected_ml_feature_names_for_model = model_cfg.get("features_used_for_ml_model", [])
            if not expected_ml_feature_names_for_model:
                return jsonify({"error": f"Feature list missing in config for model {effective_model_id_for_path}"}), 500

        except Exception as e:
            logger.error(f"Failed to load model files from R2 for {model_identifier}. Keys: {model_key}, {scaler_key}, {config_key}. Error: {e}", exc_info=True)
            return jsonify({"error": f"Could not load model files from cloud storage for {model_identifier}."}), 500

        # FIN DEL NUEVO BLOQUE

        player_seasons_all = player_metadata.get("seasons", [])
        if not player_seasons_all: return jsonify({"error": "No seasons for player"}), 404
        
        df_all_base_features_for_player_list_pred = []
        try:
            # minutes_df_global = pd.read_csv(PLAYER_MINUTES_PATH)
            minutes_df_global = pd.DataFrame()
            if s3_client:
                try:
                    response_minutes = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key="data/player_season_minutes_with_names.csv")
                    minutes_content = response_minutes['Body'].read().decode('utf-8')
                    minutes_df_global = pd.read_csv(StringIO(minutes_content))
                except Exception as e:
                    logger.error(f"Error loading player_season_minutes_with_names.csv from R2: {e}")
                    return jsonify({"error": "Could not load essential minutes data from cloud storage."}), 500
            minutes_df_global['season_name_std'] = minutes_df_global['season_name'].str.replace('/', '_', regex=False)
        except FileNotFoundError:
            logger.error(f"Player minutes file '{PLAYER_MINUTES_PATH}' not found for prediction.")
            return jsonify({"error": f"Player minutes file not found."}), 500

        target_s_numeric_pred = int(season_to_predict_for.split('_')[0])
        all_base_metric_names_from_trainer = trainer_get_feature_names()

        for s_hist_or_current_pred in sorted(player_seasons_all):
            s_numeric_hist_pred = int(s_hist_or_current_pred.split('_')[0])
            if s_numeric_hist_pred > target_s_numeric_pred: continue 
            
            age_for_this_s_pred = get_age_at_fixed_point_in_season(dob, s_hist_or_current_pred)
            if age_for_this_s_pred is None: continue
            if age_for_this_s_pred > 21 and s_hist_or_current_pred != season_to_predict_for :
                 continue

            player_minutes_row_hist_pred = minutes_df_global[(minutes_df_global['player_id'].astype(str) == player_id_str) & (minutes_df_global['season_name_std'] == s_hist_or_current_pred)]
            total_minutes_hist_pred = player_minutes_row_hist_pred['total_minutes_played'].iloc[0] if not player_minutes_row_hist_pred.empty else 0.0
            num_90s_hist_pred = trainer_safe_division(total_minutes_hist_pred, 90.0)
            
            df_events_hist_pred = load_player_data(player_id_str, s_hist_or_current_pred, DATA_DIR) 
            if df_events_hist_pred is None: df_events_hist_pred = pd.DataFrame()

            base_features_for_s_hist_pred = trainer_extract_base_features(df_events_hist_pred, age_for_this_s_pred, s_numeric_hist_pred, num_90s_hist_pred)
            
            base_features_for_s_hist_pred['player_id_identifier'] = player_id_str
            base_features_for_s_hist_pred['target_season_identifier'] = s_hist_or_current_pred 
            base_features_for_s_hist_pred['season_numeric'] = s_numeric_hist_pred
            base_features_for_s_hist_pred['general_position_identifier'] = trainer_get_general_position(primary_pos_str)
            df_all_base_features_for_player_list_pred.append(base_features_for_s_hist_pred)

        if not df_all_base_features_for_player_list_pred: 
            return jsonify({"error": "Insufficient historical/current data for base feature extraction."}), 404
        
        df_all_base_features_for_player_df_pred = pd.DataFrame(df_all_base_features_for_player_list_pred).fillna(0.0)
        
        current_season_data_row_for_ml = df_all_base_features_for_player_df_pred[
            df_all_base_features_for_player_df_pred['target_season_identifier'] == season_to_predict_for
        ]
        if current_season_data_row_for_ml.empty:
            return jsonify({"error": f"Base features for target season {season_to_predict_for} not found after extraction."}), 404
        current_season_data_row_for_ml = current_season_data_row_for_ml.iloc[0]

        historical_df_for_ml = df_all_base_features_for_player_df_pred[
            df_all_base_features_for_player_df_pred['season_numeric'] < target_s_numeric_pred
        ].sort_values(by='season_numeric') 

        ml_features_series_pred = trainer_construct_ml_features_for_player_season(
            current_season_base_features_row=current_season_data_row_for_ml,
            historical_base_features_df=historical_df_for_ml,
            all_base_metric_names=all_base_metric_names_from_trainer
        )

        if ml_features_series_pred is None or ml_features_series_pred.empty:
            return jsonify({"error": "Failed to construct ML features using trainer's logic."}), 500

        features_for_scaling_df_pred = pd.DataFrame([ml_features_series_pred])
        aligned_features_df_pred = pd.DataFrame(columns=expected_ml_feature_names_for_model)
        
        missing_features_in_generation = []
        for col in expected_ml_feature_names_for_model:
            if col in features_for_scaling_df_pred.columns: 
                aligned_features_df_pred[col] = features_for_scaling_df_pred[col]
            else: 
                missing_features_in_generation.append(col)
                aligned_features_df_pred[col] = 0.0 
        
        if missing_features_in_generation:
            logger.warning(f"ML features expected by model but not generated by trainer's logic for prediction ({len(missing_features_in_generation)} missing): {missing_features_in_generation[:5]}...")

        aligned_features_df_pred = aligned_features_df_pred.fillna(0.0)

        scaled_features_array_pred = scaler_to_load.transform(aligned_features_df_pred)
        predicted_potential_score_raw_pred = model_to_load.predict(scaled_features_array_pred)[0]
        final_predicted_score = min(200.0, max(0.0, float(predicted_potential_score_raw_pred)))

        num_90s_target_season_pred_row = minutes_df_global[(minutes_df_global['player_id'].astype(str) == player_id_str) & (minutes_df_global['season_name_std'] == season_to_predict_for)]
        num_90s_target_season_pred = trainer_safe_division(num_90s_target_season_pred_row['total_minutes_played'].iloc[0], 90.0) if not num_90s_target_season_pred_row.empty else 0.0

        return jsonify({
            "player_id": player_id_str, "player_name": player_name_from_index,
            "season_predicted_from": season_to_predict_for,
            "age_at_season_start_of_year": age_at_season, "position_group": position_group_for_prediction,
            "predicted_potential_score": round(final_predicted_score, 2),
            "num_90s_played_in_season": round(num_90s_target_season_pred, 2),
            "model_used": model_identifier,
            "debug_num_ml_features_generated_for_pred": len(ml_features_series_pred) if ml_features_series_pred is not None else 0,
            "debug_num_ml_features_expected_by_model": len(expected_ml_feature_names_for_model)
        })

    except FileNotFoundError as e: return jsonify({"error": f"File not found for prediction: {e.filename}"}), 500
    except Exception as e:
        logger.error(f"Error in /scouting_predict (model: {model_identifier}): {e}", exc_info=True)
        return jsonify({"error": f"Unexpected error during prediction: {str(e)}"}), 500

@app.route("/api/custom_model/available_ml_features")
def available_ml_features_for_custom_model():
    try:
        ml_feature_names = get_trainer_all_possible_ml_feature_names()
        return jsonify({"available_ml_features": ml_feature_names})
    except Exception as e:
        logger.error(f"Error fetching available ML features: {e}", exc_info=True)
        return jsonify({"error": str(e), "available_ml_features": []}), 500

@app.route("/api/player/<player_id>/goalkeeper/analysis/<season>")
def goalkeeper_analysis_route(player_id, season):
    """Serves comprehensive GK analysis including stats and chart data."""
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df_player = load_player_data(player_id, season, DATA_DIR)
        analysis_results = _calculate_goalkeeper_metrics(df_player, player_id)

        if analysis_results.get("error"):
            logger.warning(f"GK Analysis for {player_id}/{season} resulted in error: {analysis_results.get('error')}")
            return jsonify(analysis_results), 404
        return jsonify(analysis_results)
    except Exception as e:
        logger.error(f"Exception in goalkeeper_analysis_route for {player_id}, {season}: {e}", exc_info=True)
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500

@app.route("/pass_map_plot")
def pass_map_plot_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    try:
        if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"passes": []})

        df_passes = df[df.get("type") == "Pass"].copy() if "type" in df.columns else pd.DataFrame()
        if df_passes.empty or not all(c in df_passes.columns for c in ["location", "pass_end_location"]):
            return jsonify({"passes": []})

        df_passes["location_eval"] = df_passes["location"].apply(safe_literal_eval)
        df_passes["pass_end_location_eval"] = df_passes["pass_end_location"].apply(safe_literal_eval)
        df_passes.dropna(subset=["location_eval", "pass_end_location_eval"], inplace=True)

        df_passes = df_passes[
            df_passes["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2) &
            df_passes["pass_end_location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)
        ]

        pass_data = []
        for _, row in df_passes.iterrows():
            loc = row["location_eval"]
            end_loc = row["pass_end_location_eval"]
            outcome = row.get("pass_outcome")
            assist_flag = row.get("pass_goal_assist", False)

            pass_data.append({
                "start_x": loc[0], "start_y": loc[1],
                "end_x": end_loc[0], "end_y": end_loc[1],
                "completed": pd.isna(outcome),
                "assist": str(assist_flag).lower() == 'true',
                "final_third": end_loc[0] > 80
            })
        return jsonify({"passes": pass_data})
    except Exception as e:
        logger.error(f"Error in /pass_map_plot for {player_id}/{season}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# @app.route("/position_heatmap")
# def position_heatmap_route():
#     player_id = request.args.get("player_id")
#     season = request.args.get("season")
#     if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
#     try:
#         player_dir = os.path.join(STATIC_IMG_DIR, str(player_id))
#         os.makedirs(player_dir, exist_ok=True)
#         image_filename = f"{str(player_id)}_{season}_pos_heatmap.png"
#         image_path = os.path.join(player_dir, image_filename)
#         image_url = f"/static/images/{str(player_id)}/{image_filename}"

#         df = load_player_data(player_id, season, DATA_DIR)
#         if df is None or df.empty or "location" not in df.columns:
#             logger.warning(f"No data or location column for position heatmap {player_id}/{season}")
#             return jsonify({"error": "No data or location column missing for heatmap"}), 404

#         df["location_eval"] = df["location"].apply(safe_literal_eval)
#         df_valid_loc = df[df["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)].copy()
#         if df_valid_loc.empty:
#             logger.warning(f"No valid location data for position heatmap {player_id}/{season}")
#             return jsonify({"error": "No valid location data for heatmap"}), 404

#         df_valid_loc["x"] = df_valid_loc["location_eval"].apply(lambda loc: loc[0])
#         df_valid_loc["y"] = df_valid_loc["location_eval"].apply(lambda loc: loc[1])

#         pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='white')
#         fig, ax = pitch.draw(figsize=(4.125, 6))
#         fig.set_facecolor('#22312b')

#         bin_statistic = pitch.bin_statistic_positional(df_valid_loc.x, df_valid_loc.y, statistic='count', positional='full', normalize=True)
#         pitch.heatmap_positional(bin_statistic, ax=ax, cmap='coolwarm', edgecolors='#22312b')
#         path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')]
#         pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)

#         # plt.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
#         fig.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
#         plt.close(fig)
#         return jsonify({"image_url": image_url})
#     except Exception as e:
#         logger.error(f"Error generating position heatmap for {player_id}/{season}: {e}", exc_info=True)
#         return jsonify({"error": f"Failed to generate position heatmap: {str(e)}"}), 500

# @app.route("/pressure_heatmap")
# def pressure_heatmap_route():
#     player_id = request.args.get("player_id")
#     season = request.args.get("season")
#     if not player_id or not season:
#         return jsonify({"image_url": None, "message": "Missing player_id or season"})
#     try:
#         player_dir = os.path.join(STATIC_IMG_DIR, str(player_id))
#         os.makedirs(player_dir, exist_ok=True)
#         image_filename = f"{str(player_id)}_{season}_pressure_heatmap.png"
#         image_path = os.path.join(player_dir, image_filename)
#         image_url = f"/static/images/{str(player_id)}/{image_filename}"

#         df_events = load_player_data(player_id, season, DATA_DIR)
#         df_pressure = pd.DataFrame()

#         if df_events is not None and not df_events.empty and 'type' in df_events.columns:
#             df_pressure = df_events[df_events["type"] == "Pressure"].copy()

#         df_valid_loc = pd.DataFrame({"x": [], "y": []}) 
#         if not df_pressure.empty and "location" in df_pressure.columns:
#             df_pressure["location_eval"] = df_pressure["location"].apply(safe_literal_eval)
#             temp_df_valid_loc = df_pressure[df_pressure["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)].copy()
#             if not temp_df_valid_loc.empty:
#                 df_valid_loc["x"] = temp_df_valid_loc["location_eval"].apply(lambda loc: loc[0])
#                 df_valid_loc["y"] = temp_df_valid_loc["location_eval"].apply(lambda loc: loc[1])

#         pitch = Pitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#000000', line_color='#efefef')
#         fig, ax = pitch.draw(figsize=(6.6, 4.125))
#         fig.set_facecolor('#000000')

#         if not df_valid_loc.empty and not df_valid_loc['x'].empty:
#             bin_statistic = pitch.bin_statistic(df_valid_loc.x, df_valid_loc.y, statistic='count', bins=(25, 25))
#             if 'statistic' in bin_statistic and np.any(bin_statistic['statistic']):
#                 bin_statistic['statistic'] = gaussian_filter(bin_statistic['statistic'], 1)
#                 pcm = pitch.heatmap(bin_statistic, ax=ax, cmap='hot', edgecolors='#000000')
#                 cbar = fig.colorbar(pcm, ax=ax, shrink=0.6)
#                 cbar.outline.set_edgecolor('#efefef')
#                 cbar.ax.yaxis.set_tick_params(color='#efefef')
#                 plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#efefef')

#         # plt.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
#         fig.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
#         plt.close(fig)
#         return jsonify({"image_url": image_url})
#     except Exception as e:
#         logger.error(f"Error generating pressure heatmap for {player_id}/{season}: {e}", exc_info=True)
#         return jsonify({"image_url": None, "error": f"Failed to generate pressure heatmap: {str(e)}"})


@app.route("/available_aggregated_metrics")
def available_aggregated_metrics_route():
    try:
        base_features = trainer_get_feature_names() 
        
        def format_base_feature_label(feature_name):
            label = feature_name
            label = label.replace("_p90_sqrt_", " P90 √")
            label = label.replace("_p90", " P90")
            label = label.replace("_sqrt_", " √")
            label = label.replace("_kpi", " KPI")
            label = label.replace("_inv_kpi_base", " (Inv. Base)")
            label = label.replace("count_", "Count of ")
            label = label.replace("sum_", "Sum of ")
            label = label.replace("_", " ")
            label = ' '.join(word.capitalize() for word in label.split(' '))
            return label

        formatted_metrics = [
            {"id": name, "label": format_base_feature_label(name)}
            for name in base_features
            if not name.startswith("player_") and \
               not name.startswith("target_season_") and \
               not name.startswith("general_position_") and \
               not name.startswith("matches_played_") and \
               not name == "season_numeric" 
        ]
        
        formatted_metrics.sort(key=lambda x: x["label"])
        
        return jsonify({"available_metrics": formatted_metrics})
    except Exception as e:
        logger.error(f"Error in /available_aggregated_metrics: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/player_seasonal_metric_trend")
def player_seasonal_metric_trend_route():
    player_id = request.args.get("player_id")
    metric_to_aggregate = request.args.get("metric") 

    if not player_id or not metric_to_aggregate:
        return jsonify({"error": "Missing player_id or metric"}), 400

    try:
        player_metadata = None
        if isinstance(player_index_main_data, dict):
            player_metadata = next((data for name, data in player_index_main_data.items() if str(data.get("player_id")) == player_id), None)
        elif isinstance(player_index_main_data, list):
            player_metadata = next((data for data in player_index_main_data if str(data.get("player_id")) == player_id), None)

        if not player_metadata:
            return jsonify({"error": "Player not found"}), 404

        player_seasons = sorted(player_metadata.get("seasons", []))
        if not player_seasons:
            return jsonify({"trend_data": [], "metric_label": metric_to_aggregate}), 200

        try:
            minutes_df_global = pd.read_csv(PLAYER_MINUTES_PATH)
            minutes_df_global['season_name_std'] = minutes_df_global['season_name'].str.replace('/', '_', regex=False)
        except FileNotFoundError:
            logger.error(f"Player minutes file '{PLAYER_MINUTES_PATH}' not found for trend.")
            return jsonify({"error": "Player minutes file not found."}), 500

        trend_data_list = []
        all_possible_base_features = trainer_get_feature_names() 

        if metric_to_aggregate not in all_possible_base_features:
            return jsonify({"error": f"Metric '{metric_to_aggregate}' is not a valid aggregatable metric."}), 400

        for season_str in player_seasons:
            player_minutes_row = minutes_df_global[
                (minutes_df_global['player_id'].astype(str) == player_id) & 
                (minutes_df_global['season_name_std'] == season_str)
            ]
            total_minutes = player_minutes_row['total_minutes_played'].iloc[0] if not player_minutes_row.empty else 0.0
            num_90s = trainer_safe_division(total_minutes, 90.0)
            
            dob = player_metadata.get("dob")
            age_at_season = 0 
            if dob:
                age_at_season = get_age_at_fixed_point_in_season(dob, season_str) or 0 
            
            season_numeric = int(season_str.split('_')[0]) 

            df_events_season = load_player_data(player_id, season_str, DATA_DIR)
            if df_events_season is None: df_events_season = pd.DataFrame()
            
            base_features_series = trainer_extract_base_features(
                df_events_season, 
                age_at_season, 
                season_numeric, 
                num_90s
            )
            
            metric_value = base_features_series.get(metric_to_aggregate, 0.0) 
            if pd.isna(metric_value):
                metric_value = 0.0
            
            trend_data_list.append({
                "season": season_str,
                "value": float(metric_value), 
                "metric_name": metric_to_aggregate 
            })
        
        metric_label_friendly = format_base_feature_label(metric_to_aggregate) 

        return jsonify({
            "trend_data": trend_data_list, 
            "metric_label": metric_label_friendly,
            "metric_id": metric_to_aggregate
        })

    except Exception as e:
        logger.error(f"Error in /player_seasonal_metric_trend for player {player_id}, metric {metric_to_aggregate}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def format_base_feature_label(feature_name):
    label = feature_name
    label = label.replace("_p90_sqrt_", " P90 √")
    label = label.replace("_p90", " P90")
    label = label.replace("_sqrt_", " √")
    label = label.replace("_kpi", " KPI")
    label = label.replace("_inv_kpi_base", " (Inv. Base)")
    label = label.replace("count_", "Count of ")
    label = label.replace("sum_", "Sum of ")
    label = label.replace("_", " ")
    label = ' '.join(word.capitalize() for word in label.split(' '))
    return label


@app.route("/player_single_season_aggregated_metric")
def player_single_season_aggregated_metric_route():
    player_id = request.args.get("player_id")
    season_str = request.args.get("season") 
    metric_to_aggregate = request.args.get("metric")

    if not all([player_id, season_str, metric_to_aggregate]):
        return jsonify({"error": "Missing player_id, season, or metric"}), 400

    if season_str == "all":
        return jsonify({"error": "This endpoint is for single seasons only. Use /player_seasonal_metric_trend for all seasons."}), 400

    try:
        player_metadata = None
        if isinstance(player_index_main_data, dict):
            player_metadata = next((data for name, data in player_index_main_data.items() if str(data.get("player_id")) == player_id), None)
        elif isinstance(player_index_main_data, list):
             player_metadata = next((data for data in player_index_main_data if str(data.get("player_id")) == player_id), None)


        if not player_metadata:
            return jsonify({"error": "Player not found"}), 404

        all_possible_base_features = trainer_get_feature_names()
        if metric_to_aggregate not in all_possible_base_features:
            return jsonify({"error": f"Metric '{metric_to_aggregate}' is not a valid aggregatable metric."}), 400

        try:
            minutes_df_global = pd.read_csv(PLAYER_MINUTES_PATH)
            minutes_df_global['season_name_std'] = minutes_df_global['season_name'].str.replace('/', '_', regex=False)
        except FileNotFoundError:
            logger.error(f"Player minutes file '{PLAYER_MINUTES_PATH}' not found.")
            return jsonify({"error": "Player minutes file not found."}), 500

        player_minutes_row = minutes_df_global[
            (minutes_df_global['player_id'].astype(str) == player_id) & 
            (minutes_df_global['season_name_std'] == season_str)
        ]
        total_minutes = player_minutes_row['total_minutes_played'].iloc[0] if not player_minutes_row.empty else 0.0
        num_90s = trainer_safe_division(total_minutes, 90.0)
        
        dob = player_metadata.get("dob")
        age_at_season = 0
        if dob:
            age_at_season = get_age_at_fixed_point_in_season(dob, season_str) or 0 
        
        try:
            season_numeric = int(season_str.split('_')[0])
        except ValueError:
            logger.error(f"Could not parse season_numeric from season_str: {season_str}")
            return jsonify({"error": f"Invalid season format: {season_str}"}), 400

        df_events_season = load_player_data(player_id, season_str, DATA_DIR)
        if df_events_season is None: 
            df_events_season = pd.DataFrame() 
        
        base_features_series = trainer_extract_base_features(
            df_events_season, 
            age_at_season, 
            season_numeric, 
            num_90s
        )
        
        metric_value = base_features_series.get(metric_to_aggregate, 0.0)
        if pd.isna(metric_value):
            metric_value = 0.0
        
        metric_label_friendly = format_base_feature_label(metric_to_aggregate)

        return jsonify({
            "season": season_str,
            "metric_id": metric_to_aggregate,
            "metric_label": metric_label_friendly,
            "value": float(metric_value)
        })

    except Exception as e:
        logger.error(f"Error in /player_single_season_aggregated_metric for player {player_id}, season {season_str}, metric {metric_to_aggregate}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# --- Flask App Finalization ---
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    app.run(debug=True)