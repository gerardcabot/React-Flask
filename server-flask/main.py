from flask import Flask, jsonify, request, send_file, redirect, redirect
import os
import pandas as pd
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
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
import gc
import math
import requests
 

from model_trainer.trainer_v2 import (
    build_and_train_model_from_script_logic,
    get_trainer_kpi_definitions_for_weight_derivation,
    get_trainer_composite_impact_kpis_definitions,
    get_general_position as trainer_get_general_position, 
    get_feature_names_for_extraction as trainer_get_feature_names,
    extract_season_features as trainer_extract_base_features,
    trainer_construct_ml_features_for_player_season, 
    safe_division as trainer_safe_division, 
    get_trainer_all_possible_ml_feature_names 
)

from validation_schemas import (
    CustomModelTrainingSchema,
    PredictionRequestSchema,
    PlayerQuerySchema,
    MetricQuerySchema,
    validate_request_data
)


R2_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO_OWNER = os.environ.get('GITHUB_REPO_OWNER', 'gerardcabot')
GITHUB_REPO_NAME = os.environ.get('GITHUB_REPO_NAME', 'React-Flask')
  

s3_client = None
if R2_ENDPOINT_URL and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME:
    logger.info("R2 environment variables found. Initializing S3 client.")
    s3_client = boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name='auto'
    )
else:
    logger.warning("R2 environment variables not set. S3 client not initialized. App will likely fail.")



BASE_DIR_SERVER_FLASK = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "..", "data")

V14_MODEL_BASE_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "..", "ml_models", "ml_model_files_peak_potential", "peak_potential_v2_15_16")

PLAYER_MINUTES_PATH = os.path.join(DATA_DIR, "player_season_minutes_with_names.csv")

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

def load_translation(lang_code):
    """
    Carrega el fitxer de traducció amb missatges de depuració detallats.
    """
    lang = lang_code.split('-')[0].lower()
    
    logger.info("--- Iniciant càrrega de traducció ---")
    logger.info(f"Codi d'idioma rebut: '{lang_code}', normalitzat a: '{lang}'")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    translations_dir = os.path.join(base_dir, 'translations')
    file_path = os.path.join(translations_dir, f"{lang}.json")
    
    logger.info(f"Ruta absoluta construïda per al fitxer: '{file_path}'")
    logger.info(f"El fitxer existeix? -> {os.path.exists(file_path)}")

    if not os.path.exists(file_path):
        logger.warning(f"No s'ha trobat el fitxer per a '{lang}'. Es farà servir 'ca.json' com a alternativa.")
        file_path = os.path.join(translations_dir, "ca.json")

    if not os.path.exists(file_path):
        logger.error(f"CRÍTIC: Tampoc s'ha trobat el fitxer per defecte 'ca.json' a '{file_path}'.")
        raise FileNotFoundError("Els fitxers de traducció no existeixen al servidor.")

    with open(file_path, 'r', encoding='utf-8') as f:
        logger.info(f"S'ha carregat correctament el fitxer: '{file_path}'")
        logger.info("------------------------------------")
        return json.load(f)

def load_player_data(player_id, season, data_dir): 
    def try_load_one_from_r2(player_id, season):
        if not s3_client:
            logger.error("Cannot load from R2: S3 client not initialized.")
            return None
            
        file_key_csv = f"data/{season}/players/{player_id}_{season}.csv"
        
        try:
            logger.debug(f"Attempting to load from R2: {R2_BUCKET_NAME}/{file_key_csv}")
            response = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=file_key_csv)
            
            csv_content = response['Body'].read().decode('utf-8')
            df = pd.read_csv(StringIO(csv_content), low_memory=False)

            loc_cols = [col for col in df.columns if 'location' in col or 'end_location' in col]
            for col in loc_cols:
                if col in df.columns: df[col] = df[col].apply(lambda x: safe_literal_eval(x) if pd.notna(x) else None)
            
            bool_cols_to_check = [
                'counterpress', 'offensive', 'recovery_failure', 'deflection', 'save_block', 'aerial_won', 'nutmeg', 'overrun',
                'no_touch', 'leads_to_shot', 'advantage', 'penalty', 'defensive', 'backheel', 'deflected', 'miscommunication',
                'cross', 'cut_back', 'switch', 'shot_assist', 'pass_goal_assist', 'follows_dribble', 'first_time', 'open_goal',
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
        except Exception as e:
            if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchKey':
                    logger.warning(f"R2 object not found: {R2_BUCKET_NAME}/{file_key_csv}")
            return None
        except Exception as e:
            logger.error(f"Error loading {file_key_csv} from R2: {e}", exc_info=True)
            return None


    if season == "all":
        logger.warning("Loading 'all' seasons is not fully supported in production environment. Returning empty DataFrame.")
        return pd.DataFrame()
    else:
        return try_load_one_from_r2(player_id, season)

app = Flask(__name__, static_folder=os.path.join(BASE_DIR_SERVER_FLASK, 'static'), static_url_path='/static')
CORS(app, resources={
    r"/*": {
        "origins": ["https://react-flask-psi.vercel.app", "http://localhost:5173", "http://localhost:5174"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "200 per hour"], 
    storage_uri="memory://"  
)


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
            label_suffix = " (per 90 min, sqrt)"
        elif kpi_name.endswith("_sqrt_"):
            base_name = kpi_name.replace("_sqrt_", "")
            variant_type = "sqrt"
            label_suffix = " (sqrt)"
        elif kpi_name.endswith("_p90"):
            base_name = kpi_name.replace("_p90", "")
            variant_type = "p90"
            label_suffix = " (per 90 min)"
        elif kpi_name.endswith("_kpi"):
            base_name = kpi_name.replace("_kpi", "")
            variant_type = "direct_kpi"
            label_suffix = ""
        elif kpi_name.endswith("_base") and "_inv_kpi_base" in kpi_name: 
            base_name = kpi_name.replace("_p90_inv_kpi_base", "").replace("_", " ").strip()
            if not base_name:
                base_name = "turnovers"
            variant_type = "p90_inv_base"
            label_suffix = " (p90, inv, base)"
        else:
            base_name = kpi_name
            variant_type = "total"
            label_suffix = ""

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

@app.route("/health")
@limiter.exempt
def health_check():
    """
    Lightweight health check endpoint for uptime monitoring.
    Returns immediately without loading any data or performing heavy operations.
    """
    return jsonify({
        "status": "healthy",
        "service": "Football Stats API",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }), 200


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
            {
                "name": name, 
                "player_id": data["player_id"], 
                "seasons": data.get("seasons", []), 
                "dob": data.get("dob", ""),
                "position": data.get("position", "")
            }
            for name, data in sorted(player_index_main_data.items()) if isinstance(data, dict) and "player_id" in data
        ])
    except Exception as e: 
        logger.error(f"Error in /players: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

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


@app.route("/pass_completion_heatmap")
@limiter.limit("30 per minute") 
def pass_completion_heatmap_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400

    public_r2_url = os.environ.get('R2_PUBLIC_URL')
    if not public_r2_url:
        return jsonify({"error": "Server is not configured with R2_PUBLIC_URL"}), 500

    image_filename = f"{player_id}_{season}_pass_completion_heatmap.png"
    image_url = f"{public_r2_url}/{image_filename}"
    
    return redirect(image_url)

@app.route("/position_heatmap")
@limiter.limit("30 per minute")
def position_heatmap_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
        
    public_r2_url = os.environ.get('R2_PUBLIC_URL')
    if not public_r2_url:
        return jsonify({"error": "Server is not configured with R2_PUBLIC_URL"}), 500

    image_filename = f"{player_id}_{season}_position_heatmap.png"
    image_url = f"{public_r2_url}/{image_filename}"
    return redirect(image_url)

@app.route("/pressure_heatmap")
@limiter.limit("30 per minute") 
def pressure_heatmap_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400

    public_r2_url = os.environ.get('R2_PUBLIC_URL')
    if not public_r2_url:
        return jsonify({"error": "Server is not configured with R2_PUBLIC_URL"}), 500
        
    image_filename = f"{player_id}_{season}_pressure_heatmap.png"
    image_url = f"{public_r2_url}/{image_filename}"
    return redirect(image_url)


@app.route("/pass_map_zona_stats")
@limiter.limit("30 per minute")
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
@limiter.limit("30 per minute")  
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

@app.route("/api/model/default_v14_config")
def get_default_v14_config():
    """
    Retorna la configuració del model V14 amb els textos traduïts.
    """
    try:
        lang = request.headers.get('Accept-Language', 'ca').split(',')[0]
        translations = load_translation(lang)
        
        config_translations = translations.get("scouting", {}).get("v14Config", {})

        kpi_definitions = get_trainer_kpi_definitions_for_weight_derivation()
        composite_impact_kpis = get_trainer_composite_impact_kpis_definitions()
        
        return jsonify({
            "model_id": "peak_potential_v2_15_16",
            "model_name": config_translations.get('title'),
            "description": config_translations.get('description'),
            
            "algorithm": config_translations.get('algorithm_value'),
            "target_variable": config_translations.get('targetVariable_value'),
            "training_data": config_translations.get('trainingData_value'),
            "evaluation_season": config_translations.get('evaluationSeason_value'),
            
            "kpi_definitions_for_weight_derivation": kpi_definitions,
            "composite_impact_kpis": composite_impact_kpis,
            
            "feature_engineering": {
                "current_season": config_translations.get('currentSeason_desc'),
                "historical": config_translations.get('historical_desc'),
                "age_based": config_translations.get('ageBased_desc')
            }
        })
    except Exception as e:
        logger.error(f"Error fetching default V14 config: {e}", exc_info=True)
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
    custom_model_display_name = custom_model_name_prefix

    user_impact_kpis_config = {position_group: user_impact_kpis_list}
    user_target_kpis_for_weight_derivation_config = {position_group: user_target_kpis_list}

    try:
        success, message = build_and_train_model_from_script_logic(
            r2_bucket_name=R2_BUCKET_NAME,
            r2_endpoint_url=R2_ENDPOINT_URL,
            r2_access_key_id=R2_ACCESS_KEY_ID,
            r2_secret_access_key=R2_SECRET_ACCESS_KEY,
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


@app.route("/api/custom_model/trigger_github_training", methods=['POST'])
@limiter.limit("20 per hour") 
def trigger_github_training():
    """
    Triggers a GitHub Actions workflow to train a custom model.
    This avoids timeout issues on Render free tier by running the training on GitHub Actions.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON payload"}), 400

    logger.info(f" Received training request: {json.dumps(data, indent=2)}")
    logger.info(f" Data types: position_group={type(data.get('position_group'))}, impact_kpis={type(data.get('impact_kpis'))}, target_kpis={type(data.get('target_kpis'))}")

    validated_data, error_response = validate_request_data(CustomModelTrainingSchema, data)
    if error_response:
        logger.error(f" Validation failed: {error_response[0].json}")
        return error_response
    
    position_group = validated_data["position_group"]
    user_impact_kpis_list = validated_data["impact_kpis"]
    user_target_kpis_list = validated_data["target_kpis"]
    custom_model_name_prefix = validated_data.get("model_name", f"custom_{position_group.lower()}")
    user_ml_feature_selection = validated_data.get("ml_features")

    if not GITHUB_TOKEN:
        return jsonify({
            "error": "GitHub Actions integration not configured. Please set GITHUB_TOKEN environment variable.",
            "fallback": "You can manually trigger the workflow at: https://github.com/{}/{}/actions/workflows/train_model.yml".format(GITHUB_REPO_OWNER, GITHUB_REPO_NAME)
        }), 503

    custom_model_id = f"{custom_model_name_prefix.replace(' ', '_').replace('-', '_')}_{uuid.uuid4().hex[:6]}"
    custom_model_display_name = custom_model_name_prefix

    github_api_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/dispatches"
    
    payload = {
        "event_type": "train-model-event",
        "client_payload": {
            "model_id": custom_model_id,
            "position_group": position_group,
            "impact_kpis": user_impact_kpis_list,
            "target_kpis": user_target_kpis_list,
            "ml_features": user_ml_feature_selection
        }
    }

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        logger.info(f"Triggering GitHub Actions workflow for model: {custom_model_id}")
        response = requests.post(github_api_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 204:            
            response_data = {
                "success": True,
                "message": f"Model training started successfully",
                "custom_model_id": custom_model_id,
                "estimated_time": "45-90 minutes",
                "instructions": "The model will be available in the list once training completes. This typically takes 45-90 minutes depending on data size and complexity."
            }
            
            
            workflow_url = f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/train_model.yml"
            response_data["workflow_url"] = workflow_url
            response_data["instructions"] = "You can monitor the progress at the workflow URL. The model will be available in the list once training completes (typically 45-90 minutes)."            
            return jsonify(response_data), 202
        else:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            return jsonify({
                "error": f"Failed to trigger GitHub Actions: {response.status_code}",
                "details": response.text,
                "manual_url": f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/train_model.yml"
            }), 500
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling GitHub API: {e}", exc_info=True)
        return jsonify({
            "error": f"Failed to connect to GitHub API: {str(e)}",
            "manual_url": f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/train_model.yml"
        }), 500


@app.route("/api/custom_model/list")
def list_custom_models():
    custom_models_list = []
    
    if s3_client and R2_BUCKET_NAME:
        try:
            logger.info("Listing custom models from R2...")
            response = s3_client.list_objects_v2(
                Bucket=R2_BUCKET_NAME,
                Prefix='ml_models/custom_models/',
                Delimiter='/'
            )
            
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    model_folder = prefix['Prefix']
                    model_id = model_folder.strip('/').split('/')[-1]
                    
                    for position_group in ['attacker', 'midfielder', 'defender']:
                        config_key = f"{model_folder}{position_group}/model_config_{position_group}_{model_id}.json"
                        try:
                            config_obj = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=config_key)
                            config_content = config_obj['Body'].read().decode('utf-8')
                            cfg = json.loads(config_content)
                            
                            position_display = position_group.capitalize()
                            display_name = cfg.get("model_display_name", cfg.get("model_type", ""))

                            custom_models_list.append({
                                "id": model_id,
                                "name": display_name,
                                "position_group": cfg.get("position_group_trained_for", position_display),
                                "description": cfg.get("description", "Custom Potential Model")
                            })
                            logger.info(f"Found custom model: {model_id} for {position_display}")
                        except Exception as e:
                            if 'NoSuchKey' in str(e) or '404' in str(e):
                                pass
                            else:
                                logger.error(f"Error reading config for {model_id}/{position_group}: {e}")
            
            logger.info(f"Found {len(custom_models_list)} custom models in R2")
        except Exception as e:
            logger.error(f"Error listing custom models from R2: {e}", exc_info=True)
    
    if os.path.exists(CUSTOM_MODELS_DIR):
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
                                with open(config_path, 'r') as f_cfg: 
                                    cfg = json.load(f_cfg)
                                if not any(m['id'] == model_id_folder for m in custom_models_list):
                                    custom_models_list.append({
                                        "id": model_id_folder,
                                        "name": cfg.get("model_display_name", cfg.get("model_type", f"{model_id_folder} ({pos_group_folder_name.capitalize()})")),  # ✅ Should use model_display_name
                                        "position_group": cfg.get("position_group_trained_for", pos_group_folder_name.capitalize()),
                                        "description": cfg.get("description", "Custom Potential Model (Local)")
                                    })
                                    logger.info(f"Found local custom model: {model_id_folder}")
                            except Exception as e:
                                logger.error(f"Error reading local config {config_path}: {e}")
    
    return jsonify({"custom_models": custom_models_list})


def load_model_from_r2_cached(model_key: str, scaler_key: str, config_key: str):
    """
    Load model, scaler, and config from R2.
    Note: Caching temporarily disabled due to compatibility issues with lru_cache.
    
    Args:
        model_key: R2 object key for the model file
        scaler_key: R2 object key for the scaler file
        config_key: R2 object key for the config file
    
    Returns:
        tuple: (model, scaler, config_dict)
    """
    logger.info(f"Loading model from R2: {model_key}")
    
    try:
        with BytesIO() as f_model:
            s3_client.download_fileobj(Bucket=R2_BUCKET_NAME, Key=model_key, Fileobj=f_model)
            f_model.seek(0)
            model = joblib.load(f_model)
        
        with BytesIO() as f_scaler:
            s3_client.download_fileobj(Bucket=R2_BUCKET_NAME, Key=scaler_key, Fileobj=f_scaler)
            f_scaler.seek(0)
            scaler = joblib.load(f_scaler)
        
        response_cfg = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=config_key)
        config_content = response_cfg['Body'].read().decode('utf-8')
        config = json.loads(config_content)
        
        logger.info(f" Model loaded successfully: {model_key}")
        return model, scaler, config
    
    except Exception as e:
        logger.error(f" Failed to load model from R2: {str(e)}")
        raise


@app.route("/scouting_predict")
@limiter.limit("10 per minute") 
def scouting_predict():
    validated_data, error_response = validate_request_data(
        PredictionRequestSchema,
        {
            "player_id": request.args.get("player_id"),
            "season": request.args.get("season"),
            "model_id": request.args.get("model_id", "default_v14")
        }
    )
    if error_response:
        return error_response
    
    player_id_str = validated_data["player_id"]
    season_to_predict_for = validated_data["season"]
    model_identifier = validated_data.get("model_id", "default_v14")

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
        
        is_custom_model = True
        base_path_in_bucket = "ml_models/custom_models" 
        
        if model_identifier == "default_v14":
            effective_model_id_for_path = "peak_potential_v2_15_16"
            is_custom_model = False 
            base_path_in_bucket = "ml_models/ml_model_files_peak_potential"


        if not s3_client:
            return jsonify({"error": "S3 client not initialized. Check server configuration."}), 500
            
        logger.info(f"Loading model from R2. Bucket: {R2_BUCKET_NAME}, Model ID: {effective_model_id_for_path}, Position: {position_group_for_prediction}")

        model_file_name_suffix = f"_{effective_model_id_for_path}"
        
        model_key = f"{base_path_in_bucket}/{effective_model_id_for_path}/{position_group_for_prediction.lower()}/potential_model_{position_group_for_prediction.lower()}{model_file_name_suffix}.joblib"
        scaler_key = f"{base_path_in_bucket}/{effective_model_id_for_path}/{position_group_for_prediction.lower()}/feature_scaler_{position_group_for_prediction.lower()}{model_file_name_suffix}.joblib"
        config_key = f"{base_path_in_bucket}/{effective_model_id_for_path}/{position_group_for_prediction.lower()}/model_config_{position_group_for_prediction.lower()}{model_file_name_suffix}.json"

        try:
            model_to_load, scaler_to_load, model_cfg = load_model_from_r2_cached(
                model_key, scaler_key, config_key
            )
            
            expected_ml_feature_names_for_model = model_cfg.get("features_used_for_ml_model", [])
            if not expected_ml_feature_names_for_model:
                return jsonify({"error": f"Feature list missing in config for model {effective_model_id_for_path}"}), 500

        except Exception as e:
            error_str = str(e)
            if '404' in error_str or 'NoSuchKey' in error_str or 'Not Found' in error_str:
                error_message = f"Model files not found in R2. Model ID: {model_identifier}, Position: {position_group_for_prediction}. Keys tried: model={model_key}, scaler={scaler_key}, config={config_key}"
                logger.error(error_message)
                return jsonify({"error": error_message}), 404
            else:
                logger.error(f"Failed to load model files from R2 for {model_identifier}. Keys: model={model_key}, scaler={scaler_key}, config={config_key}. Error: {error_str}", exc_info=True)
                return jsonify({"error": f"Could not load model files from cloud storage for {model_identifier}. Error: {error_str}"}), 500


        player_seasons_all = player_metadata.get("seasons", [])
        if not player_seasons_all: return jsonify({"error": "No seasons for player"}), 404
        
        minutes_df_global = pd.DataFrame()
        if s3_client:
            try:
                response_minutes = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key="data/player_season_minutes_with_names.csv")
                minutes_content = response_minutes['Body'].read().decode('utf-8')
                minutes_df_global = pd.read_csv(StringIO(minutes_content))
                minutes_df_global['season_name_std'] = minutes_df_global['season_name'].str.replace('/', '_', regex=False)
            except Exception as e:
                logger.error(f"Error loading player_season_minutes_with_names.csv from R2: {e}")
                return jsonify({"error": "Could not load essential minutes data from cloud storage."}), 500
        else:
             return jsonify({"error": "Server not configured for cloud data access."}), 500

        target_s_numeric_pred = int(season_to_predict_for.split('_')[0])
        all_base_metric_names_from_trainer = trainer_get_feature_names()

        df_all_base_features_for_player_list_pred = []
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

        result = jsonify({
            "player_id": player_id_str, "player_name": player_name_from_index,
            "season_predicted_from": season_to_predict_for,
            "age_at_season_start_of_year": age_at_season, "position_group": position_group_for_prediction,
            "predicted_potential_score": round(final_predicted_score, 2),
            "num_90s_played_in_season": round(num_90s_target_season_pred, 2),
            "model_used": model_identifier,
            "debug_num_ml_features_generated_for_pred": len(ml_features_series_pred) if ml_features_series_pred is not None else 0,
            "debug_num_ml_features_expected_by_model": len(expected_ml_feature_names_for_model)
        })
        
        if 'df_all_seasons_base_features' in locals():
            del df_all_seasons_base_features
        if 'minutes_df_global' in locals():
            del minutes_df_global
        if 'aligned_features_df_pred' in locals():
            del aligned_features_df_pred
        gc.collect()
        
        return result

    except Exception as e:
        logger.error(f"Error in /scouting_predict (model: {model_identifier}): {e}", exc_info=True)
        gc.collect()
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
@limiter.limit("20 per minute")
def goalkeeper_analysis_route(player_id, season):
    """Serveix una anàlisi completa del porter incloent estadístiques i dades de gràfics."""
    if not player_id or not season:
        return jsonify({"error": "Falta player_id o season"}), 400
    try:
        df_player = load_player_data(player_id, season, DATA_DIR)
        analysis_results = _calculate_goalkeeper_metrics(df_player, player_id)

        del df_player
        gc.collect() 

        if analysis_results.get("error"):
            logger.warning(f"L'anàlisi del porter per a {player_id}/{season} ha resultat en un error: {analysis_results.get('error')}")
            return jsonify(analysis_results), 404
        return jsonify(analysis_results)
    except Exception as e:
        logger.error(f"Excepció a goalkeeper_analysis_route per a {player_id}, {season}: {e}", exc_info=True)
        return jsonify({"error": f"Error inesperat del servidor: {str(e)}"}), 500

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

        minutes_df_global = pd.DataFrame()
        if s3_client:
            try:
                response_minutes = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key="data/player_season_minutes_with_names.csv")
                minutes_content = response_minutes['Body'].read().decode('utf-8')
                minutes_df_global = pd.read_csv(StringIO(minutes_content))
                minutes_df_global['season_name_std'] = minutes_df_global['season_name'].str.replace('/', '_', regex=False)
            except Exception as e:
                logger.error(f"Error loading player_season_minutes_with_names.csv from R2: {e}")
                return jsonify({"error": "Could not load essential minutes data from cloud storage."}), 500
        else:
             return jsonify({"error": "Server not configured for cloud data access."}), 500

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
            if df_events_season is None: 
                df_events_season = pd.DataFrame()
            
            base_features_series = trainer_extract_base_features(
                df_events_season, 
                age_at_season, 
                season_numeric, 
                num_90s
            )
            
            metric_value = base_features_series.get(metric_to_aggregate, 0.0)

            try:
                numeric_metric_value = float(metric_value)
            except (ValueError, TypeError):
                numeric_metric_value = float('nan')

            if not math.isfinite(numeric_metric_value):
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

        minutes_df_global = pd.DataFrame()
        if s3_client:
            try:
                response_minutes = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key="data/player_season_minutes_with_names.csv")
                minutes_content = response_minutes['Body'].read().decode('utf-8')
                minutes_df_global = pd.read_csv(StringIO(minutes_content))
                minutes_df_global['season_name_std'] = minutes_df_global['season_name'].str.replace('/', '_', regex=False)
            except Exception as e:
                logger.error(f"Error loading player_season_minutes_with_names.csv from R2: {e}")
                return jsonify({"error": "Could not load essential minutes data from cloud storage."}), 500
        else:
            return jsonify({"error": "Server not configured for data access."}), 500

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
        

        try:
            numeric_metric_value = float(metric_value)
        except (ValueError, TypeError):

            numeric_metric_value = float('nan')


        if not math.isfinite(numeric_metric_value):
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
