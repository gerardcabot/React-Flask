from flask import Flask, jsonify, request
import os
import pandas as pd
from flask_cors import CORS
import matplotlib
from matplotlib import pyplot as plt
from mplsoccer import Pitch, Radar, grid, FontManager, VerticalPitch
from ast import literal_eval
import json
from scipy.ndimage import gaussian_filter
from matplotlib import patheffects
import logging
import numpy as np
import joblib
import datetime
import uuid 

from model_trainer.trainer import (
    build_and_train_model_from_script_logic,
    get_trainer_kpi_definitions_for_weight_derivation,
    get_trainer_composite_impact_kpis_definitions,
    # NOVES IMPORTACIONS PER CONSISTÈNCIA:
    get_general_position as trainer_get_general_position, # Renombrat per evitar conflictes si ja existeix un local
    parse_location as trainer_parse_location,
    # is_progressive as trainer_is_progressive,
    get_feature_names_for_extraction as trainer_get_feature_names,
    extract_season_features as trainer_extract_base_features,
    trainer_construct_ml_features_for_player_season, # Nova funció per al Pass 2
    safe_division as trainer_safe_division, # Importar safe_division del trainer si es necessita
    get_trainer_all_possible_ml_feature_names 
)


# Configure logging
logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
logger = logging.getLogger(__name__)


BASE_DIR_SERVER_FLASK = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "..", "data")

V14_MODEL_BASE_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "..", "ml_models", "ml_model_files_v14_rebuild_trainer", "v14_rebuild") # Ruta ajustada

PLAYER_MINUTES_PATH = os.path.join(DATA_DIR, "player_season_minutes_with_names.csv")
LOADED_V14_MODELS = {}

STATIC_IMG_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "static", "images")
os.makedirs(STATIC_IMG_DIR, exist_ok=True)

CUSTOM_MODELS_DIR = os.path.join(BASE_DIR_SERVER_FLASK, "ml_models", "custom_models")
os.makedirs(CUSTOM_MODELS_DIR, exist_ok=True)

matplotlib.use("Agg")

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError, AttributeError): # Added AttributeError for resilience
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

def load_player_data(player_id, season, data_dir):
    def try_load_one(player_id, season, data_dir):
        file_path_json = os.path.join(data_dir, str(season), f"{player_id}.json")
        if os.path.exists(file_path_json):
            try:
                logger.debug(f"Loading JSON: {file_path_json}")
                return pd.read_json(file_path_json, convert_dates=False)
            except Exception as e:
                logger.error(f"Error loading JSON {file_path_json}: {e}")
                pass

        file_path_csv = os.path.join(data_dir, str(season), "players", f"{player_id}_{season}.csv")
        if os.path.exists(file_path_csv):
            try:
                logger.debug(f"Loading CSV: {file_path_csv}")
                df = pd.read_csv(file_path_csv, low_memory=False)
                loc_cols = [col for col in df.columns if 'location' in col or 'end_location' in col]
                for col in loc_cols:
                    if col in df.columns: df[col] = df[col].apply(lambda x: safe_literal_eval(x) if pd.notna(x) else None)

                bool_cols_to_check = [
                    # 50/50
                    'counterpress', # General, also used in Block, Dribbled Past, Duel, Foul Committed, Interception, Pressure
                    # Ball Recovery
                    'offensive', # General, also used in Block, Foul Committed
                    'recovery_failure',
                    # Block
                    'deflection',
                    'save_block',
                    # Clearance
                    'aerial_won', # General, also used in Miscontrol, Shot
                    # Dribble
                    'nutmeg',
                    'overrun',
                    'no_touch', # Dribble specific attribute
                    # Error
                    'leads_to_shot',
                    # Foul Committed
                    'advantage', # General, also used in Foul Won
                    'penalty',   # General, also used in Foul Won
                    # Foul Won
                    'defensive',
                    # Pass
                    'backheel',
                    'deflected', # Pass specific deflection
                    'miscommunication',
                    'cross',
                    'cut_back',
                    'switch',
                    'shot_assist',
                    'goal_assist',
                    # Shot
                    'follows_dribble',
                    'first_time',
                    'open_goal', # Assuming 'openAssistant' in your spec corresponds to 'open_goal' in data
                                 # If it's literally 'openAssistant', add that too.
                    'deflected', # Shot specific deflection

                    # General attributes that might be boolean and only present if true
                    'under_pressure',
                    'out' # Added from general attributes page 2 of spec.
                ]
                # Ensure uniqueness if any column appears multiple times due to "General"
                bool_cols_to_check = sorted(list(set(bool_cols_to_check)))


                for col in bool_cols_to_check:
                    if col in df.columns:
                        if df[col].dtype == 'object':
                            # Convert 'true'/'false' strings to True/False, keep others as NaN
                            # This preserves the StatsBomb convention where boolean flags are often only present if true.
                            df[col] = df[col].astype(str).str.lower().map(
                                {'true': True, 'false': False, 'nan': pd.NA, '': pd.NA}
                            ).astype('boolean') # Use pandas nullable boolean type
                        elif pd.api.types.is_numeric_dtype(df[col]):
                            # If numeric, 1.0 becomes True, 0.0 becomes False, NaN stays NaN
                            df[col] = df[col].map({1.0: True, 1: True, 0.0: False, 0: False}).astype('boolean')
                        # If already boolean or nullable boolean, leave it.
                
                numeric_cols_to_check = ['duration', 'pass_length', 'pass_angle', 'shot_statsbomb_xg', 'statsbomb_xg'] # Added statsbomb_xg for Shot
                for col in numeric_cols_to_check:
                    if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
                return df
            except Exception as e: logger.error(f"Error loading CSV {file_path_csv}: {e}"); pass
        logger.warning(f"No data file found for player {player_id} in season {season} (tried JSON: {file_path_json}, CSV: {file_path_csv})")
        return None

    if season == "all":
        dfs = []
        for season_folder_name in os.listdir(data_dir):
            season_folder_path = os.path.join(data_dir, season_folder_name)
            if os.path.isdir(season_folder_path) and '_' in season_folder_name:
                df_season = try_load_one(player_id, season_folder_name, data_dir)
                if df_season is not None and not df_season.empty: dfs.append(df_season)
        if dfs: return pd.concat(dfs, ignore_index=True)
        else: logger.info(f"No data found for player {player_id} across any seasons."); return pd.DataFrame()
    else:
        return try_load_one(player_id, season, data_dir)

app = Flask(__name__, static_folder=os.path.join(BASE_DIR_SERVER_FLASK, 'static'), static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})


def get_position_group(position_str: str) -> str:
    if not position_str or pd.isna(position_str): return "Unknown"
    pos_str_lower = str(position_str).lower()
    POSITION_GROUPS = {
        "Defender": ["defender", "back"], "Midfielder": ["midfield"],
        "Attacker": ["forward", "winger", "striker"], "Goalkeeper": ["goalkeeper", "keeper"]
    }
    for group, keywords in POSITION_GROUPS.items():
        if any(keyword in pos_str_lower for keyword in keywords): return group
    return "Unknown"

# def _calculate_goalkeeper_metrics(player_df, player_id_str):
#     empty_results = {
#         "player_id": player_id_str, "error": None,
#         "summary_text_stats": {
#             "total_actions_recorded": 0,
#             "total_passes": 0, "passes_completed": 0, "passes_incomplete_explicit": 0, "pass_accuracy_percentage": 0.0,
#             "total_gk_specific_actions": 0,
#             "saves_from_gk_events_colab_def": 0,
#             "goals_conceded_from_gk_events_colab_def": 0,
#             "shots_faced_in_gk_events_colab_def": 0,
#             "save_percentage_from_gk_events_colab_def": 0.0,
#             "total_shots_faced_on_target_direct": 0,
#             "saves_direct_involvement": 0,
#             "goals_conceded_direct_involvement": 0,
#             "save_percentage_direct_involvement": 0.0,
#             "carries_count": 0, "receipts_count": 0
#         },
#         "charts_data": {
#             "overall_action_type_distribution": [],
#             "pass_height_distribution": [],
#             "pass_outcome_pie_chart_data": [],
#             "gk_event_type_distribution": [],
#         },
#         "raw_data_points": {
#             "shots_faced_map_data": []
#         }
#     }

#     if player_df.empty:
#         empty_results["error"] = f"No data provided for player {player_id_str}."
#         return empty_results
#     if 'player_id' not in player_df.columns:
#         empty_results["error"] = "'player_id' column missing."
#         return empty_results

#     df_player_events = player_df[player_df['player_id'].astype(str) == str(player_id_str)].copy()
#     if df_player_events.empty:
#         empty_results["error"] = f"No events found for player_id {player_id_str} in filtered DataFrame."
#         return empty_results

#     results = json.loads(json.dumps(empty_results))
#     results.pop("error", None)
#     results["player_id"] = player_id_str
#     summary_stats = results["summary_text_stats"]

#     summary_stats["total_actions_recorded"] = len(df_player_events)
#     results["charts_data"]["overall_action_type_distribution"] = _format_value_counts(df_player_events.get('type'))

#     # df_passes = df_player_events[df_player_events.get('type') == 'Pass'].copy() if 'type' in df_player_events else pd.DataFrame()
#     df_passes = pd.DataFrame() # Initialize as an empty DataFrame
#     if 'type' in df_player_events.columns and not df_player_events['type'].dropna().empty:
#         # Check the actual type of the first non-null value in the 'type' column
#         first_type_val = df_player_events['type'].dropna().iloc[0]
        
#         if isinstance(first_type_val, dict) and 'name' in first_type_val:
#             # Handle cases where 'type' is an object like {'id': ..., 'name': 'Pass'}
#             pass_mask = df_player_events['type'].apply(lambda x: isinstance(x, dict) and x.get('name') == 'Pass')
#         else:
#             # Handle cases where 'type' is a simple string
#             pass_mask = (df_player_events['type'] == 'Pass')
        
#         df_passes = df_player_events[pass_mask].copy()
#     elif 'type' in df_player_events.columns: 
#         # 'type' column exists but is all NaN or empty, create an empty df_passes with same columns
#         df_passes = pd.DataFrame(columns=df_player_events.columns)
#     # If 'type' column doesn't exist at all, df_passes remains the initial empty DataFrame
#     if not df_passes.empty:
#         summary_stats["total_passes"] = len(df_passes)
#         colab_pass_failure_outcomes = ['Incomplete', 'Out', 'Pass Offside', 'Injury Clearance', 'Unknown']
#         if 'pass_outcome' in df_passes.columns:
#             summary_stats["passes_completed"] = int(len(df_passes[~df_passes['pass_outcome'].astype(str).isin(colab_pass_failure_outcomes)]))
#             summary_stats["passes_incomplete_explicit"] = int((df_passes['pass_outcome'] == 'Incomplete').sum())
#             pass_outcome_for_pie = df_passes['pass_outcome'].fillna('Completed (Implied)')
#             results["charts_data"]["pass_outcome_pie_chart_data"] = _format_value_counts(pass_outcome_for_pie)
#         else:
#             summary_stats["passes_completed"] = summary_stats["total_passes"]
#             results["charts_data"]["pass_outcome_pie_chart_data"] = [{"name": "Unknown Outcome", "value": summary_stats["total_passes"]}]

#         if summary_stats["total_passes"] > 0:
#             summary_stats["pass_accuracy_percentage"] = round((summary_stats["passes_completed"] / summary_stats["total_passes"]) * 100, 2)
#         results["charts_data"]["pass_height_distribution"] = _format_value_counts(df_passes.get('pass_height'))

#     df_gk_actions = df_player_events[df_player_events.get('type') == 'Goal Keeper'].copy() if 'type' in df_player_events else pd.DataFrame()
#     summary_stats["total_gk_specific_actions"] = len(df_gk_actions)
#     results["charts_data"]["gk_event_type_distribution"] = _format_value_counts(df_gk_actions.get('goalkeeper_type'))

#     if not df_gk_actions.empty and 'goalkeeper_type' in df_gk_actions.columns and 'goalkeeper_outcome' in df_gk_actions.columns:
#         colab_save_types = ['Shot Saved', 'Penalty Saved', 'Save', 'Smother']
#         sb_v11_success_outcomes_for_saves = ['Success', 'Success In Play', 'Success Out', 'Collected', 'Claim']

#         summary_stats["saves_from_gk_events_colab_def"] = int(len(df_gk_actions[
#             (df_gk_actions['goalkeeper_type'].isin(colab_save_types)) &
#             (df_gk_actions['goalkeeper_outcome'].isin(sb_v11_success_outcomes_for_saves))
#         ]))
#         summary_stats["goals_conceded_from_gk_events_colab_def"] = int((df_gk_actions['goalkeeper_type'] == 'Goal Conceded').sum())
#         summary_stats["shots_faced_in_gk_events_colab_def"] = int((df_gk_actions['goalkeeper_type'] == 'Shot Faced').sum())

#         shots_on_target_colab_def = summary_stats["saves_from_gk_events_colab_def"] + summary_stats["goals_conceded_from_gk_events_colab_def"]
#         if shots_on_target_colab_def > 0:
#             summary_stats["save_percentage_from_gk_events_colab_def"] = round(
#                 (summary_stats["saves_from_gk_events_colab_def"] / shots_on_target_colab_def) * 100, 2)

#     shots_faced_map_data_list = []
#     goals_conceded_direct = 0
#     saves_direct = 0

#     shot_related_gk_types_for_direct_analysis = ['Shot Saved', 'Penalty Saved', 'Goal Conceded', 'Save', 'Shot Faced']
#     df_direct_shot_interactions = df_gk_actions[df_gk_actions.get('goalkeeper_type', pd.Series(dtype=str)).isin(shot_related_gk_types_for_direct_analysis)]

#     # Attempt to find an xG column on GK events (though unlikely as per spec)
#     xg_col_on_gk_event = None
#     if not df_direct_shot_interactions.empty:
#         potential_xg_cols = ['shot_statsbomb_xg', 'goalkeeper.shot_statsbomb_xg', 'xg']
#         for col in potential_xg_cols:
#             if col in df_direct_shot_interactions.columns:
#                 xg_col_on_gk_event = col
#                 break

#     for _, row in df_direct_shot_interactions.iterrows():
#         shot_loc = safe_literal_eval(row.get('location'))
#         shot_end_loc = safe_literal_eval(row.get('shot_end_location'))

#         current_shot_xg = 0.0 # Default xG
#         if xg_col_on_gk_event and pd.notna(row.get(xg_col_on_gk_event)): # If an xG col was found and has value
#             current_shot_xg = safe_float(row.get(xg_col_on_gk_event))

#         is_goal_flag = None
#         shot_outcome_for_map = row.get('goalkeeper_type')

#         if row.get('goalkeeper_type') == 'Goal Conceded':
#             is_goal_flag = True
#             goals_conceded_direct += 1
#         elif row.get('goalkeeper_type') in ['Shot Saved', 'Penalty Saved', 'Save']:
#             save_outcomes_sb = ['Success', 'Success In Play', 'Success Out', 'Collected', 'Claim', 'In Play Safe', 'Saved Twice', 'Touched Out']
#             if row.get('goalkeeper_outcome') in save_outcomes_sb:
#                 is_goal_flag = False
#                 saves_direct += 1
#             shot_outcome_for_map = 'Saved' if is_goal_flag is False else shot_outcome_for_map
#         elif row.get('goalkeeper_type') == 'Shot Faced':
#              shot_outcome_for_map = 'Faced'


#         map_entry = {
#             "origin": shot_loc[:2] if shot_loc and len(shot_loc) >=2 else None,
#             "end_location": shot_end_loc[:3] if shot_end_loc and len(shot_end_loc) >=3 else None,
#             "outcome": shot_outcome_for_map, "xg": current_shot_xg, "is_goal": is_goal_flag,
#             "minute": int(safe_float(row.get("minute"))), "second": int(safe_float(row.get("second")))
#         }
#         if map_entry["origin"]:
#             shots_faced_map_data_list.append(map_entry)

#     results["raw_data_points"]["shots_faced_map_data"] = shots_faced_map_data_list

#     summary_stats["total_shots_faced_on_target_direct"] = saves_direct + goals_conceded_direct
#     summary_stats["saves_direct_involvement"] = saves_direct
#     summary_stats["goals_conceded_direct_involvement"] = goals_conceded_direct
#     if summary_stats["total_shots_faced_on_target_direct"] > 0:
#         summary_stats["save_percentage_direct_involvement"] = round(
#             (saves_direct / summary_stats["total_shots_faced_on_target_direct"]) * 100, 2
#         )

#     df_carries = df_player_events[df_player_events.get('type') == 'Carry'] if 'type' in df_player_events else pd.DataFrame()
#     summary_stats["carries_count"] = len(df_carries)
#     df_receipts = df_player_events[df_player_events.get('type') == 'Ball Receipt*'] if 'type' in df_player_events else pd.DataFrame()
#     summary_stats["receipts_count"] = len(df_receipts)

#     return results


def _calculate_goalkeeper_metrics(player_df, player_id_str):
    # Consistent empty structure
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
            # REMOVED PSXG METRICS
            # "psxg_faced_direct_involvement": 0.0,
            # "goals_prevented_direct_involvement": 0.0,
            "carries_count": 0, "receipts_count": 0
        },
        "charts_data": {
            "overall_action_type_distribution": [],
            "pass_height_distribution": [],
            "pass_outcome_pie_chart_data": [],
            "gk_event_type_distribution": [],
        },
        "raw_data_points": {
            "shots_faced_map_data": [] # Only this map data remains
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
    # REMOVED: total_psxg_direct = 0.0 (no longer needed for this function's output)
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
        
        current_shot_xg = 0.0 # Default xG
        if xg_col_on_gk_event and pd.notna(row.get(xg_col_on_gk_event)): # If an xG col was found and has value
            current_shot_xg = safe_float(row.get(xg_col_on_gk_event))

        is_goal_flag = None
        shot_outcome_for_map = row.get('goalkeeper_type')

        if row.get('goalkeeper_type') == 'Goal Conceded':
            is_goal_flag = True
            goals_conceded_direct += 1
            # total_psxg_direct += current_shot_xg # Accumulate xG for goals
        elif row.get('goalkeeper_type') in ['Shot Saved', 'Penalty Saved', 'Save']:
            save_outcomes_sb = ['Success', 'Success In Play', 'Success Out', 'Collected', 'Claim', 'In Play Safe', 'Saved Twice', 'Touched Out']
            if row.get('goalkeeper_outcome') in save_outcomes_sb:
                is_goal_flag = False
                saves_direct += 1
                # total_psxg_direct += current_shot_xg # Accumulate xG for saves
            shot_outcome_for_map = 'Saved' if is_goal_flag is False else shot_outcome_for_map
        elif row.get('goalkeeper_type') == 'Shot Faced':
             shot_outcome_for_map = 'Faced'


        map_entry = {
            "origin": shot_loc[:2] if shot_loc and len(shot_loc) >=2 else None,
            "end_location": shot_end_loc[:3] if shot_end_loc and len(shot_end_loc) >=3 else None,
            "outcome": shot_outcome_for_map, "xg": current_shot_xg, "is_goal": is_goal_flag,
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
    # REMOVED PSXG dependent stats
    # summary_stats["psxg_faced_direct_involvement"] = round(total_psxg_direct, 2)
    # summary_stats["goals_prevented_direct_involvement"] = round(total_psxg_direct - goals_conceded_direct, 2)

    df_carries = df_player_events[df_player_events.get('type') == 'Carry'] if 'type' in df_player_events else pd.DataFrame()
    summary_stats["carries_count"] = len(df_carries)
    df_receipts = df_player_events[df_player_events.get('type') == 'Ball Receipt*'] if 'type' in df_player_events else pd.DataFrame()
    summary_stats["receipts_count"] = len(df_receipts)
    
    return results



def get_seasons_up_to(season, data_dir):
    all_seasons = sorted([s for s in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, s)) and '_' in s])
    if season not in all_seasons: return []
    try: idx = all_seasons.index(season); return all_seasons[:idx+1]
    except ValueError: return []


def get_age_at_fixed_point_in_season(dob_str, season_str):
    try:
        birth_date = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date()
        season_end_year = int(str(season_str).split('_')[1])
        fixed_date_in_season = datetime.date(season_end_year, 1, 1)
        age = fixed_date_in_season.year - birth_date.year - \
              ((fixed_date_in_season.month, fixed_date_in_season.day) < (birth_date.month, birth_date.day))
        return age
    except Exception as e: logger.error(f"Error calculating age for DOB {dob_str}, season {season_str}: {e}"); return None

def load_all_v14_potential_models():
    global LOADED_V14_MODELS
    LOADED_V14_MODELS = {}
    logger.info(f"Attempting to load V14 models. Base directory: {os.path.abspath(V14_MODEL_BASE_DIR)}")
    position_groups_v14 = ["Attacker", "Midfielder", "Defender"]
    for group in position_groups_v14:
        group_lower = group.lower()
        model_dir_for_group = os.path.join(V14_MODEL_BASE_DIR, group_lower) # V14_MODEL_BASE_DIR ja inclou v14_rebuild
        
        # Els noms dels fitxers desats per trainer.py inclouen el custom_model_id ("v14_rebuild")
        model_path = os.path.join(model_dir_for_group, f"potential_model_{group_lower}_v14_rebuild.joblib")
        scaler_path = os.path.join(model_dir_for_group, f"feature_scaler_{group_lower}_v14_rebuild.joblib")
        config_path = os.path.join(model_dir_for_group, f"model_config_{group_lower}_v14_rebuild.json")
        
        if not all(os.path.exists(p) for p in [model_path, scaler_path, config_path]):
            logger.error(f"One or more V14 files NOT FOUND for {group} in {model_dir_for_group} (tried _v14_rebuild variants)")
            logger.error(f"  Expected model: {model_path}")
            logger.error(f"  Expected scaler: {scaler_path}")
            logger.error(f"  Expected config: {config_path}")
            continue
        try:
            model = joblib.load(model_path); scaler = joblib.load(scaler_path)
            with open(config_path, 'r', encoding='utf-8') as f: model_config = json.load(f)
            feature_names_from_config = model_config.get("features_used_for_ml_model")
            if not feature_names_from_config:
                logger.error(f"Corrupt config for {group}: 'features_used_for_ml_model' missing."); continue
            LOADED_V14_MODELS[group] = {"model": model, "scaler": scaler, "feature_names": feature_names_from_config}
            logger.info(f"Successfully loaded V14 model, scaler, config for {group}. Expects {len(feature_names_from_config)} features.")
        except Exception as e: logger.error(f"Error loading V14 model/scaler/config for {group}: {e}", exc_info=True)
    if not LOADED_V14_MODELS: logger.critical("CRITICAL FAILURE: No V14 potential models were loaded.")
    else: logger.info(f"V14 Models successfully loaded for groups: {list(LOADED_V14_MODELS.keys())}")


def structure_kpis_for_frontend(kpi_definitions_by_position):
    """
    Transforma el diccionari de KPIs per posició en una estructura més amigable
    per al frontend, agrupant mètriques base amb les seves variants.
    També genera una llista plana de tots els noms de kpi tècnics per a la validació.
    """
    structured_kpis = []
    all_technical_kpi_names = set()

    # Identificar mètriques base i les seves variants
    # Això és una heurística; pot necessitar ajustos segons la teva nomenclatura exacta
    metric_map = {} # base_metric -> {label: "Gols", variants: {p90: "goals_p90", total: "goals", ...}}

    raw_kpis_flat = set()
    for pos_kpis in kpi_definitions_by_position.values():
        raw_kpis_flat.update(pos_kpis)

    for kpi_name in sorted(list(raw_kpis_flat)):
        all_technical_kpi_names.add(kpi_name)
        base_name = kpi_name
        variant_type = "total" # Suma o recompte directe
        label_suffix = ""

        if kpi_name.endswith("_p90_sqrt_"):
            base_name = kpi_name.replace("_p90_sqrt_", "")
            variant_type = "p90_sqrt"
            label_suffix = " (per 90 min, arrel quadrada)"
        elif kpi_name.endswith("_sqrt_"): # Per si hi ha mètriques sqrt directes
            base_name = kpi_name.replace("_sqrt_", "")
            variant_type = "sqrt"
            label_suffix = " (arrel quadrada)"
        elif kpi_name.endswith("_p90"):
            base_name = kpi_name.replace("_p90", "")
            variant_type = "p90"
            label_suffix = " (per 90 min)"
        elif kpi_name.endswith("_kpi"): # KPIs directes com "pass_completion_rate_kpi"
             base_name = kpi_name # Mantenir el nom complet com a base per a aquests
             variant_type = "direct_kpi" # Un tipus especial
             # L'etiqueta ja és descriptiva
        elif kpi_name.endswith("_base") and "_inv_kpi_base" in kpi_name: # Ex: turnovers_p90_inv_kpi_base
             base_name = kpi_name.replace("_p90_inv_kpi_base", "_turnovers") # Agrupar sota "Turnovers"
             variant_type = "p90_inv_base"
             label_suffix = " (Pèrdues p90, invertit, valor base)"
        
        # Creació d'etiquetes més amigables
        # (aquesta part es pot millorar amb un mapeig més explícit si cal)
        label_base = base_name.replace('_', ' ').replace("count ", "").replace("sum ", "")
        label_base = ' '.join(word.capitalize() for word in label_base.split(' '))
        if variant_type == "direct_kpi":
            label = label_base # L'etiqueta ja hauria de ser bona
        else:
            label = f"{label_base}{label_suffix}"

        if base_name not in metric_map:
            metric_map[base_name] = {"id_base": base_name, "label_base": label_base, "variants": {}}
        
        metric_map[base_name]["variants"][variant_type] = {
            "id": kpi_name, # Nom tècnic complet
            "label_variant": label_suffix.strip(" ()"), # Només el sufix per a la UI de selecció de variant
            "full_label": label # Etiqueta completa per mostrar
        }
        # Cas especial per a mètriques directes sense sufix de variant
        if not label_suffix and variant_type == "total":
             metric_map[base_name]["variants"][variant_type]["label_variant"] = "Total / Recompte"


    # Convertir el mapa a la llista estructurada
    for base_info in metric_map.values():
        # Només afegir si té variants (evitar mètriques base que no tenien sufixos)
        if base_info["variants"]:
            variants_list = []
            # Ordre desitjat de les variants
            order = ["total", "p90", "p90_sqrt", "sqrt", "direct_kpi", "p90_inv_base"]
            for variant_key in order:
                if variant_key in base_info["variants"]:
                    variants_list.append(base_info["variants"][variant_key])
            if variants_list: # Només si hi ha variants processades
                 structured_kpis.append({
                    "metric_base_id": base_info["id_base"],
                    "metric_base_label": base_info["label_base"],
                    "options": variants_list
                })
    
    structured_kpis.sort(key=lambda x: x["metric_base_label"]) # Ordenar per etiqueta base

    return structured_kpis, sorted(list(all_technical_kpi_names))

# --- End of pasted helper functions from main.py ---


# --- API Routes ---

@app.route("/")
def home(): return jsonify({"message": "Welcome to the Player Stats API."})

player_index_path_main = os.path.join(DATA_DIR, "player_index.json")
player_index_main_data = {}
if os.path.exists(player_index_path_main):
    try:
        with open(player_index_path_main, "r", encoding="utf-8") as f: player_index_main_data = json.load(f)
    except Exception as e: logger.error(f"Error loading player_index.json for main: {e}")
else: logger.warning("main.py: player_index.json not found.")

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

@app.route("/player_valid_seasons")
def player_valid_seasons():
    player_id = request.args.get("player_id")
    if not player_id: return jsonify({"error": "Missing player_id"}), 400
    try:
        player_data = next((data for data in player_index_main_data.values() if isinstance(data, dict) and str(data.get("player_id")) == str(player_id)), None)
        if not player_data: return jsonify({"error": "Player not found"}), 404
        valid_seasons = []
        for season_folder in player_data.get("seasons", []):
            # Check for JSON
            json_path = os.path.join(DATA_DIR, season_folder, f"{player_id}.json")
            if os.path.exists(json_path): valid_seasons.append(season_folder); continue
            # Check for CSV if JSON not found
            csv_path = os.path.join(DATA_DIR, season_folder, "players", f"{player_id}_{season_folder}.csv") # Adjusted path
            if os.path.exists(csv_path): valid_seasons.append(season_folder)
        return jsonify({"player_id": player_id, "seasons": valid_seasons})
    except Exception as e: logger.error(f"Error in /player_valid_seasons: {e}", exc_info=True); return jsonify({"error": str(e)}), 500

@app.route("/player_events")
def player_events_route():
    player_id = request.args.get("player_id"); season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"error": "No data found"}), 404
        return df.to_json(orient="records", date_format="iso", default_handler=str)
    except Exception as e: logger.error(f"Error in /player_events: {e}", exc_info=True); return jsonify({"error": str(e)}), 500

@app.route("/seasons")
def list_seasons_route():
    try:
        season_folders = [folder for folder in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, folder)) and '_' in folder]
        return jsonify(sorted(season_folders))
    except Exception as e: logger.error(f"Error in /seasons: {e}", exc_info=True); return jsonify({"error": str(e)}), 500


@app.route("/api/player/<player_id>/event_data_schema/<season>")
def get_event_data_schema(player_id, season):
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400

    try:
        df = load_player_data(player_id, season, DATA_DIR)

        if df is None or df.empty:
            logger.warning(f"No event data for schema: player {player_id}, season {season}")
            return jsonify({"error": f"No event data found for player {player_id}, season {season}", "event_data_schema": []}), 404

        schema = []
        excluded_cols = [
            'index', 'id', 'match_id', 'player_id', 'team_id',
            'related_events', 'tactics_formation', 'tactics_lineup', 'shot_freeze_frame',
            'player', 'position', 'team', 'pass_recipient', 'substitution_replacement',
            'goalkeeper_body_part', 'goalkeeper_outcome', 'goalkeeper_position', 'goalkeeper_technique',
            'pass_body_part', 'pass_height', 'pass_outcome', 'pass_technique',
            'shot_body_part', 'shot_outcome', 'shot_technique',
            'duel_outcome', 'duel_type', # Added duel_type as it's often a dict
            'bad_behaviour_card', 'foul_committed_card', 'foul_committed_type',
            'interception_outcome', '50_50_outcome', 'ball_receipt_outcome',
            'substitution_outcome', 'goalkeeper_end_location'
        ]

        location_like_cols = ['location', 'carry_end_location', 'pass_end_location', 'shot_end_location']

        for col in df.columns:
            if col in excluded_cols and col not in location_like_cols:
                continue

            label = col.replace('_', ' ').title()
            col_type_str = str(df[col].dtype) # Get dtype as string
            viz_options = []

            example_val_series = df[col].dropna()
            example_value_str = "N/A"
            num_unique_values = 0 # Default

            try:
                if not example_val_series.empty:
                    first_val = example_val_series.iloc[0]
                    # For lists or dicts, nunique needs special handling
                    if isinstance(first_val, (list, dict)):
                        # Convert to string/tuple to count uniques if possible
                        try:
                            num_unique_values = example_val_series.astype(str).nunique() # Fallback: count unique string representations
                        except TypeError: # If even string conversion fails for nunique (rare)
                            num_unique_values = -1 # Indicate special handling needed
                        example_value_str = str(first_val)[:100] # Truncate long examples
                    else: # For hashable types
                        num_unique_values = example_val_series.nunique()
                        example_value_str = str(first_val)
                else: # Column is all NaNs
                    num_unique_values = 0
            except Exception as e_nunique:
                logger.warning(f"Could not calculate nunique or get example for column '{col}': {e_nunique}")
                num_unique_values = -2 # Indicate error during nunique/example
                example_value_str = "Error getting example"


            # Visualization suggestions based on column name and inferred type/cardinality
            if col in location_like_cols:
                if not example_val_series.empty and isinstance(example_val_series.iloc[0], (list, tuple)) and len(example_val_series.iloc[0]) >= 2:
                    viz_options.append({"viz_type": "scatter", "metric_type": "location", "label_suffix": "Locations"})
                # else: (Handled by general object/string below if not a valid location list)

            elif col_type_str == 'object':
                first_valid_obj = example_val_series.iloc[0] if not example_val_series.empty else None
                if isinstance(first_valid_obj, dict) and 'name' in first_valid_obj:
                    # For object columns like type: {'id': X, 'name': 'Pass'}, visualize the 'name'
                    viz_options.append({"viz_type": "bar", "metric_type": "categorical_object_name", "label_suffix": "Distribution (by Name)"})
                    viz_options.append({"viz_type": "pie", "metric_type": "categorical_object_name", "label_suffix": "Proportions (by Name)"})
                # If it's an object but not a dict with 'name', or if num_unique is low, treat as general categorical
                elif num_unique_values < 25 and num_unique_values > 0 :
                    viz_options.append({"viz_type": "bar", "metric_type": "categorical", "label_suffix": "Distribution"})
                    viz_options.append({"viz_type": "pie", "metric_type": "categorical", "label_suffix": "Proportions"})
                # If it's a list and wasn't caught by location_like_cols, it's likely unhashable for direct value_counts.
                # The frontend would need to handle this (e.g., by showing raw list or user choosing sub-elements).
                # For now, we might skip offering direct viz for generic list columns unless they are locations.

            elif col_type_str == 'bool':
                viz_options.append({"viz_type": "bar", "metric_type": "categorical", "label_suffix": "Distribution (True/False)"})
                viz_options.append({"viz_type": "pie", "metric_type": "categorical", "label_suffix": "Proportions (True/False)"})

            elif col_type_str.startswith('int') or col_type_str.startswith('float'):
                if num_unique_values < 25 and num_unique_values > 1:
                    viz_options.append({"viz_type": "bar", "metric_type": "categorical_numeric", "label_suffix": "Distribution (Counts)"}) # Treat as discrete categories
                    viz_options.append({"viz_type": "pie", "metric_type": "categorical_numeric", "label_suffix": "Proportions"})

                viz_options.append({"viz_type": "number_sum", "metric_type": "sum", "label_suffix": "Total Sum"})
                viz_options.append({"viz_type": "number_average", "metric_type": "average", "label_suffix": "Average"})
                if num_unique_values > 1:
                    viz_options.append({"viz_type": "numerical_distribution", "metric_type": "histogram", "label_suffix": "Distribution (Histogram)"})

            if viz_options: # Only add if we have some viz suggestion
                schema.append({
                    "column_name": col,
                    "label_prefix": label,
                    "data_type_original": col_type_str, # Store original pandas dtype
                    "example_value": example_value_str,
                    "num_unique": num_unique_values,
                    "possible_viz": viz_options
                })

        schema.sort(key=lambda x: x["label_prefix"])
        return jsonify({"event_data_schema": schema})

    except Exception as e:
        logger.error(f"CRITICAL ERROR in get_event_data_schema for {player_id}/{season}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error while generating data schema.", "event_data_schema": []}), 500


@app.route("/pass_completion_heatmap")
def pass_completion_heatmap_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        player_dir = os.path.join(STATIC_IMG_DIR, str(player_id))
        os.makedirs(player_dir, exist_ok=True)
        image_filename = f"{str(player_id)}_{season}_pass_compl_heatmap.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{str(player_id)}/{image_filename}"

        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            logger.warning(f"No data for pass completion heatmap {player_id}/{season}")
            return jsonify({"error": "No data found"}), 404

        df_passes = df[df.get("type") == "Pass"].copy() if "type" in df.columns else pd.DataFrame()

        if df_passes.empty or not all(c in df_passes.columns for c in ["location", "pass_outcome"]):
            logger.warning(f"Required columns missing for pass completion heatmap {player_id}/{season}")
            return jsonify({"error": "Required columns for pass completion missing"}), 400

        df_passes["location_eval"] = df_passes["location"].apply(safe_literal_eval)
        df_valid_loc = df_passes[df_passes["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)].copy()

        if df_valid_loc.empty:
            logger.warning(f"No valid pass location data for pass completion heatmap {player_id}/{season}")
            return jsonify({"error": "No valid pass location data"}), 404

        df_valid_loc["x"] = df_valid_loc["location_eval"].apply(lambda loc: loc[0])
        df_valid_loc["y"] = df_valid_loc["location_eval"].apply(lambda loc: loc[1])
        df_valid_loc["completed"] = df_valid_loc["pass_outcome"].isna() # StatsBomb: NaN often means completed

        pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='white')
        fig, ax = pitch.draw(figsize=(4.125, 6))
        fig.set_facecolor('#22312b')

        bin_statistic = pitch.bin_statistic_positional(df_valid_loc.x, df_valid_loc.y, values=df_valid_loc.completed, statistic='mean', positional='full')

        # Handle empty bins or all-NaN statistics before plotting
        for section_data in bin_statistic:
            if 'statistic' in section_data and isinstance(section_data['statistic'], np.ndarray):
                section_data['statistic'] = np.nan_to_num(section_data['statistic'], nan=0.0) # Replace NaN with 0 for plotting
            elif 'statistic' not in section_data or section_data['statistic'] is None : # If a section has no data at all
                 # Create zero-filled array matching grid shape if missing
                if 'x_grid' in section_data and 'y_grid' in section_data and section_data['x_grid'] is not None and section_data['y_grid'] is not None:
                    section_data['statistic'] = np.zeros((section_data['y_grid'].shape[0]-1, section_data['x_grid'].shape[1]-1), dtype=float)
                else: # Fallback if grid info also missing for a section
                    logger.warning(f"Missing grid info for a section in pass completion heatmap for {player_id}/{season}, section: {section_data.get('pos_section')}")
                    section_data['statistic'] = np.array([[0.0]])


        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='Blues', edgecolors='#22312b', vmin=0, vmax=1)
        path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')]
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)

        plt.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return jsonify({"image_url": image_url})
    except Exception as e:
        logger.error(f"Error in /pass_completion_heatmap for {player_id}/{season}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate pass completion heatmap: {str(e)}"}), 500


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
            if x_coord < 40: return "Defensive Third"  # StatsBomb X: 0-120
            elif x_coord < 80: return "Middle Third"
            else: return "Attacking Third"

        def get_pitch_channel(y_coord):
            if y_coord < 26.67: return "Left Channel" # StatsBomb Y: 0-80
            elif y_coord < 53.33: return "Central Channel"
            else: return "Right Channel"

        passes_df["end_third"] = passes_df["end_loc_eval"].apply(lambda loc: get_pitch_third(loc[0]))
        passes_df["end_channel"] = passes_df["end_loc_eval"].apply(lambda loc: get_pitch_channel(loc[1]))
        passes_df["zona"] = passes_df["end_third"] + " - " + passes_df["end_channel"]

        zonas_data = []
        for zona_name, group in passes_df.groupby("zona"):
            total_passes = len(group)
            # Using StatsBomb definition: NaN outcome for pass is completed
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
            # Match trainer's 'shot_outcome' (not 'shot_outcome_name')
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
        # Aquesta funció ja retorna el diccionari per posició.
        kpi_definitions_from_trainer = get_trainer_kpi_definitions_for_weight_derivation()

        # Ara utilitzem la nova funció per estructurar-los
        structured_kpis_for_frontend, all_technical_names = structure_kpis_for_frontend(kpi_definitions_from_trainer)
        
        return jsonify({
            "structured_kpis": structured_kpis_for_frontend,
            # Mantenim selectable_kpis per si alguna part del frontend encara la necessita,
            # o per a validació al backend si cal.
            "selectable_kpis_flat": all_technical_names, 
            # default_kpis_by_group_for_builder ja no és tan rellevant si l'usuari tria de la llista estructurada.
            # Podríem eliminar-lo o mantenir-lo si es vol alguna pre-selecció per defecte.
            # Per ara, el mantenim per si es vol una lògica de pre-selecció.
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
    
    # NOU: Rebre la selecció de característiques ML
    user_ml_feature_selection = data.get("ml_features", None) # Acceptar 'ml_features', default a None

    if not all([position_group, user_impact_kpis_list, user_target_kpis_list]):
        return jsonify({"error": "Missing required fields: position_group, impact_kpis (for correlation), target_kpis (for weighting)"}), 400
    if position_group not in ["Attacker", "Midfielder", "Defender"]:
        return jsonify({"error": f"Invalid position_group: {position_group}"}), 400
    
    # Validació opcional de user_ml_feature_selection (ex: és una llista de strings?)
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
            user_ml_feature_subset=user_ml_feature_selection, # Passar la selecció de l'usuari
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
                                # MILLORA APLICADA:
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
    model_identifier = request.args.get("model_id", "default_v14") # default_v14 és el ID per als reconstruïts

    if not player_id_str or not season_to_predict_for:
        return jsonify({"error": "Missing player_id or season"}), 400

    try:
        player_metadata = next((p_data for p_name, p_data in player_index_main_data.items() if isinstance(p_data, dict) and str(p_data.get("player_id")) == player_id_str), None)
        player_name_from_index = next((p_name for p_name, p_data in player_index_main_data.items() if isinstance(p_data, dict) and str(p_data.get("player_id")) == player_id_str), "N/A")

        if not player_metadata: return jsonify({"error": f"Player metadata not found for ID {player_id_str}"}), 404

        primary_pos_str = player_metadata.get("position", "Unknown")
        # ÚS DE LA FUNCIÓ IMPORTADA DEL TRAINER:
        position_group_for_prediction = trainer_get_general_position(primary_pos_str)
        if position_group_for_prediction not in ["Attacker", "Midfielder", "Defender"]:
             return jsonify({"error": f"Prediction not supported for position group: {position_group_for_prediction}"}), 400

        dob = player_metadata.get("dob")
        if not dob: return jsonify({"error": "Player DOB not found"}), 400
        age_at_season = get_age_at_fixed_point_in_season(dob, season_to_predict_for) # Funció local de main.py
        if age_at_season is None: return jsonify({"error": "Could not calculate age"}), 400

        model_to_load = None; scaler_to_load = None; expected_ml_feature_names_for_model = []
        # Per als models V14 reconstruïts, el model_identifier serà "v14_rebuild" si el frontend l'envia així.
        # Si el frontend envia "default_v14", haurem de mapejar-lo a "v14_rebuild" per carregar els fitxers correctes.
        effective_model_id_for_path = model_identifier
        model_base_path_to_use = "" # Inicialitzar
        is_custom_model = True # Assumir custom per defecte

        if model_identifier == "default_v14":
            effective_model_id_for_path = "v14_rebuild" # El sufix del nom del fitxer
            is_custom_model = False 
            # V14_MODEL_BASE_DIR ja és E:\React-Flask\ml_models\ml_model_files_v14_rebuild_trainer\v14_rebuild
            # model_pos_dir només necessita afegir la posició
            model_pos_dir = os.path.join(V14_MODEL_BASE_DIR, position_group_for_prediction.lower())
            model_base_path_to_use = V14_MODEL_BASE_DIR # Per al log
        else: # És un model personalitzat
            # effective_model_id_for_path ja és el model_identifier (l'ID del model custom)
            model_base_path_to_use = CUSTOM_MODELS_DIR
            model_pos_dir = os.path.join(model_base_path_to_use, effective_model_id_for_path, position_group_for_prediction.lower())
        
        logger.info(f"Loading model. Requested: {model_identifier}, Effective ID for filename: {effective_model_id_for_path}, Final Model Dir: {model_pos_dir}, Position: {position_group_for_prediction}")
        
        if not os.path.isdir(model_pos_dir):
            logger.error(f"Model directory not found: {model_pos_dir}")
            return jsonify({"error": f"Model directory not found for ID {effective_model_id_for_path}, Pos {position_group_for_prediction}"}), 404

        # El sufix ja està en effective_model_id_for_path (ja sigui 'v14_rebuild' o l'ID del custom model)
        model_file_name_suffix = f"_{effective_model_id_for_path}"
        
        model_file = os.path.join(model_pos_dir, f"potential_model_{position_group_for_prediction.lower()}{model_file_name_suffix}.joblib")
        scaler_file = os.path.join(model_pos_dir, f"feature_scaler_{position_group_for_prediction.lower()}{model_file_name_suffix}.joblib")
        config_file = os.path.join(model_pos_dir, f"model_config_{position_group_for_prediction.lower()}{model_file_name_suffix}.json")

        if not all(os.path.exists(p) for p in [model_file, scaler_file, config_file]):
            logger.error(f"Missing files for model {effective_model_id_for_path}, Pos {position_group_for_prediction}.")
            logger.error(f"  Checked model: {model_file}")
            logger.error(f"  Checked scaler: {scaler_file}")
            logger.error(f"  Checked config: {config_file}")
            return jsonify({"error": f"Missing files for model ID {effective_model_id_for_path}, Pos {position_group_for_prediction}"}), 404
        
        model_to_load = joblib.load(model_file); scaler_to_load = joblib.load(scaler_file)
        with open(config_file, 'r') as f_cfg: model_cfg = json.load(f_cfg)
        expected_ml_feature_names_for_model = model_cfg.get("features_used_for_ml_model", [])
        if not expected_ml_feature_names_for_model: return jsonify({"error": f"Feature list missing in config for model {effective_model_id_for_path}"}), 500

        # Feature Extraction usando funcions del trainer
        player_seasons_all = player_metadata.get("seasons", [])
        if not player_seasons_all: return jsonify({"error": "No seasons for player"}), 404
        
        df_all_base_features_for_player_list_pred = []
        try:
            minutes_df_global = pd.read_csv(PLAYER_MINUTES_PATH)
            minutes_df_global['season_name_std'] = minutes_df_global['season_name'].str.replace('/', '_', regex=False)
        except FileNotFoundError:
            logger.error(f"Player minutes file '{PLAYER_MINUTES_PATH}' not found for prediction.")
            return jsonify({"error": f"Player minutes file not found."}), 500

        target_s_numeric_pred = int(season_to_predict_for.split('_')[0])
        all_base_metric_names_from_trainer = trainer_get_feature_names() # Obtenir noms de mètriques base una vegada

        for s_hist_or_current_pred in sorted(player_seasons_all):
            s_numeric_hist_pred = int(s_hist_or_current_pred.split('_')[0])
            if s_numeric_hist_pred > target_s_numeric_pred: continue # Només temporades anteriors o actual
            
            age_for_this_s_pred = get_age_at_fixed_point_in_season(dob, s_hist_or_current_pred)
            if age_for_this_s_pred is None: continue
            # Permetre la temporada actual per a la predicció fins i tot si > 21, però l'historial ha de ser U21
            if age_for_this_s_pred > 21 and s_hist_or_current_pred != season_to_predict_for :
                 # logger.debug(f"Skipping season {s_hist_or_current_pred} for history, age {age_for_this_s_pred} > 21")
                 continue

            player_minutes_row_hist_pred = minutes_df_global[(minutes_df_global['player_id'].astype(str) == player_id_str) & (minutes_df_global['season_name_std'] == s_hist_or_current_pred)]
            total_minutes_hist_pred = player_minutes_row_hist_pred['total_minutes_played'].iloc[0] if not player_minutes_row_hist_pred.empty else 0.0
            # ÚS DE trainer_safe_division SI CAL:
            num_90s_hist_pred = trainer_safe_division(total_minutes_hist_pred, 90.0)
            
            df_events_hist_pred = load_player_data(player_id_str, s_hist_or_current_pred, DATA_DIR) # load_player_data ja usa safe_literal_eval
            if df_events_hist_pred is None: df_events_hist_pred = pd.DataFrame()

            # ÚS DE LA FUNCIÓ IMPORTADA DEL TRAINER:
            # Nota: trainer_extract_base_features espera que parse_location i is_progressive estiguin definides
            # globalment dins de trainer.py o que siguin passades/importades per trainer_extract_base_features.
            # Ja les hem importat com trainer_parse_location, etc. Hem d'assegurar que trainer_extract_base_features les utilitzi.
            # La versió de trainer.py que vas proporcionar ja fa servir les seves pròpies funcions parse_location/is_progressive internes.
            base_features_for_s_hist_pred = trainer_extract_base_features(df_events_hist_pred, age_for_this_s_pred, s_numeric_hist_pred, num_90s_hist_pred)
            
            base_features_for_s_hist_pred['player_id_identifier'] = player_id_str
            base_features_for_s_hist_pred['target_season_identifier'] = s_hist_or_current_pred # Aquesta és la temporada de les dades base
            base_features_for_s_hist_pred['season_numeric'] = s_numeric_hist_pred # Assegurar que season_numeric hi és per ordenar
            base_features_for_s_hist_pred['general_position_identifier'] = trainer_get_general_position(primary_pos_str)
            df_all_base_features_for_player_list_pred.append(base_features_for_s_hist_pred)

        if not df_all_base_features_for_player_list_pred: 
            return jsonify({"error": "Insufficient historical/current data for base feature extraction."}), 404
        
        df_all_base_features_for_player_df_pred = pd.DataFrame(df_all_base_features_for_player_list_pred).fillna(0.0)
        
        # Trobar la fila de la temporada actual per a la predicció
        current_season_data_row_for_ml = df_all_base_features_for_player_df_pred[
            df_all_base_features_for_player_df_pred['target_season_identifier'] == season_to_predict_for
        ]
        if current_season_data_row_for_ml.empty:
            return jsonify({"error": f"Base features for target season {season_to_predict_for} not found after extraction."}), 404
        current_season_data_row_for_ml = current_season_data_row_for_ml.iloc[0]

        # Preparar dades històriques per a la funció de construcció de ML
        historical_df_for_ml = df_all_base_features_for_player_df_pred[
            df_all_base_features_for_player_df_pred['season_numeric'] < target_s_numeric_pred
        ].sort_values(by='season_numeric') # Assegurar ordre per a la funció del trainer

        # ÚS DE LA FUNCIÓ IMPORTADA DEL TRAINER PER AL PASS 2:
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
                aligned_features_df_pred[col] = 0.0 # Omplir amb 0 segons la lògica prèvia
        
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
            "model_used": model_identifier, # Retorna l'ID que va demanar el frontend
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

@app.route("/goalkeeper_stats")
def goalkeeper_stats_single_season_summary():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season or season == "all":
        return jsonify({"error": "Missing player_id or specific season. For all seasons, use /goalkeeper_stats_all_seasons_summary."}), 400

    df_player = load_player_data(player_id, season, DATA_DIR)
    analysis = _calculate_goalkeeper_metrics(df_player, player_id)
    if analysis.get("error"): return jsonify({"stats": {}, "message": analysis["error"]})
    return jsonify({"stats": analysis.get("summary_text_stats", {})})

@app.route("/goalkeeper_stats_all_seasons")
def goalkeeper_stats_all_seasons_summary():
    player_id = request.args.get("player_id")
    if not player_id: return jsonify({"error": "Missing player_id"}), 400

    df_player_all = load_player_data(player_id, "all", DATA_DIR)
    analysis = _calculate_goalkeeper_metrics(df_player_all, player_id)
    if analysis.get("error"): return jsonify({"stats": {}, "message": analysis["error"]})
    return jsonify({"stats": analysis.get("summary_text_stats", {})})

@app.route("/goalkeeper_shot_map")
def goalkeeper_shot_map_data():
    player_id = request.args.get("player_id"); season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400

    df_player = load_player_data(player_id, season, DATA_DIR)
    analysis = _calculate_goalkeeper_metrics(df_player, player_id)
    if analysis.get("error"):
        logger.warning(f"Data for GK shot map {player_id}/{season} error: {analysis.get('error')}")
        return jsonify({"shots": [], "message": analysis.get("error")})
    return jsonify({"shots": analysis.get("raw_data_points", {}).get("shots_faced_map_data", [])})


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


@app.route("/seasonal_stats")
def seasonal_stats_route(): # Renamed
    player_id = request.args.get("player_id")
    if not player_id: return jsonify({"error": "Missing player_id"}), 400
    try:
        stats_data = []
        seasons_available = sorted([s_dir for s_dir in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, s_dir))])
        for season_name in seasons_available:
            df = load_player_data(player_id, season_name, DATA_DIR)
            if df is None or df.empty: continue
            
            shots_df = df[df.get("type") == "Shot"]
            total_xg = shots_df.get("shot_statsbomb_xg", pd.Series(dtype='float64')).sum()

            passes_df = df[df.get("type") == "Pass"].copy() # Use .copy() for modifications
            total_passes = len(passes_df)
            completed_passes = len(passes_df[passes_df.get("pass_outcome").isna()])
            pass_completion_pct = (completed_passes / total_passes * 100) if total_passes > 0 else 0.0
            
            # progressive_passes = 0
            # if "pass_end_location" in passes_df.columns:
            #     passes_df["end_loc_eval"] = passes_df["pass_end_location"].apply(safe_literal_eval)
            #     progressive_passes = len(passes_df[
            #         passes_df["end_loc_eval"].apply(lambda loc: isinstance(loc, (list,tuple)) and len(loc)>0 and loc[0] > 80)
            #     ])
            # stats_data.append({
            #     "season": season_name, "total_xg": round(float(total_xg), 2),
            #     "pass_completion_pct": round(pass_completion_pct, 1),
            #     "progressive_passes": progressive_passes
            # })
        if not stats_data: return jsonify({"error": "No data found across seasons for this player"}), 404
        return jsonify({"stats_data": stats_data})
    except Exception as e:
        logger.error(f"Error in /seasonal_stats: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/position_heatmap")
def position_heatmap_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        player_dir = os.path.join(STATIC_IMG_DIR, str(player_id))
        os.makedirs(player_dir, exist_ok=True)
        image_filename = f"{str(player_id)}_{season}_pos_heatmap.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{str(player_id)}/{image_filename}"

        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty or "location" not in df.columns:
            logger.warning(f"No data or location column for position heatmap {player_id}/{season}")
            return jsonify({"error": "No data or location column missing for heatmap"}), 404

        df["location_eval"] = df["location"].apply(safe_literal_eval)
        df_valid_loc = df[df["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)].copy()
        if df_valid_loc.empty:
            logger.warning(f"No valid location data for position heatmap {player_id}/{season}")
            return jsonify({"error": "No valid location data for heatmap"}), 404

        df_valid_loc["x"] = df_valid_loc["location_eval"].apply(lambda loc: loc[0])
        df_valid_loc["y"] = df_valid_loc["location_eval"].apply(lambda loc: loc[1])

        pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='white')
        fig, ax = pitch.draw(figsize=(4.125, 6))
        fig.set_facecolor('#22312b')

        bin_statistic = pitch.bin_statistic_positional(df_valid_loc.x, df_valid_loc.y, statistic='count', positional='full', normalize=True)
        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='coolwarm', edgecolors='#22312b')
        path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')]
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)

        plt.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return jsonify({"image_url": image_url})
    except Exception as e:
        logger.error(f"Error generating position heatmap for {player_id}/{season}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate position heatmap: {str(e)}"}), 500

@app.route("/pressure_heatmap")
def pressure_heatmap_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"image_url": None, "message": "Missing player_id or season"})
    try:
        player_dir = os.path.join(STATIC_IMG_DIR, str(player_id))
        os.makedirs(player_dir, exist_ok=True)
        image_filename = f"{str(player_id)}_{season}_pressure_heatmap.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{str(player_id)}/{image_filename}"

        df_events = load_player_data(player_id, season, DATA_DIR)
        df_pressure = pd.DataFrame()

        if df_events is not None and not df_events.empty and 'type' in df_events.columns:
            df_pressure = df_events[df_events["type"] == "Pressure"].copy()

        df_valid_loc = pd.DataFrame({"x": [], "y": []}) # Default to empty
        if not df_pressure.empty and "location" in df_pressure.columns:
            df_pressure["location_eval"] = df_pressure["location"].apply(safe_literal_eval)
            temp_df_valid_loc = df_pressure[df_pressure["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)].copy()
            if not temp_df_valid_loc.empty:
                df_valid_loc["x"] = temp_df_valid_loc["location_eval"].apply(lambda loc: loc[0])
                df_valid_loc["y"] = temp_df_valid_loc["location_eval"].apply(lambda loc: loc[1])

        pitch = Pitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#000000', line_color='#efefef')
        fig, ax = pitch.draw(figsize=(6.6, 4.125))
        fig.set_facecolor('#000000')

        if not df_valid_loc.empty and not df_valid_loc['x'].empty: # Ensure there's data to plot
            bin_statistic = pitch.bin_statistic(df_valid_loc.x, df_valid_loc.y, statistic='count', bins=(25, 25))
            if 'statistic' in bin_statistic and np.any(bin_statistic['statistic']):
                bin_statistic['statistic'] = gaussian_filter(bin_statistic['statistic'], 1)
                pcm = pitch.heatmap(bin_statistic, ax=ax, cmap='hot', edgecolors='#000000')
                cbar = fig.colorbar(pcm, ax=ax, shrink=0.6)
                cbar.outline.set_edgecolor('#efefef')
                cbar.ax.yaxis.set_tick_params(color='#efefef')
                plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#efefef')

        plt.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return jsonify({"image_url": image_url})
    except Exception as e:
        logger.error(f"Error generating pressure heatmap for {player_id}/{season}: {e}", exc_info=True)
        return jsonify({"image_url": None, "error": f"Failed to generate pressure heatmap: {str(e)}"})


@app.route("/xg_goal_trend")
def xg_goal_trend_route():
    player_id = request.args.get("player_id")
    if not player_id:
        return jsonify({"error": "Missing player_id"}), 400
    
    try:
        # Trobar les metadades del jugador per obtenir la llista de temporades
        player_metadata = None
        # Asumint que player_index_main_data és un diccionari de diccionaris o una llista de diccionaris
        if isinstance(player_index_main_data, dict):
            player_metadata = next((data for name, data in player_index_main_data.items() if str(data.get("player_id")) == player_id), None)
        elif isinstance(player_index_main_data, list):
             player_metadata = next((data for data in player_index_main_data if str(data.get("player_id")) == player_id), None)

        if not player_metadata:
            logger.warning(f"Player metadata not found for ID {player_id} in xg_goal_trend")
            return jsonify({"error": "Player not found"}), 404

        player_seasons = sorted(player_metadata.get("seasons", []))
        if not player_seasons:
            logger.warning(f"No seasons found for player ID {player_id} in xg_goal_trend")
            return jsonify({"trend_data": []}), 200 # Retornar llista buida si no hi ha temporades

        trend_data_list = []

        for season_str in player_seasons:
            df_season_events = load_player_data(player_id, season_str, DATA_DIR) # La teva funció existent
            
            if df_season_events is None or df_season_events.empty:
                # Afegir entrada per a la temporada fins i tot si no hi ha dades d'esdeveniments, amb valors 0
                trend_data_list.append({
                    "season": season_str,
                    "goals": 0,
                    "total_xg": 0.0,
                    "shots_taken": 0,
                    "avg_xg_per_shot": 0.0
                })
                continue

            # Filtrar per esdeveniments de tipus 'Shot'
            shots_df = df_season_events[df_season_events.get("type") == "Shot"].copy() # .copy() per evitar SettingWithCopyWarning

            if shots_df.empty:
                trend_data_list.append({
                    "season": season_str,
                    "goals": 0,
                    "total_xg": 0.0,
                    "shots_taken": 0,
                    "avg_xg_per_shot": 0.0
                })
                continue
            
            # Calcular Gols
            # Assegurar que la columna 'shot_outcome' existeix abans d'intentar accedir-hi
            if 'shot_outcome' in shots_df.columns:
                goals = int((shots_df["shot_outcome"] == "Goal").sum())
            else:
                goals = 0
                logger.warning(f"Column 'shot_outcome' not found in shots_df for player {player_id}, season {season_str}")


            # Calcular Total xG
            # Assegurar que la columna 'shot_statsbomb_xg' existeix i convertir a numèric
            if 'shot_statsbomb_xg' in shots_df.columns:
                shots_df["shot_statsbomb_xg_numeric"] = pd.to_numeric(shots_df["shot_statsbomb_xg"], errors='coerce').fillna(0.0)
                total_xg = float(shots_df["shot_statsbomb_xg_numeric"].sum())
            else:
                total_xg = 0.0
                logger.warning(f"Column 'shot_statsbomb_xg' not found in shots_df for player {player_id}, season {season_str}")


            # Calcular Shots Taken
            shots_taken = len(shots_df)

            # Calcular Avg xG per Shot
            avg_xg_per_shot = trainer_safe_division(total_xg, shots_taken, default=0.0) # Utilitza trainer_safe_division importat

            trend_data_list.append({
                "season": season_str,
                "goals": goals,
                "total_xg": round(total_xg, 3), # Més precisió per a xG
                "shots_taken": shots_taken,
                "avg_xg_per_shot": round(avg_xg_per_shot, 3)
            })
            
        return jsonify({"trend_data": trend_data_list})

    except Exception as e:
        logger.error(f"Error in /xg_goal_trend for player_id {player_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/available_aggregated_metrics")
def available_aggregated_metrics_route():
    try:
        # Aquests són els noms de les columnes generades per trainer_extract_base_features
        # L'usuari podria voler veure l'evolució de qualsevol d'aquestes.
        base_features = trainer_get_feature_names() 
        
        # Podem filtrar o categoritzar aquestes mètriques si volem
        # Per ara, les retornem totes. Podríem afegir etiquetes amigables aquí.
        
        # Creem etiquetes més amigables per al frontend
        # (Pots reutilitzar o adaptar la funció formatMlFeatureName de ScoutingPage si la portes al backend,
        # o crear una nova funció de mapeig aquí)
        
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
            # Capitalitzar
            label = ' '.join(word.capitalize() for word in label.split(' '))
            return label

        formatted_metrics = [
            {"id": name, "label": format_base_feature_label(name)}
            for name in base_features
            if not name.startswith("player_") and \
               not name.startswith("target_season_") and \
               not name.startswith("general_position_") and \
               not name.startswith("matches_played_") and \
               not name == "season_numeric" # Excloure mètriques d'identificació/context menys rellevants per a gràfics de tendència directa
        ]
        
        # Ordenar per etiqueta per a una millor presentació
        formatted_metrics.sort(key=lambda x: x["label"])
        
        return jsonify({"available_metrics": formatted_metrics})
    except Exception as e:
        logger.error(f"Error in /available_aggregated_metrics: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/player_seasonal_metric_trend")
def player_seasonal_metric_trend_route():
    player_id = request.args.get("player_id")
    metric_to_aggregate = request.args.get("metric") # Ex: "goals_p90", "sum_xg", "pass_completion_rate_kpi"

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

        # Obtenir minuts jugats per a totes les temporades del jugador (per calcular P90 si cal)
        # (Això ja ho fas dins del bucle, però podria ser optimitzat si es carrega un cop)
        try:
            minutes_df_global = pd.read_csv(PLAYER_MINUTES_PATH)
            minutes_df_global['season_name_std'] = minutes_df_global['season_name'].str.replace('/', '_', regex=False)
        except FileNotFoundError:
            logger.error(f"Player minutes file '{PLAYER_MINUTES_PATH}' not found for trend.")
            return jsonify({"error": "Player minutes file not found."}), 500

        trend_data_list = []
        all_possible_base_features = trainer_get_feature_names() # Per validar 'metric_to_aggregate'

        if metric_to_aggregate not in all_possible_base_features:
            return jsonify({"error": f"Metric '{metric_to_aggregate}' is not a valid aggregatable metric."}), 400

        for season_str in player_seasons:
            # Obtenir dades base per a la temporada
            # (Aquesta part és similar a la de /scouting_predict per obtenir característiques base)
            player_minutes_row = minutes_df_global[
                (minutes_df_global['player_id'].astype(str) == player_id) & 
                (minutes_df_global['season_name_std'] == season_str)
            ]
            total_minutes = player_minutes_row['total_minutes_played'].iloc[0] if not player_minutes_row.empty else 0.0
            num_90s = trainer_safe_division(total_minutes, 90.0)
            
            # Necessitem l'edat per a trainer_extract_base_features
            # (Assumeixo que dob està a player_metadata)
            dob = player_metadata.get("dob")
            age_at_season = 0 # Default or handle if DOB is missing
            if dob:
                age_at_season = get_age_at_fixed_point_in_season(dob, season_str) or 0 
            
            season_numeric = int(season_str.split('_')[0]) # o 1 segons el format

            df_events_season = load_player_data(player_id, season_str, DATA_DIR)
            if df_events_season is None: df_events_season = pd.DataFrame()
            
            base_features_series = trainer_extract_base_features(
                df_events_season, 
                age_at_season, 
                season_numeric, 
                num_90s
            )
            
            metric_value = base_features_series.get(metric_to_aggregate, 0.0) # Obtenir el valor de la mètrica
            if pd.isna(metric_value):
                metric_value = 0.0
            
            trend_data_list.append({
                "season": season_str,
                "value": float(metric_value), # Assegurar que és un float
                "metric_name": metric_to_aggregate # Mantenir per si el frontend el necessita
            })
        
        # Generar una etiqueta amigable per al gràfic
        # Pots reutilitzar la funció format_base_feature_label aquí
        metric_label_friendly = format_base_feature_label(metric_to_aggregate) # Assegura't que format_base_feature_label està definida

        return jsonify({
            "trend_data": trend_data_list, 
            "metric_label": metric_label_friendly,
            "metric_id": metric_to_aggregate
        })

    except Exception as e:
        logger.error(f"Error in /player_seasonal_metric_trend for player {player_id}, metric {metric_to_aggregate}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Funció auxiliar (si no la tens ja importada o definida)
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
    season_str = request.args.get("season") # Temporada específica
    metric_to_aggregate = request.args.get("metric")

    if not all([player_id, season_str, metric_to_aggregate]):
        return jsonify({"error": "Missing player_id, season, or metric"}), 400

    if season_str == "all":
        return jsonify({"error": "This endpoint is for single seasons only. Use /player_seasonal_metric_trend for all seasons."}), 400

    try:
        player_metadata = None
        # Asumint que player_index_main_data és un diccionari de diccionaris
        if isinstance(player_index_main_data, dict):
            player_metadata = next((data for name, data in player_index_main_data.items() if str(data.get("player_id")) == player_id), None)
        elif isinstance(player_index_main_data, list):
             player_metadata = next((data for data in player_index_main_data if str(data.get("player_id")) == player_id), None)


        if not player_metadata:
            return jsonify({"error": "Player not found"}), 404

        # Validar la mètrica
        all_possible_base_features = trainer_get_feature_names()
        if metric_to_aggregate not in all_possible_base_features:
            return jsonify({"error": f"Metric '{metric_to_aggregate}' is not a valid aggregatable metric."}), 400

        # Obtenir minuts jugats per a la temporada
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
        
        # El format de season_numeric pot variar, ajusta-ho si cal. Exemple: "2022_2023" -> 2022
        try:
            season_numeric = int(season_str.split('_')[0])
        except ValueError: # Per si la temporada no té el format esperat
            logger.error(f"Could not parse season_numeric from season_str: {season_str}")
            return jsonify({"error": f"Invalid season format: {season_str}"}), 400

        df_events_season = load_player_data(player_id, season_str, DATA_DIR)
        if df_events_season is None: 
            df_events_season = pd.DataFrame() # Per a trainer_extract_base_features
        
        base_features_series = trainer_extract_base_features(
            df_events_season, 
            age_at_season, 
            season_numeric, 
            num_90s
        )
        
        metric_value = base_features_series.get(metric_to_aggregate, 0.0)
        if pd.isna(metric_value):
            metric_value = 0.0
        
        metric_label_friendly = format_base_feature_label(metric_to_aggregate) # Funció auxiliar que ja tens

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
    load_all_v14_potential_models()
    app.run(debug=True)