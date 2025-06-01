# server-flask/model_trainer/trainer.py
import json
import pandas as pd
from datetime import datetime
import os
import numpy as np
from sklearn.model_selection import train_test_split, GroupKFold, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import warnings
import logging # Added for logging within trainer
from ast import literal_eval # Added for parse_location

logger_trainer = logging.getLogger(__name__ + "_trainer") # Specific logger for trainer

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.feature_extraction.text")
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# --- Configuration (relative to this trainer.py file if run directly, or passed if called) ---
_TRAINER_SCRIPT_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_TRAINER_SCRIPT_DIR, '..', '..')) # Goes up to REACT-FLASK
_DATA_DIR_FOR_TRAINER = os.path.join(_PROJECT_ROOT, 'data')

PLAYER_INDEX_PATH = os.path.join(_DATA_DIR_FOR_TRAINER, 'player_index.json')
BASE_EVENT_DATA_PATH = _DATA_DIR_FOR_TRAINER # Season folders are directly in data
PLAYER_MINUTES_PATH = os.path.join(_DATA_DIR_FOR_TRAINER, 'player_season_minutes_with_names.csv')


MIN_90S_PLAYED_FOR_P90_STATS = 3


CONCEPTUAL_BASE_METRICS_FOR_KPI_VARIANTS = {
    "Attacker": [
        "goals", "sum_xg", "shots_total", "shots_on_target", 
        # "sum_xA_proxy", 
        "key_passes_goal_assist", "dribbles_completed", 
        "progressive_carries", "pressures", "turnovers_total", # Nota: 'turnovers_total' per a la suma, 'turnovers_p90_inv_kpi_base' per a p90 invertit
        "aerial_duels_won"
    ],
    "Midfielder": [
        "successful_passes", 
        # "sum_xA_proxy", 
        "key_passes_goal_assist", 
        # "passes_progressive_count", 
        "progressive_carries", "dribbles_completed", 
        "interceptions", "tackles_won", "count_ball_recovery", 
        "pressures", "turnovers_total"
    ],
    "Defender": [
        "tackles_won", "interceptions", "clearances", "blocks", 
        "aerial_duels_won", "successful_passes", 
        "progressive_carries", "turnovers_total"
    ],
    "CommonDirectKPIs": [ # KPIs que no tenen variants p90/sqrt de la mateixa manera, o són directes
        "conversion_rate_excl_xg_kpi", "pass_completion_rate_kpi",
        "tackle_win_rate_kpi", "aerial_duel_win_rate_kpi",
        # 'turnovers_p90_inv_kpi' es tractarà com una variant de 'turnovers_total' o 'turnovers_p90_inv_kpi_base'
    ]
}

# Funció auxiliar per generar variants per a una mètrica base
def generate_kpi_variants(base_name, include_sum=True, include_p90=True, include_p90_sqrt=False):
    variants = []
    if include_sum:
        variants.append(base_name) # La versió "suma" és el nom base
    if include_p90:
        variants.append(f"{base_name}_p90")
    if include_p90_sqrt: # Normalment per a mètriques que es vol suavitzar i són p90
        if include_p90: # Només té sentit si ja hi ha p90
             variants.append(f"{base_name}_p90_sqrt_")
        else: # Si no hi ha p90, però es vol sqrt del nom base (menys comú per a la nostra estructura actual)
             variants.append(f"{base_name}_sqrt_") 
    return variants


KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION = {
    "Attacker": 
        generate_kpi_variants("goals", include_p90_sqrt=True) +
        generate_kpi_variants("sum_xg", include_p90_sqrt=True) +
        generate_kpi_variants("shots_total") +
        generate_kpi_variants("shots_on_target") +
        ["conversion_rate_excl_xg_kpi"] + # KPI directe
        # generate_kpi_variants("sum_xA_proxy", include_p90_sqrt=True) +
        generate_kpi_variants("key_passes_goal_assist", include_p90=True) + # key_passes_goal_assist_p90_sqrt_ no sol ser estàndard
        generate_kpi_variants("dribbles_completed") +
        generate_kpi_variants("progressive_carries") + # Aquest és un àlies de count_carry_p90, però el base és count_carry
        generate_kpi_variants("pressures") + # àlies de count_pressure_p90, base count_pressure
        ["turnovers_p90_inv_kpi_base"] + # Nom específic per a la versió p90 invertida
        generate_kpi_variants("aerial_duels_won"),

    "Midfielder": 
        generate_kpi_variants("successful_passes") +
        ["pass_completion_rate_kpi"] +
        # generate_kpi_variants("sum_xA_proxy", include_p90_sqrt=True) +
        generate_kpi_variants("key_passes_goal_assist", include_p90=True) +
        # generate_kpi_variants("passes_progressive_count") +
        generate_kpi_variants("progressive_carries") +
        generate_kpi_variants("dribbles_completed") +
        generate_kpi_variants("interceptions") + # àlies de count_interception_p90
        generate_kpi_variants("tackles_won") +
        generate_kpi_variants("count_ball_recovery") + # Ja és un recompte, es pot fer p90
        generate_kpi_variants("pressures") +
        ["turnovers_p90_inv_kpi_base"],

    "Defender":
        generate_kpi_variants("tackles_won") +
        ["tackle_win_rate_kpi"] +
        generate_kpi_variants("interceptions") +
        generate_kpi_variants("clearances") + # àlies de count_clearance_p90
        generate_kpi_variants("blocks") +    # àlies de count_block_p90
        generate_kpi_variants("aerial_duels_won") +
        ["aerial_duel_win_rate_kpi"] +
        generate_kpi_variants("successful_passes") +
        ["pass_completion_rate_kpi"] +
        generate_kpi_variants("progressive_carries") +
        ["turnovers_p90_inv_kpi_base"],
}

for pos, kpis in KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION.items():
    KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION[pos] = sorted(list(set(kpis)))


COMPOSITE_IMPACT_KPIS = {
    "Attacker": ["sum_xg_p90_sqrt_", "goals_p90_sqrt_", "dribbles_completed_p90"],
    "Midfielder": [
        # "passes_progressive_count_p90", "sum_xA_proxy_p90_sqrt_", 
        "interceptions_p90", "key_passes_goal_assist_p90"],
    "Defender": ["tackles_won_p90", "interceptions_p90", "aerial_duels_won_p90"]
}

# --- Helper Functions (Copied from your original script) ---
def get_age_at_fixed_point_in_season(dob_str, season_str):
    try:
        birth_date = datetime.strptime(dob_str, "%Y-%m-%d")
        season_end_year = int(season_str.split('_')[1])
        fixed_date_in_season = datetime(season_end_year, 1, 1)
        age = fixed_date_in_season.year - birth_date.year - \
              ((fixed_date_in_season.month, fixed_date_in_season.day) < (birth_date.month, birth_date.day))
        return age
    except Exception: return None

def get_general_position(specific_position):
    if not isinstance(specific_position, str): return "Unknown"
    sp_lower = specific_position.lower()
    if "goalkeeper" in sp_lower: return "Goalkeeper"
    elif "forward" in sp_lower or "striker" in sp_lower or ("wing" in sp_lower and "back" not in sp_lower): return "Attacker"
    elif "midfield" in sp_lower: return "Midfielder"
    elif "back" in sp_lower or "defender" in sp_lower: return "Defender"
    else: return "Unknown"

def safe_division(numerator, denominator, default=0.0):
    if denominator is None or pd.isna(denominator) or denominator == 0 or denominator == 0.0: return default
    if numerator is None or pd.isna(numerator): return default
    try: return float(numerator) / float(denominator)
    except (TypeError, ValueError): return default

def parse_location(loc_str):
    try:
        if pd.isna(loc_str) or not isinstance(loc_str, str): return None
        # Make sure it's a string representation of a list/tuple before literal_eval
        if not (loc_str.startswith('[') and loc_str.endswith(']')) and \
           not (loc_str.startswith('(') and loc_str.endswith(')')):
             # Try splitting if it's just comma-separated numbers without brackets
            parts = loc_str.split(',')
            if len(parts) >= 2:
                return tuple(map(float, parts))
            return None
        return tuple(map(float, literal_eval(loc_str.strip('[]()'))))
    except: return None


# def is_progressive(start_loc_tuple, end_loc_tuple, min_prog_dist=10.0):
#     if start_loc_tuple is None or end_loc_tuple is None or \
#        not all(isinstance(c, (int, float)) and pd.notna(c) for c in start_loc_tuple + end_loc_tuple) or \
#        len(start_loc_tuple) < 2 or len(end_loc_tuple) < 2:
#         return False
#     start_x, _ = start_loc_tuple; end_x, _ = end_loc_tuple
#     if (end_x - start_x) >= min_prog_dist: return True
#     if start_x < 60 and end_x >= 60 and (end_x - start_x) >= min_prog_dist / 2: return True
#     if start_x >= 60 and end_x > start_x and (end_x - start_x) >= min_prog_dist / 3: return True
#     return False

def get_feature_names_for_extraction():
    kpi_direct_names = ['conversion_rate_excl_xg_kpi', 'xg_performance', 'pass_completion_rate_kpi',
                        'avg_pass_length_kpi', 'dribble_success_rate_kpi', 'tackle_win_rate_kpi',
                        'aerial_duel_win_rate_kpi', 'turnovers_p90_inv_kpi_base']
    event_types_suffixes = ['pass', 'shot', 'dribble', 'duel', 'interception', 'clearance', 'foul_committed',
                            'foul_won', 'ball_recovery', 'miscontrol', 'dispossessed', 'pressure', 'carry', 'block', '50_50']
    raw_counts = [f'count_{suffix}' for suffix in event_types_suffixes]
    other_raw_aggregates = [
        'shots_total', 'goals', 'shots_on_target', 'sum_xg', 'count_shot_first_time', 'passes_total',
        'successful_passes', 'avg_pass_length', 'key_passes_goal_assist', 'key_passes_shot_assist',
        'crosses', 'switches', 'through_balls', 
        # 'passes_progressive_count', 'sum_xA_proxy',
        'dribbles_attempted', 'dribbles_completed', 'tackles_attempted', 'tackles_won',
        'aerial_duels_total', 'aerial_duels_won', 'counterpress_events', 'events_under_pressure', 'turnovers_total']
    
    metrics_for_p90_conversion = [
        'shots_total', 'goals', 'shots_on_target', 'sum_xg', 'count_shot_first_time', 
        'passes_total', 'successful_passes', 'avg_pass_length',
        'key_passes_goal_assist', 'key_passes_shot_assist', 
        'crosses', 'switches', 'through_balls', 
        # 'passes_progressive_count', 'sum_xA_proxy',
        'dribbles_attempted', 'dribbles_completed', 'count_dribble',
        'tackles_attempted', 'tackles_won', 'count_duel',
        'aerial_duels_total', 'aerial_duels_won', 'count_interception', 'count_clearance', 
        'count_block', 'count_ball_recovery', 'count_miscontrol', 'count_dispossessed',
        'turnovers_total', 'count_pressure', 'counterpress_events', 'events_under_pressure', 'count_carry',
        'count_foul_committed', 'count_foul_won', 'count_50_50',
        'count_pass', 'count_shot'
    ]
    p90_versions = [f"{m}_p90" for m in metrics_for_p90_conversion]
    p90_aliases = ['progressive_carries_p90', 'interceptions_p90', 'clearances_p90', 'blocks_p90', 'pressures_p90']
    sqrt_transformed_kpis_base_p90 = ["goals_p90", "sum_xg_p90", "key_passes_goal_assist_p90"]
    sqrt_transformed_kpis = [f"{b}_sqrt_" for b in sqrt_transformed_kpis_base_p90]
    context_features = ['age', 'season_numeric', 'num_90s_played', 'matches_played_events']
    
    all_features_set = set(
        kpi_direct_names + raw_counts + other_raw_aggregates + metrics_for_p90_conversion +
        p90_versions + p90_aliases + sqrt_transformed_kpis_base_p90 + sqrt_transformed_kpis + context_features
    )
    return sorted(list(all_features_set))


def extract_season_features(event_df, age_in_season, season_str_numeric, num_90s_played):
    s = pd.Series(dtype='float64')
    s['age'] = float(age_in_season) if age_in_season is not None else 0.0
    s['season_numeric'] = float(season_str_numeric) if season_str_numeric is not None else 0.0
    s['num_90s_played'] = float(num_90s_played) if pd.notna(num_90s_played) else 0.0
    s['matches_played_events'] = float(event_df['match_id'].nunique()) if 'match_id' in event_df.columns and not event_df.empty else 0.0
    
    use_p90 = s['num_90s_played'] >= MIN_90S_PLAYED_FOR_P90_STATS
    
    all_expected_features = get_feature_names_for_extraction()
    for fname in all_expected_features:
        if fname not in ['age', 'season_numeric', 'num_90s_played', 'matches_played_events']:
             s[fname] = 0.0

    if event_df.empty or len(event_df) == 0:
        if 'turnovers_p90_inv_kpi_base' in s.index: s['turnovers_p90_inv_kpi_base'] = 999.0
        sqrt_kpis = ["goals_p90_sqrt_", "sum_xg_p90_sqrt_", "key_passes_goal_assist_p90_sqrt_"]
        for skpi in sqrt_kpis:
            if skpi in s.index: s[skpi] = 0.0
        return s.reindex(all_expected_features).fillna(0.0)

    event_counts = event_df['type'].value_counts() if 'type' in event_df.columns else pd.Series(dtype='int64')
    event_type_map = [('Pass', 'pass'), ('Shot', 'shot'), ('Dribble', 'dribble'), ('Duel', 'duel'),
                      ('Interception', 'interception'), ('Clearance', 'clearance'),
                      ('Foul Committed', 'foul_committed'), ('Foul Won', 'foul_won'),
                      ('Ball Recovery', 'ball_recovery'), ('Miscontrol', 'miscontrol'),
                      ('Dispossessed', 'dispossessed'), ('Pressure', 'pressure'), ('Carry', 'carry'),
                      ('Block', 'block'), ('50/50', '50_50')]
    for event_type_orig, feature_suffix in event_type_map:
        if f'count_{feature_suffix}' in s.index:
            s[f'count_{feature_suffix}'] = float(event_counts.get(event_type_orig, 0))
    if s.get('count_50_50', 0) == 0 and 'duel_type' in event_df.columns and 'count_50_50' in s.index:
        s['count_50_50'] = float((event_df['duel_type'].astype(str) == '50/50').sum())

    shots_df = event_df[event_df['type'] == 'Shot'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if 'shots_total' in s.index: s['shots_total'] = float(len(shots_df))
    if s.get('shots_total', 0.0) > 0:
        shot_outcome_col = shots_df.get('shot_outcome_name', shots_df.get('shot_outcome', pd.Series(dtype=str)))
        if 'goals' in s.index: s['goals'] = float((shot_outcome_col == 'Goal').sum())
        if 'shots_on_target' in s.index: s['shots_on_target'] = float(shot_outcome_col.isin(['Saved', 'Goal', 'Post', 'Saved To Post', 'Saved Off Target']).sum())
        if 'sum_xg' in s.index: s['sum_xg'] = pd.to_numeric(shots_df.get('shot_statsbomb_xg'), errors='coerce').sum()
        if 'count_shot_first_time' in s.index: s['count_shot_first_time'] = (shots_df.get('shot_first_time', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()
    if 'conversion_rate_excl_xg_kpi' in s.index: s['conversion_rate_excl_xg_kpi'] = safe_division(s.get('goals',0.0), s.get('shots_total',0.0)) * 100
    if 'xg_performance' in s.index: s['xg_performance'] = s.get('goals',0.0) - s.get('sum_xg',0.0)

    pass_df = event_df[event_df['type'] == 'Pass'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if 'passes_total' in s.index: s['passes_total'] = float(len(pass_df))
    if s.get('passes_total', 0.0) > 0:
        if 'successful_passes' in s.index: s['successful_passes'] = float(pass_df.get('pass_outcome', pd.Series(dtype=str)).isna().sum())
        if 'avg_pass_length' in s.index: s['avg_pass_length'] = pd.to_numeric(pass_df.get('pass_length'), errors='coerce').mean()
        if 'key_passes_goal_assist' in s.index: s['key_passes_goal_assist'] = float((pass_df.get('pass_goal_assist', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'key_passes_shot_assist' in s.index: s['key_passes_shot_assist'] = float((pass_df.get('pass_shot_assist', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'crosses' in s.index: s['crosses'] = float((pass_df.get('pass_cross', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'switches' in s.index: s['switches'] = float((pass_df.get('pass_switch', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'through_balls' in s.index: s['through_balls'] = float((pass_df.get('pass_through_ball', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        
        prog_pass_count = 0; temp_xa_sum = 0.0
        xa_lookup = {}
        if not shots_df.empty and 'shot_key_pass_id' in shots_df.columns and 'shot_statsbomb_xg' in shots_df.columns:
            shots_with_kp_xg = shots_df[shots_df['shot_key_pass_id'].notna() & shots_df['shot_statsbomb_xg'].notna()].copy()
            if not shots_with_kp_xg.empty:
                shots_with_kp_xg['shot_statsbomb_xg'] = pd.to_numeric(shots_with_kp_xg['shot_statsbomb_xg'], errors='coerce').fillna(0)
                xa_lookup = shots_with_kp_xg.set_index(shots_with_kp_xg['shot_key_pass_id'].astype(str))['shot_statsbomb_xg'].to_dict()

        for _, row in pass_df.iterrows():
            start_loc = parse_location(row.get('location')); end_loc = parse_location(row.get('pass_end_location'))
        #     if is_progressive(start_loc, end_loc): prog_pass_count += 1
        #     pass_id_str = str(row.get('id'))
        #     is_shot_assist_flag = str(row.get('pass_shot_assist','false')).lower() == 'true'
        #     is_goal_assist_flag = str(row.get('pass_goal_assist','false')).lower() == 'true'
        #     if is_shot_assist_flag or is_goal_assist_flag:
        #         if pass_id_str in xa_lookup: temp_xa_sum += xa_lookup.get(pass_id_str, 0.0)
        # if 'passes_progressive_count' in s.index: s['passes_progressive_count'] = float(prog_pass_count)
        # if 'sum_xA_proxy' in s.index: s['sum_xA_proxy'] = float(temp_xa_sum)
    if 'pass_completion_rate_kpi' in s.index: s['pass_completion_rate_kpi'] = safe_division(s.get('successful_passes',0.0), s.get('passes_total',0.0)) * 100
    if 'avg_pass_length_kpi' in s.index: s['avg_pass_length_kpi'] = s.get('avg_pass_length', 0.0) if pd.notna(s.get('avg_pass_length')) else 0.0

    dribble_df = event_df[event_df['type'] == 'Dribble'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if 'dribbles_attempted' in s.index: s['dribbles_attempted'] = float(len(dribble_df))
    if 'dribble_outcome' in dribble_df.columns and not dribble_df.empty:
        dribble_outcome_col = dribble_df['dribble_outcome'].apply(lambda x: x.get('name') if isinstance(x, dict) else x)
        if 'dribbles_completed' in s.index: s['dribbles_completed'] = float((dribble_outcome_col == 'Complete').sum())
    if 'dribble_success_rate_kpi' in s.index: s['dribble_success_rate_kpi'] = safe_division(s.get('dribbles_completed', 0.0), s.get('dribbles_attempted',0.0)) * 100

    duel_df_orig = event_df[event_df['type'] == 'Duel'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not duel_df_orig.empty:
        if 'duel_type' in duel_df_orig.columns:
            duel_df_orig.loc[:, 'duel_type_name'] = duel_df_orig['duel_type'].apply(lambda x: x.get('name') if isinstance(x, dict) else str(x))
            if 'tackles_attempted' in s.index: s['tackles_attempted'] = float(duel_df_orig[duel_df_orig['duel_type_name'] == 'Tackle'].shape[0])
            aerial_duels_df_temp = duel_df_orig[duel_df_orig['duel_type_name'].str.contains("Aerial", case=False, na=False)].copy()
            if 'aerial_duels_total' in s.index: s['aerial_duels_total'] = float(len(aerial_duels_df_temp))

            if 'duel_outcome' in duel_df_orig.columns:
                duel_df_orig.loc[:, 'duel_outcome_name'] = duel_df_orig['duel_outcome'].apply(lambda x: x.get('name') if isinstance(x, dict) else str(x))
                tackle_duels_df_temp = duel_df_orig[duel_df_orig['duel_type_name'] == 'Tackle'].copy()
                if 'tackles_won' in s.index and 'duel_outcome_name' in tackle_duels_df_temp.columns:
                    s['tackles_won'] = float(tackle_duels_df_temp[tackle_duels_df_temp['duel_outcome_name'].isin(['Won', 'Success', 'Success In Play', 'Success Out'])].shape[0])
                
                aerial_duels_df_for_outcome_temp = duel_df_orig[duel_df_orig['duel_type_name'].str.contains("Aerial", case=False, na=False)].copy()
                if not aerial_duels_df_for_outcome_temp.empty and 'duel_outcome_name' in aerial_duels_df_for_outcome_temp.columns and 'aerial_duels_won' in s.index:
                     s['aerial_duels_won'] = float(aerial_duels_df_for_outcome_temp[aerial_duels_df_for_outcome_temp['duel_outcome_name'].isin(['Won', 'Success'])].shape[0])

    if 'tackle_win_rate_kpi' in s.index: s['tackle_win_rate_kpi'] = safe_division(s.get('tackles_won',0.0), s.get('tackles_attempted',0.0)) * 100
    if 'aerial_duel_win_rate_kpi' in s.index: s['aerial_duel_win_rate_kpi'] = safe_division(s.get('aerial_duels_won',0.0), s.get('aerial_duels_total',0.0)) * 100
    
    if 'counterpress_events' in s.index: s['counterpress_events'] = (event_df.get('counterpress', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()
    if 'events_under_pressure' in s.index: s['events_under_pressure'] = (event_df.get('under_pressure', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()
    if 'turnovers_total' in s.index:
        s['turnovers_total'] = s.get('count_miscontrol', 0.0) + s.get('count_dispossessed', 0.0) + \
                               (s.get('dribbles_attempted', 0.0) - s.get('dribbles_completed', 0.0))
    if 'turnovers_p90_inv_kpi_base' in s.index:
        s['turnovers_p90_inv_kpi_base'] = safe_division(s.get('turnovers_total',0.0), num_90s_played) if use_p90 else (999.0 if s.get('turnovers_total',0.0) == 0 else s.get('turnovers_total',0.0))

    metrics_for_p90_conversion = [
        'shots_total', 'goals', 'shots_on_target', 'sum_xg', 'count_shot_first_time', 
        'passes_total', 'successful_passes', 'avg_pass_length',
        'key_passes_goal_assist', 'key_passes_shot_assist', 
        'crosses', 'switches', 'through_balls', 
        # 'passes_progressive_count', 'sum_xA_proxy',
        'dribbles_attempted', 'dribbles_completed', 'count_dribble',
        'tackles_attempted', 'tackles_won', 'count_duel',
        'aerial_duels_total', 'aerial_duels_won', 'count_interception', 'count_clearance', 
        'count_block', 'count_ball_recovery', 'count_miscontrol', 'count_dispossessed',
        'turnovers_total', 'count_pressure', 'counterpress_events', 'events_under_pressure', 'count_carry',
        'count_foul_committed', 'count_foul_won', 'count_50_50',
        'count_pass', 'count_shot'
    ]
    for col_raw in metrics_for_p90_conversion:
        if f'{col_raw}_p90' in s.index:
            s[f'{col_raw}_p90'] = safe_division(s.get(col_raw, 0.0), num_90s_played) if use_p90 else 0.0
    
    p90_aliases_map = {
        'progressive_carries_p90': 'count_carry_p90', 
        'interceptions_p90': 'count_interception_p90',
        'clearances_p90': 'count_clearance_p90',
        'blocks_p90': 'count_block_p90',
        'pressures_p90': 'count_pressure_p90'
    }
    for alias, base_p90_col in p90_aliases_map.items():
        if alias in s.index:
            s[alias] = s.get(base_p90_col, 0.0)

    sqrt_transformed_kpis_base_p90 = ["goals_p90", "sum_xg_p90", "key_passes_goal_assist_p90"]
    for kpi_base_name in sqrt_transformed_kpis_base_p90:
        if f"{kpi_base_name}_sqrt_" in s.index:
            val = s.get(kpi_base_name, 0.0)
            s[f"{kpi_base_name}_sqrt_"] = np.sqrt(val) if pd.notna(val) and val > 0 else 0.0
        
    return s.reindex(all_expected_features).fillna(0.0)


def derive_kpi_weights_from_impact_correlation(df_all_features, position_group, impact_kpi_list, kpi_definitions_for_pos):
    pos_df = df_all_features[df_all_features['general_position_identifier'] == position_group].copy()
    if pos_df.empty or len(impact_kpi_list) == 0 or len(kpi_definitions_for_pos) == 0:
        logger_trainer.warning(f"    Trainer: Not enough data or definitions to derive weights for {position_group}. Using equal weights.")
        return {kpi: 1.0/len(kpi_definitions_for_pos) if kpi_definitions_for_pos else 1.0 for kpi in kpi_definitions_for_pos}

    impact_score_components_normalized = pd.DataFrame(index=pos_df.index)
    for kpi_impact_comp_orig in impact_kpi_list:
        kpi_impact_comp = kpi_impact_comp_orig.replace('_inv_kpi', '_inv_kpi_base') if kpi_impact_comp_orig.endswith('_inv_kpi') else kpi_impact_comp_orig
        if kpi_impact_comp in pos_df.columns:
            col_data = pos_df[kpi_impact_comp].copy()
            if kpi_impact_comp.endswith(('_p90', '_sqrt_')) and 'num_90s_played' in pos_df.columns:
                reliable_mask_pos = pos_df['num_90s_played'] >= MIN_90S_PLAYED_FOR_P90_STATS
                col_data_reliable = col_data[reliable_mask_pos]
                if not col_data_reliable.empty and col_data_reliable.nunique() > 1:
                    scaler_impact_comp = MinMaxScaler()
                    scaled_reliable = scaler_impact_comp.fit_transform(col_data_reliable.values.reshape(-1,1)).flatten()
                    impact_score_components_normalized[kpi_impact_comp] = pd.Series(np.nan, index=col_data.index)
                    impact_score_components_normalized.loc[reliable_mask_pos, kpi_impact_comp] = scaled_reliable
                    impact_score_components_normalized[kpi_impact_comp].fillna(0.0, inplace=True)
                elif not col_data_reliable.empty:
                    impact_score_components_normalized[kpi_impact_comp] = 0.5 
                    impact_score_components_normalized.loc[~reliable_mask_pos, kpi_impact_comp] = 0.0
                else: impact_score_components_normalized[kpi_impact_comp] = 0.0
            elif col_data.nunique() > 1:
                scaler_impact_comp = MinMaxScaler()
                impact_score_components_normalized[kpi_impact_comp] = scaler_impact_comp.fit_transform(col_data.values.reshape(-1,1)).flatten()
            else: impact_score_components_normalized[kpi_impact_comp] = 0.5 if col_data.notna().any() else 0.0
        else:
            logger_trainer.warning(f"    Trainer: Impact KPI {kpi_impact_comp} not found in features for {position_group}. Assigning 0 for impact.")
            impact_score_components_normalized[kpi_impact_comp] = 0.0
    
    pos_df['composite_impact_score'] = impact_score_components_normalized.sum(axis=1)
    correlations = {}
    for kpi_to_weight in kpi_definitions_for_pos:
        data_col_for_corr = kpi_to_weight.replace('_inv_kpi', '_inv_kpi_base') if kpi_to_weight.endswith('_inv_kpi') else kpi_to_weight
        if data_col_for_corr in pos_df.columns and \
           pos_df['composite_impact_score'].nunique() > 1 and \
           pos_df[data_col_for_corr].nunique() > 1:
            corr_series_data = pos_df[data_col_for_corr].copy()
            if kpi_to_weight.endswith('_inv_kpi'):
                max_val, min_val = corr_series_data.max(), corr_series_data.min()
                if max_val > min_val : corr_series_data = (max_val - corr_series_data) / (max_val - min_val)
                elif corr_series_data.notna().any(): corr_series_data[:] = 0.5
                else: corr_series_data[:] = 0.0
            correlation = pos_df['composite_impact_score'].corr(corr_series_data)
            correlations[kpi_to_weight] = abs(correlation if pd.notna(correlation) else 0.0)
        else: correlations[kpi_to_weight] = 0.0
    abs_correlations_sum = sum(correlations.values())
    if abs_correlations_sum == 0:
        num_kpis = len(kpi_definitions_for_pos)
        return {kpi: 1.0/num_kpis if num_kpis > 0 else 1.0 for kpi in kpi_definitions_for_pos}
    return {kpi: val / abs_correlations_sum for kpi, val in correlations.items()}


def generate_potential_target(df_all_u21_seasons, derived_kpi_weights_config):
    df = df_all_u21_seasons.copy()
    df['raw_composite_score'] = 0.0
    df['potential_target'] = 0.0
    
    global_percentiles = {}
    all_kpi_cols_for_norm = list(set(kpi for weights_dict in derived_kpi_weights_config.values() for kpi in weights_dict.keys()))

    for kpi_col_name in all_kpi_cols_for_norm:
        data_col_for_percentile = kpi_col_name.replace('_inv_kpi', '_inv_kpi_base') if kpi_col_name.endswith('_inv_kpi') else kpi_col_name
        
        if data_col_for_percentile in df.columns:
            data_values = df[data_col_for_percentile].copy()
            if data_col_for_percentile.endswith(('_p90', '_sqrt_', '_base')):
                if 'num_90s_played' in df.columns:
                    reliable_mask = df['num_90s_played'] >= MIN_90S_PLAYED_FOR_P90_STATS
                    if reliable_mask.sum() > 0: data_values = data_values[reliable_mask]
            
            if not data_values.empty and data_values.nunique() > 1:
                 global_percentiles[kpi_col_name] = {'p05': data_values.quantile(0.05), 'p95': data_values.quantile(0.95)}
            else: global_percentiles[kpi_col_name] = {'p05': df[data_col_for_percentile].min(), 'p95': df[data_col_for_percentile].max()}
        else: global_percentiles[kpi_col_name] = {'p05': 0.0, 'p95': 0.0}

    for position_group, weights in derived_kpi_weights_config.items():
        pos_mask = (df['general_position_identifier'] == position_group)
        if pos_mask.sum() == 0: continue
        
        current_total_weight = sum(w for w in weights.values() if isinstance(w, (int, float)))
        if current_total_weight == 0: current_total_weight = 1.0

        position_composite_score = pd.Series(0.0, index=df[pos_mask].index)

        for kpi_col_name_in_weights, weight_value in weights.items():
            actual_weight = safe_division(weight_value, current_total_weight)
            is_inverted_kpi = kpi_col_name_in_weights.endswith('_inv_kpi')
            data_col_for_calc = kpi_col_name_in_weights.replace('_inv_kpi', '_inv_kpi_base') if is_inverted_kpi else kpi_col_name_in_weights
            
            if data_col_for_calc not in df.columns: continue
            
            kpi_data_for_pos = df.loc[pos_mask, data_col_for_calc].copy()
            
            percentile_info = global_percentiles.get(kpi_col_name_in_weights)
            if percentile_info:
                p05, p95 = percentile_info['p05'], percentile_info['p95']
                if pd.notna(p05) and pd.notna(p95):
                    kpi_data_for_pos.clip(lower=p05, upper=p95, inplace=True)
            
            min_val_pos_clipped, max_val_pos_clipped = kpi_data_for_pos.min(), kpi_data_for_pos.max()
            
            norm_value_series = pd.Series(0.5, index=kpi_data_for_pos.index)
            if not pd.isna(min_val_pos_clipped) and not pd.isna(max_val_pos_clipped) and max_val_pos_clipped > min_val_pos_clipped :
                norm_value_series = (kpi_data_for_pos - min_val_pos_clipped) / (max_val_pos_clipped - min_val_pos_clipped)
            
            if data_col_for_calc.endswith(('_p90', '_sqrt_', '_base')):
                 if 'num_90s_played' in df.columns:
                    low_mins_mask_on_norm_series = df.loc[norm_value_series.index, 'num_90s_played'] < MIN_90S_PLAYED_FOR_P90_STATS
                    if is_inverted_kpi:
                        norm_value_series[low_mins_mask_on_norm_series] = 1.0
                    else:
                        norm_value_series[low_mins_mask_on_norm_series] = 0.0

            if is_inverted_kpi:
                position_composite_score += (1 - norm_value_series.fillna(0.5)) * actual_weight
            else:
                position_composite_score += norm_value_series.fillna(0.0) * actual_weight
        
        df.loc[pos_mask, 'raw_composite_score'] = position_composite_score

        if pos_mask.sum() > 0:
            min_raw_score_group = df.loc[pos_mask, 'raw_composite_score'].min()
            max_raw_score_group = df.loc[pos_mask, 'raw_composite_score'].max()
            
            if max_raw_score_group == min_raw_score_group or pd.isna(max_raw_score_group) or pd.isna(min_raw_score_group):
                df.loc[pos_mask, 'potential_target'] = 100.0
            else:
                scaled_potential = ((df.loc[pos_mask, 'raw_composite_score'] - min_raw_score_group) / 
                                   (max_raw_score_group - min_raw_score_group)) * 200.0
                df.loc[pos_mask, 'potential_target'] = scaled_potential.clip(0, 200).round(2)
                
    return df[['player_id_identifier', 'target_season_identifier', 'potential_target', 'raw_composite_score']]


def trainer_save_model_run_config(filepath, model_name, feature_cols, model_params, 
                                  user_kpi_definitions_for_weights,
                                  user_composite_impact_kpis,
                                  derived_kpi_weights_actually_used,
                                  position_group_trained,
                                  best_params_from_search=None,
                                  evaluation_metrics=None): # Added evaluation_metrics
    safe_model_params = {}
    actual_params_to_save = best_params_from_search if best_params_from_search else model_params
    for k, v in actual_params_to_save.items():
        if isinstance(v, (np.int_, np.integer, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64,
                        np.uint8, np.uint16, np.uint32, np.uint64)): safe_model_params[k] = int(v)
        elif isinstance(v, (np.float_, np.floating, np.float16, np.float32, np.float64)): safe_model_params[k] = float(v)
        elif isinstance(v, np.ndarray): safe_model_params[k] = v.tolist()
        elif isinstance(v, (bool, np.bool_)): safe_model_params[k] = bool(v)
        else: safe_model_params[k] = v
    
    config = {
        "model_type": f"{model_name}_for_{position_group_trained}",
        "description": f"Custom Model: Position-Specific ({position_group_trained}) XGBoost. Target derived from user-selected KPIs. Weights derived via correlation. Hyperparameter search performed.",
        "features_used_for_ml_model": feature_cols,
        "ml_model_parameters": safe_model_params,
        "target_variable_generation": {
            "method": "User-selected KPIs used for impact score & target definition. Weights derived via correlation. Global percentile clipping, then position-group MinMax normalization. Scaled 0-200.",
            "user_selected_kpi_definitions_for_target_weights": user_kpi_definitions_for_weights.get(position_group_trained, []),
            "user_selected_composite_impact_kpis": user_composite_impact_kpis.get(position_group_trained, []),
            "derived_kpi_weights_for_target": derived_kpi_weights_actually_used.get(position_group_trained, {}),
            "base_features_list_source": "get_trainer_feature_names_for_extraction()",
            "min_90s_for_p90_kpi_reliability": MIN_90S_PLAYED_FOR_P90_STATS
        },
        "hyperparameter_search_used": best_params_from_search is not None,
        "position_group_trained_for": position_group_trained
    }
    if evaluation_metrics: # Add evaluation metrics if available
        config["evaluation_metrics_on_test_set"] = evaluation_metrics

    try:
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(config, f, indent=4)
        logger_trainer.info(f"Custom Model Run Configuration for {position_group_trained} saved to {filepath}")
    except IOError: logger_trainer.error(f"Error: Could not save custom model run configuration for {position_group_trained} to {filepath}")
    except TypeError as e: logger_trainer.error(f"TypeError during JSON serialization for {position_group_trained} custom model config: {e}.")


# --- Main Training Function (replaces main() from your script) ---
def build_and_train_model_from_script_logic(
    custom_model_id: str,
    position_group_to_train: str,
    user_kpi_definitions_for_weight_derivation: dict,
    user_composite_impact_kpis: dict,
    base_output_dir_for_custom_model: str,
    user_ml_feature_subset: list = None
):
    logger_trainer.info(f"Starting Custom Model Build (ID: {custom_model_id}) for Position: {position_group_to_train} using trainer.py logic.")
    logger_trainer.info(f"  User Target KPIs for weight derivation for {position_group_to_train}: {user_kpi_definitions_for_weight_derivation.get(position_group_to_train)}")
    logger_trainer.info(f"  User Impact KPIs for {position_group_to_train}: {user_composite_impact_kpis.get(position_group_to_train)}")

    try:
        with open(PLAYER_INDEX_PATH, 'r', encoding='utf-8') as f: player_index = json.load(f)
    except FileNotFoundError: 
        msg = f"Trainer Error: Player index file not found at {PLAYER_INDEX_PATH}"
        logger_trainer.error(msg); return False, msg
    try:
        minutes_df = pd.read_csv(PLAYER_MINUTES_PATH)
        minutes_df['season_name_std'] = minutes_df['season_name'].str.replace('/', '_', regex=False)
        minutes_df_dict = { (str(row['player_id']), row['season_name_std']): row['total_minutes_played']
                            for _, row in minutes_df.iterrows() }
    except FileNotFoundError: logger_trainer.warning(f"Trainer Warning: Player minutes file '{PLAYER_MINUTES_PATH}' not found."); minutes_df_dict = {}
    except Exception as e: logger_trainer.error(f"Trainer Error loading minutes file: {e}."); minutes_df_dict = {}

    all_u21_season_features = []
    logger_trainer.info("Trainer Pass 1: Extracting base features for all U21 player-seasons (all relevant positions).")
    
    player_items = []
    if isinstance(player_index, dict): player_items = player_index.items()
    elif isinstance(player_index, list): player_items = [(p.get("name", str(p.get("player_id"))), p) for p in player_index]

    for i, (player_name_from_key, p_info) in enumerate(player_items):
        if (i + 1) % 200 == 0: logger_trainer.info(f"  Trainer Pass 1 - Processed {i+1}/{len(player_items)} players...")
        player_id_str, dob, specific_pos_idx = str(p_info.get("player_id")), p_info.get("dob"), p_info.get("position")
        if not all([player_id_str, dob, specific_pos_idx]): continue
        general_pos_idx = get_general_position(specific_pos_idx)
        if general_pos_idx in ["Goalkeeper", "Unknown"]: continue

        for season_str in p_info.get("seasons", []):
            if not (isinstance(season_str, str) and '_' in season_str): continue
            age_at_season = get_age_at_fixed_point_in_season(dob, season_str)
            if age_at_season is None or age_at_season > 21: continue
            
            season_numeric = int(season_str.split('_')[0])
            total_minutes = minutes_df_dict.get((player_id_str, season_str), 0.0); num_90s = safe_division(total_minutes, 90.0)
            event_file_path = os.path.join(BASE_EVENT_DATA_PATH, season_str, "players", f"{player_id_str}_{season_str}.csv")
            current_season_event_df = pd.DataFrame()
            try:
                temp_df = pd.read_csv(event_file_path, dtype=object, low_memory=False)
                dtype_map_read = { 'shot_statsbomb_xg': float, 'pass_length': float, 'duration': float }
                bool_like_cols = ['shot_first_time', 'counterpress', 'under_pressure', 'pass_goal_assist', 'pass_shot_assist', 'pass_cross', 'pass_switch', 'pass_through_ball']
                for col, target_dtype in dtype_map_read.items():
                    if col in temp_df.columns: temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
                for col in bool_like_cols:
                    if col in temp_df.columns: temp_df[col] = temp_df[col].fillna('False').astype(str).str.lower().map({'true': True, 'false': False, 'nan': False, '': False, 'none':False}).astype(bool)
                current_season_event_df = temp_df
            except: pass 
            
            base_features_series = extract_season_features(current_season_event_df, age_at_season, season_numeric, num_90s)
            base_features_series['player_id_identifier'] = player_id_str
            base_features_series['player_name_identifier'] = player_name_from_key
            base_features_series['target_season_identifier'] = season_str
            base_features_series['general_position_identifier'] = general_pos_idx
            all_u21_season_features.append(base_features_series)

    if not all_u21_season_features: 
        msg = "Trainer: No U21 player seasons data found for Pass 1. Cannot build model."
        logger_trainer.error(msg); return False, msg
    df_all_u21_with_base_features = pd.DataFrame(all_u21_season_features).fillna(0.0)
    logger_trainer.info(f"Trainer Pass 1 Complete. Extracted base features for {len(df_all_u21_with_base_features)} U21 player-seasons.")

    logger_trainer.info(f"\nTrainer: Deriving KPI weights (will use weights for {position_group_to_train})...")
    derived_kpi_weights_all_groups = {} 
    original_kpi_defs = KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION
    original_impact_kpis = COMPOSITE_IMPACT_KPIS

    for pos_g_loop in ["Attacker", "Midfielder", "Defender"]:
        impact_kpis_to_use = user_composite_impact_kpis.get(pos_g_loop, original_impact_kpis.get(pos_g_loop, []))
        target_kpis_to_use = user_kpi_definitions_for_weight_derivation.get(pos_g_loop, original_kpi_defs.get(pos_g_loop, []))

        if not impact_kpis_to_use or not target_kpis_to_use:
            logger_trainer.warning(f"  Trainer: KPI definitions for impact or target missing for {pos_g_loop}. Using equal weights if target KPIs exist.")
            if target_kpis_to_use:
                num_kpis = len(target_kpis_to_use)
                derived_kpi_weights_all_groups[pos_g_loop] = {kpi: 1.0/num_kpis if num_kpis > 0 else 1.0 for kpi in target_kpis_to_use}
            else: derived_kpi_weights_all_groups[pos_g_loop] = {}
            continue
        
        derived_kpi_weights_all_groups[pos_g_loop] = derive_kpi_weights_from_impact_correlation(
            df_all_u21_with_base_features, pos_g_loop, impact_kpis_to_use, target_kpis_to_use
        )
    
    df_with_heuristic_targets = generate_potential_target(df_all_u21_with_base_features.copy(), derived_kpi_weights_all_groups)
    df_all_u21_with_base_features = pd.merge(
        df_all_u21_with_base_features,
        df_with_heuristic_targets[['player_id_identifier', 'target_season_identifier', 'potential_target', 'raw_composite_score']],
        on=['player_id_identifier', 'target_season_identifier'], how='left').fillna(0.0)

    logger_trainer.info(f"\nTrainer Pass 2: Constructing full ML input features for ALL players...")
    all_player_ml_feature_vectors = []
    base_metric_names = get_feature_names_for_extraction()
    
    players_processed_count_pass2 = 0
    num_unique_players_pass1 = df_all_u21_with_base_features['player_id_identifier'].nunique()
    for player_id_str_group, player_group_df in df_all_u21_with_base_features.groupby('player_id_identifier'):
        players_processed_count_pass2 += 1
        if (players_processed_count_pass2) % 100 == 0:
            logger_trainer.info(f"  Trainer Pass 2 - Processed ML features for {players_processed_count_pass2}/{num_unique_players_pass1} players...")

        player_group_df_sorted = player_group_df.sort_values(by='season_numeric')
        historical_data_for_player_list_of_dicts = []
        
        for _, current_season_data_row in player_group_df_sorted.iterrows():
            instance_ml_features = pd.Series(dtype='float64')
            for base_fname in base_metric_names:
                instance_ml_features[f'current_{base_fname}'] = current_season_data_row.get(base_fname, 0.0)
            
            general_pos_current = current_season_data_row.get('general_position_identifier')
            interaction_poly_features_all_pos = [
                'current_inter_goals_x_conversion', 'current_poly_goals_p90_sqrt_sq',
                'current_inter_drib_x_prog_carry', 'current_inter_succpass_x_comprate', 
                'current_poly_successful_passes_p90_sq', 'current_inter_kpsa_x_prog_carry',
                'current_inter_tackles_x_rate', 'current_poly_tackles_won_p90_sq', 'current_inter_aerials_x_rate'
            ]
            for feat_name in interaction_poly_features_all_pos: instance_ml_features[feat_name] = 0.0

            if general_pos_current == "Attacker":
                g_p90s = instance_ml_features.get('current_goals_p90_sqrt_', 0.0); cr_kpi = instance_ml_features.get('current_conversion_rate_excl_xg_kpi', 0.0)
                instance_ml_features['current_inter_goals_x_conversion'] = g_p90s * cr_kpi; instance_ml_features['current_poly_goals_p90_sqrt_sq'] = g_p90s ** 2
                drib_p90 = instance_ml_features.get('current_dribbles_completed_p90',0.0); prog_car_p90 = instance_ml_features.get('current_progressive_carries_p90',0.0)
                instance_ml_features['current_inter_drib_x_prog_carry'] = drib_p90 * prog_car_p90
            elif general_pos_current == "Midfielder":
                sp_p90 = instance_ml_features.get('current_successful_passes_p90', 0.0); pc_kpi = instance_ml_features.get('current_pass_completion_rate_kpi', 0.0)
                instance_ml_features['current_inter_succpass_x_comprate'] = sp_p90 * pc_kpi; instance_ml_features['current_poly_successful_passes_p90_sq'] = sp_p90 ** 2
                kpsa_p90s = instance_ml_features.get('current_key_passes_goal_assist_p90_sqrt_',0.0); prog_car_p90 = instance_ml_features.get('current_progressive_carries_p90',0.0)
                instance_ml_features['current_inter_kpsa_x_prog_carry'] = kpsa_p90s * prog_car_p90
            elif general_pos_current == "Defender":
                tw_p90 = instance_ml_features.get('current_tackles_won_p90', 0.0); twr_kpi = instance_ml_features.get('current_tackle_win_rate_kpi', 0.0)
                instance_ml_features['current_inter_tackles_x_rate'] = tw_p90 * twr_kpi; instance_ml_features['current_poly_tackles_won_p90_sq'] = tw_p90 ** 2
                adw_p90 = instance_ml_features.get('current_aerial_duels_won_p90',0.0); adwr_kpi = instance_ml_features.get('current_aerial_duel_win_rate_kpi',0.0)
                instance_ml_features['current_inter_aerials_x_rate'] = adw_p90 * adwr_kpi

            for base_fname_hist in base_metric_names:
                for agg_prefix in ['hist_avg_', 'hist_sum_', 'hist_max_', 'hist_trend_', 'growth_', 'growth_ratio_']:
                    instance_ml_features[f'{agg_prefix}{base_fname_hist}'] = 0.0
            instance_ml_features['num_hist_seasons'] = 0.0
            
            if historical_data_for_player_list_of_dicts:
                df_history = pd.DataFrame(historical_data_for_player_list_of_dicts)
                instance_ml_features['num_hist_seasons'] = float(len(df_history))
                for col_name_base_hist in base_metric_names:
                    if col_name_base_hist in df_history.columns:
                        hist_values = pd.to_numeric(df_history[col_name_base_hist], errors='coerce').fillna(0.0)
                        if hist_values.empty or hist_values.isna().all(): continue
                        instance_ml_features[f'hist_avg_{col_name_base_hist}'] = hist_values.mean()
                        instance_ml_features[f'hist_sum_{col_name_base_hist}'] = hist_values.sum()
                        instance_ml_features[f'hist_max_{col_name_base_hist}'] = hist_values.max()
                        last_season_val_hist = hist_values.iloc[-1] if not hist_values.empty else 0.0
                        current_val_for_growth = instance_ml_features.get(f'current_{col_name_base_hist}', 0.0)
                        instance_ml_features[f'growth_{col_name_base_hist}'] = current_val_for_growth - last_season_val_hist
                        instance_ml_features[f'growth_ratio_{col_name_base_hist}'] = safe_division(current_val_for_growth, last_season_val_hist, default=1.0 if current_val_for_growth == last_season_val_hist and current_val_for_growth !=0 else 0.0)
                        if len(df_history) >= 2 and 'season_numeric' in df_history.columns:
                            x_h_series = pd.to_numeric(df_history['season_numeric'], errors='coerce'); y_h_series = hist_values
                            valid_trend_mask = x_h_series.notna() & y_h_series.notna()
                            x_h_valid, y_h_valid = x_h_series[valid_trend_mask].values, y_h_series[valid_trend_mask].values
                            if len(x_h_valid) >= 2:
                                try:
                                    slope, _ = np.polyfit(x_h_valid.astype(float), y_h_valid.astype(float), 1)
                                    instance_ml_features[f'hist_trend_{col_name_base_hist}'] = slope
                                except (np.linalg.LinAlgError, TypeError, ValueError): instance_ml_features[f'hist_trend_{col_name_base_hist}'] = 0.0
            
            instance_ml_features['player_id_identifier'] = player_id_str_group
            instance_ml_features['player_name_identifier'] = current_season_data_row['player_name_identifier']
            instance_ml_features['target_season_identifier'] = current_season_data_row['target_season_identifier']
            instance_ml_features['general_position_identifier'] = current_season_data_row['general_position_identifier']
            instance_ml_features['potential_target'] = current_season_data_row['potential_target']
            instance_ml_features['raw_composite_score_heuristic_value'] = current_season_data_row.get('raw_composite_score', 0.0)
            all_player_ml_feature_vectors.append(instance_ml_features)

            current_base_dict_for_history = { fname: current_season_data_row.get(fname, 0.0) for fname in base_metric_names }
            current_base_dict_for_history['season_numeric'] = current_season_data_row.get('season_numeric',0.0)
            historical_data_for_player_list_of_dicts.append(current_base_dict_for_history)

    if not all_player_ml_feature_vectors:
        msg = "Trainer: No ML feature vectors constructed in Pass 2. Cannot train."
        logger_trainer.error(msg); return False, msg
    full_ml_features_df = pd.DataFrame(all_player_ml_feature_vectors).fillna(0.0)
    logger_trainer.info(f"Trainer Pass 2 Complete. Full ML features constructed for {len(full_ml_features_df)} instances.")

    pos_df_for_training_all_features = full_ml_features_df[full_ml_features_df['general_position_identifier'] == position_group_to_train].copy()
    if pos_df_for_training_all_features.empty or len(pos_df_for_training_all_features) < 10: # Min samples for training + test
        msg = f"Trainer: Not enough data for {position_group_to_train} ({len(pos_df_for_training_all_features)}) after ML feature construction. Cannot train model."
        logger_trainer.error(msg); return False, msg

    id_cols_ml = ['player_id_identifier', 'player_name_identifier', 'target_season_identifier',
                  'general_position_identifier', 'potential_target', 'raw_composite_score_heuristic_value']
    all_available_ml_features_for_pos = [c for c in pos_df_for_training_all_features.columns if c not in id_cols_ml]
    
    final_ml_feature_cols_for_model = []
    if user_ml_feature_subset and isinstance(user_ml_feature_subset, list) and len(user_ml_feature_subset) > 0:
        logger_trainer.info(f"  Trainer: Using user-defined subset of {len(user_ml_feature_subset)} ML features for training.")
        final_ml_feature_cols_for_model = [feat for feat in user_ml_feature_subset if feat in all_available_ml_features_for_pos]
        if not final_ml_feature_cols_for_model:
            logger_trainer.warning("  Trainer: None of the user-selected ML features are valid/generated. Using all available as fallback.")
            final_ml_feature_cols_for_model = all_available_ml_features_for_pos
    else:
        logger_trainer.info(f"  Trainer: Deriving ML feature set from user-selected target KPIs for {position_group_to_train}.")
        selected_base_kpis_for_features = user_kpi_definitions_for_weight_derivation.get(position_group_to_train, [])
        
        if not selected_base_kpis_for_features:
            logger_trainer.warning(f"  Trainer: No base KPIs from user to guide feature selection for {position_group_to_train}. Using all {len(all_available_ml_features_for_pos)} generated ML features.");
            final_ml_feature_cols_for_model = all_available_ml_features_for_pos
        else:
            temp_feature_list = []
            for ml_feat_candidate in all_available_ml_features_for_pos:
                is_related = False
                for user_base_kpi in selected_base_kpis_for_features:
                    if user_base_kpi in ml_feat_candidate:
                        is_related = True; break
                if is_related: temp_feature_list.append(ml_feat_candidate)
            
            context_features_to_add = ['current_age', 'current_season_numeric', 'current_num_90s_played', 'current_matches_played_events', 'num_hist_seasons']
            for cf in context_features_to_add:
                if cf in all_available_ml_features_for_pos: temp_feature_list.append(cf)
            final_ml_feature_cols_for_model = sorted(list(set(temp_feature_list)))
            if not final_ml_feature_cols_for_model:
                 logger_trainer.warning(f"  Trainer: No ML features derived from selected base KPIs for {position_group_to_train}. Using all generated features as fallback.")
                 final_ml_feature_cols_for_model = all_available_ml_features_for_pos
    
    if not final_ml_feature_cols_for_model:
        msg = f"Trainer: No ML feature columns identified for {position_group_to_train}. Cannot train."
        logger_trainer.error(msg); return False, msg
    logger_trainer.info(f"  Trainer: Final ML features for {position_group_to_train} model ({len(final_ml_feature_cols_for_model)}): {final_ml_feature_cols_for_model[:5]}...")

    X_for_model = pos_df_for_training_all_features[final_ml_feature_cols_for_model].copy()
    y_for_model = pos_df_for_training_all_features['potential_target'].copy()
    groups_for_split = pos_df_for_training_all_features['player_id_identifier']
    
    for col in X_for_model.columns: X_for_model[col] = pd.to_numeric(X_for_model[col], errors='coerce')
    X_for_model.fillna(0, inplace=True)

    pos_model_output_dir = os.path.join(base_output_dir_for_custom_model, custom_model_id, position_group_to_train.lower())
    os.makedirs(pos_model_output_dir, exist_ok=True)
    pos_trained_model_path = os.path.join(pos_model_output_dir, f'potential_model_{position_group_to_train.lower()}_{custom_model_id}.joblib')
    pos_model_config_path = os.path.join(pos_model_output_dir, f'model_config_{position_group_to_train.lower()}_{custom_model_id}.json')
    pos_scaler_path = os.path.join(pos_model_output_dir, f'feature_scaler_{position_group_to_train.lower()}_{custom_model_id}.joblib')

    scaler_pos = StandardScaler()
    X_scaled_full = scaler_pos.fit_transform(X_for_model)
    joblib.dump(scaler_pos, pos_scaler_path)
    
    # --- Start: Model Training and Evaluation (adapted from v14.py) ---
    X_train_scaled, X_test_scaled, y_train, y_test = pd.DataFrame(), pd.DataFrame(), pd.Series(dtype='float64'), pd.Series(dtype='float64')
    groups_train_for_search = None # Groups for RandomizedSearchCV if GroupKFold is used for CV
    cv_for_search = 3 # Default CV splits for RandomizedSearchCV
    evaluation_metrics_dict = None # To store MAE, RMSE, R2

    unique_groups = groups_for_split.nunique()
    min_samples_for_gkf_split = 10 # Need at least this many samples to attempt GKF
    
    if unique_groups < 2 or X_scaled_full.shape[0] < min_samples_for_gkf_split :
        logger_trainer.warning(f"  Trainer: Insufficient groups/samples ({unique_groups} unique groups, {X_scaled_full.shape[0]} samples) for GroupKFold for {position_group_to_train}. Using simple train_test_split.")
        if X_scaled_full.shape[0] < 2:
            msg = f"  Trainer: Less than 2 samples for {position_group_to_train}. Skipping model training and evaluation for this group."
            logger_trainer.error(msg)
            # Save a config indicating no model was trained or save a placeholder? For now, just log and return.
            # Fallback: Train on all available data without test split if this is critical.
            # Here we will train on all data if split fails badly.
            X_train_scaled, y_train = X_scaled_full, y_for_model
            X_test_scaled, y_test = np.array([]), pd.Series(dtype='float64') # Empty test set
        else:
            test_size_actual = 0.2 if X_scaled_full.shape[0] >=5 else (1/X_scaled_full.shape[0])
            try:
                X_train_scaled, X_test_scaled, y_train, y_test = train_test_split(X_scaled_full, y_for_model, test_size=test_size_actual, random_state=42, stratify=None) # Cannot stratify with too few samples per class or continuous target easily
            except ValueError as e_split: # Could happen if test_size_actual leads to <1 sample in train or test
                logger_trainer.warning(f"  Trainer: train_test_split failed for {position_group_to_train}: {e_split}. Training on all available data.")
                X_train_scaled, y_train = X_scaled_full, y_for_model
                X_test_scaled, y_test = np.array([]), pd.Series(dtype='float64')
    else:
        # Prefer GroupKFold for outer split to simulate real-world scenario (unseen players)
        gkf_outer = GroupKFold(n_splits=min(5, unique_groups)) # Max 5 splits, or fewer if not enough groups
        try:
            train_idx, test_idx = next(gkf_outer.split(X_scaled_full, y_for_model, groups_for_split))
            X_train_scaled, X_test_scaled = X_scaled_full[train_idx], X_scaled_full[test_idx]
            y_train, y_test = y_for_model.iloc[train_idx], y_for_model.iloc[test_idx]
            groups_train_outer = groups_for_split.iloc[train_idx] # Groups for the main training set
            
            # For RandomizedSearchCV's CV, can use GroupKFold if enough unique groups in train_idx
            n_cv_splits_inner = min(3, groups_train_outer.nunique()) if groups_train_outer.nunique() >= 2 else 2
            if n_cv_splits_inner < 2 or X_train_scaled.shape[0] < n_cv_splits_inner * 2: # Ensure enough samples per inner split
                cv_for_search = 3 # Fallback to simple k-fold if not enough groups/samples for inner GroupKFold
                groups_train_for_search = None
                logger_trainer.info(f"  Trainer: Not enough unique groups in training data for inner GroupKFold in search. Using {cv_for_search}-fold CV for RandomizedSearch.")
            else:
                cv_for_search = GroupKFold(n_splits=n_cv_splits_inner)
                groups_train_for_search = groups_train_outer # Pass these groups to RandomizedSearchCV's .fit()
                logger_trainer.info(f"  Trainer: Using inner GroupKFold ({n_cv_splits_inner} splits) for RandomizedSearch.")
        except Exception as e_gkf:
            logger_trainer.error(f"  Trainer: Error in GroupKFold split for {position_group_to_train}: {e_gkf}. Falling back to simple train_test_split.")
            test_size_actual = 0.2 if X_scaled_full.shape[0] >=5 else (1/X_scaled_full.shape[0])
            if X_scaled_full.shape[0] < 2 or X_scaled_full.shape[0]*(1-test_size_actual) < 1 :
                logger_trainer.warning(f"  Trainer: Cannot split data for {position_group_to_train} after GKF error. Training on all data.")
                X_train_scaled, y_train = X_scaled_full, y_for_model
                X_test_scaled, y_test = np.array([]), pd.Series(dtype='float64')
            else:
                 X_train_scaled, X_test_scaled, y_train, y_test = train_test_split(X_scaled_full, y_for_model, test_size=test_size_actual, random_state=42)

    if X_train_scaled.shape[0] == 0:
        msg = f"Trainer: Training set empty for {position_group_to_train} after split. Cannot train model."
        logger_trainer.error(msg); return False, msg
    if X_test_scaled.shape[0] == 0:
        logger_trainer.warning(f"  Trainer: Test set is empty for {position_group_to_train}. Model will be trained on all available data for this group, no evaluation metrics will be available.")

    # XGBoost model and RandomizedSearchCV (as in v14.py)
    xgb_model_for_search = XGBRegressor(random_state=42, objective='reg:squarederror', n_jobs=-1)
    xgb_param_grid = {
        'n_estimators': [100, 200, 300, 500], 'learning_rate': [0.01, 0.03, 0.05, 0.1],
        'max_depth': [3, 4, 5, 6, 7], 'subsample': [0.6, 0.7, 0.8, 0.9, 1.0],
        'colsample_bytree': [0.6, 0.7, 0.8, 0.9], 'gamma': [0, 0.1, 0.2],
        'reg_alpha': [0, 0.005, 0.01, 0.05], 'reg_lambda': [0.1, 0.5, 1, 1.5]
    }
    # Adjust n_iter based on training set size, ensure it's at least 1.
    n_iter_search = 20 if X_train_scaled.shape[0] > 50 else max(1, int(X_train_scaled.shape[0] * 0.1)) 
    if X_train_scaled.shape[0] < 10: n_iter_search = max(1, X_train_scaled.shape[0] // 2) # Further reduce for very small sets
    
    random_search = RandomizedSearchCV(
        estimator=xgb_model_for_search, param_distributions=xgb_param_grid,
        n_iter=n_iter_search, cv=cv_for_search,
        scoring='r2', random_state=42, n_jobs=-1, verbose=0 # verbose=1 for more logs
    )
    
    logger_trainer.info(f"  Trainer: Starting RandomizedSearchCV for {position_group_to_train} on {X_train_scaled.shape[0]} training samples (n_iter={n_iter_search}).")
    best_xgb_model = None
    best_params_for_config = None
    hyperparam_search_done = False

    try:
        search_groups_param = groups_train_for_search if isinstance(cv_for_search, GroupKFold) and groups_train_for_search is not None else None
        random_search.fit(X_train_scaled, y_train, groups=search_groups_param)
        
        best_params_from_search = random_search.best_params_
        logger_trainer.info(f"  Trainer: Best XGBoost Params for {position_group_to_train} from Search: {best_params_from_search}")
        
        best_xgb_model = XGBRegressor(**best_params_from_search, random_state=42, objective='reg:squarederror', n_jobs=-1)
        if X_test_scaled.shape[0] > 0: # If there's a test set for early stopping
            best_xgb_model.set_params(early_stopping_rounds=10)
            best_xgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)
        else: # No test set, fit on all training data
            best_xgb_model.fit(X_train_scaled, y_train, verbose=False)
        
        best_params_for_config = best_params_from_search # These are the ones found by search
        hyperparam_search_done = True

    except Exception as e_search:
        logger_trainer.error(f"  Trainer: Error during RandomizedSearchCV for {position_group_to_train}: {e_search}. Training with default-ish params.")
        # Fallback to a default-ish model
        default_params = {'n_estimators': 100, 'max_depth': 4, 'learning_rate': 0.05, 
                          'random_state': 42, 'objective': 'reg:squarederror', 'n_jobs': -1}
        best_xgb_model = XGBRegressor(**default_params)
        if X_test_scaled.shape[0] > 0:
            best_xgb_model.set_params(early_stopping_rounds=10)
            best_xgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)
        else:
            best_xgb_model.fit(X_train_scaled, y_train, verbose=False)
        
        best_params_for_config = best_xgb_model.get_params() # Use the actual params of this fallback model
        hyperparam_search_done = False # Indicate search was not successful

    joblib.dump(best_xgb_model, pos_trained_model_path)
    
    # Evaluation on the test set, if it exists
    if X_test_scaled.shape[0] > 0 and y_test.shape[0] > 0:
        y_pred_test = best_xgb_model.predict(X_test_scaled)
        y_pred_test = np.clip(y_pred_test, 0, 200) # Clip predictions
        
        mae = mean_absolute_error(y_test, y_pred_test)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        r2 = r2_score(y_test, y_pred_test)
        evaluation_metrics_dict = {'MAE': round(mae, 3), 'RMSE': round(rmse, 3), 'R2': round(r2, 3)}
        logger_trainer.info(f"  Trainer: Evaluation for {position_group_to_train} (ID: {custom_model_id}) on test set ({X_test_scaled.shape[0]} samples):")
        logger_trainer.info(f"    MAE: {mae:.3f}, RMSE: {rmse:.3f}, R^2: {r2:.3f}")

        if hasattr(best_xgb_model, 'feature_importances_'):
            importances = best_xgb_model.feature_importances_
            if len(final_ml_feature_cols_for_model) == len(importances):
                feat_imp_df = pd.DataFrame({
                    'feature': final_ml_feature_cols_for_model, 
                    'importance': importances
                }).sort_values('importance', ascending=False).head(20)
                logger_trainer.info(f"  Trainer: Top Feature Importances for {position_group_to_train} (ID: {custom_model_id}):\n{feat_imp_df.to_string(index=False)}")
            else:
                logger_trainer.warning("  Trainer: Mismatch between feature columns and importances length. Cannot log feature importances.")
    else:
        logger_trainer.info(f"  Trainer: No test set available for evaluation for {position_group_to_train} (ID: {custom_model_id}).")

    trainer_save_model_run_config(
        pos_model_config_path, 
        model_name=f"XGBRegressor_Custom_{custom_model_id}", 
        feature_cols=final_ml_feature_cols_for_model, 
        model_params=best_xgb_model.get_params(), # Save params of the *final fitted* model
        user_kpi_definitions_for_weights=user_kpi_definitions_for_weight_derivation,
        user_composite_impact_kpis=user_composite_impact_kpis,
        derived_kpi_weights_actually_used=derived_kpi_weights_all_groups,
        position_group_trained=position_group_to_train,
        best_params_from_search=best_params_for_config if hyperparam_search_done else None, # Save params found by search if search was done
        evaluation_metrics=evaluation_metrics_dict # Pass metrics to save in config
    )
    # --- End: Model Training and Evaluation ---
    
    logger_trainer.info(f"Custom Model for {position_group_to_train} (ID: {custom_model_id}) trained and artifacts saved to {pos_model_output_dir}")
    return True, f"Model for {position_group_to_train} (ID: {custom_model_id}) built successfully."


# --- Functions to expose constants to main.py ---
def get_trainer_kpi_definitions_for_weight_derivation():
    return KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION

def get_trainer_composite_impact_kpis_definitions():
    return COMPOSITE_IMPACT_KPIS


# Al final de trainer.py, abans del bloc if __name__ == "__main__":

# --- Function to expose ML feature construction logic ---
def trainer_construct_ml_features_for_player_season(
    current_season_base_features_row: pd.Series, # Fila del DataFrame de característiques base per a la temporada actual
    historical_base_features_df: pd.DataFrame,   # DataFrame amb característiques base de temporades anteriors (player_group_df_sorted[player_group_df_sorted['season_numeric'] < target_season_numeric])
    all_base_metric_names: list                    # Llista de tots els noms de mètriques base (de get_feature_names_for_extraction)
):
    instance_ml_features = pd.Series(dtype='float64')

    # Populate current features
    for base_fname in all_base_metric_names:
        instance_ml_features[f'current_{base_fname}'] = current_season_base_features_row.get(base_fname, 0.0)
    
    general_pos_current = current_season_base_features_row.get('general_position_identifier')
    
    # Interaction and Polynomial features (mateixa lògica que a build_and_train_model_from_script_logic Pass 2)
    interaction_poly_features_all_pos = [
        'current_inter_goals_x_conversion', 'current_poly_goals_p90_sqrt_sq',
        'current_inter_drib_x_prog_carry', 'current_inter_succpass_x_comprate', 
        'current_poly_successful_passes_p90_sq', 'current_inter_kpsa_x_prog_carry',
        'current_inter_tackles_x_rate', 'current_poly_tackles_won_p90_sq', 'current_inter_aerials_x_rate'
    ]
    for feat_name in interaction_poly_features_all_pos: instance_ml_features[feat_name] = 0.0

    if general_pos_current == "Attacker":
        g_p90s = instance_ml_features.get('current_goals_p90_sqrt_', 0.0); cr_kpi = instance_ml_features.get('current_conversion_rate_excl_xg_kpi', 0.0)
        instance_ml_features['current_inter_goals_x_conversion'] = g_p90s * cr_kpi; instance_ml_features['current_poly_goals_p90_sqrt_sq'] = g_p90s ** 2
        drib_p90 = instance_ml_features.get('current_dribbles_completed_p90',0.0); prog_car_p90 = instance_ml_features.get('current_progressive_carries_p90',0.0)
        instance_ml_features['current_inter_drib_x_prog_carry'] = drib_p90 * prog_car_p90
    elif general_pos_current == "Midfielder":
        sp_p90 = instance_ml_features.get('current_successful_passes_p90', 0.0); pc_kpi = instance_ml_features.get('current_pass_completion_rate_kpi', 0.0)
        instance_ml_features['current_inter_succpass_x_comprate'] = sp_p90 * pc_kpi; instance_ml_features['current_poly_successful_passes_p90_sq'] = sp_p90 ** 2
        kpsa_p90s = instance_ml_features.get('current_key_passes_goal_assist_p90_sqrt_',0.0); prog_car_p90 = instance_ml_features.get('current_progressive_carries_p90',0.0)
        instance_ml_features['current_inter_kpsa_x_prog_carry'] = kpsa_p90s * prog_car_p90
    elif general_pos_current == "Defender":
        tw_p90 = instance_ml_features.get('current_tackles_won_p90', 0.0); twr_kpi = instance_ml_features.get('current_tackle_win_rate_kpi', 0.0)
        instance_ml_features['current_inter_tackles_x_rate'] = tw_p90 * twr_kpi; instance_ml_features['current_poly_tackles_won_p90_sq'] = tw_p90 ** 2
        adw_p90 = instance_ml_features.get('current_aerial_duels_won_p90',0.0); adwr_kpi = instance_ml_features.get('current_aerial_duel_win_rate_kpi',0.0)
        instance_ml_features['current_inter_aerials_x_rate'] = adw_p90 * adwr_kpi

    # Initialize historical/growth features
    for base_fname_hist in all_base_metric_names:
        for agg_prefix in ['hist_avg_', 'hist_sum_', 'hist_max_', 'hist_trend_', 'growth_', 'growth_ratio_']:
            instance_ml_features[f'{agg_prefix}{base_fname_hist}'] = 0.0
    instance_ml_features['num_hist_seasons'] = 0.0
    
    if historical_base_features_df is not None and not historical_base_features_df.empty:
        df_history = historical_base_features_df.copy() # historical_base_features_df ja està filtrat per temporades anteriors
        instance_ml_features['num_hist_seasons'] = float(len(df_history))
        for col_name_base_hist in all_base_metric_names:
            if col_name_base_hist in df_history.columns:
                hist_values = pd.to_numeric(df_history[col_name_base_hist], errors='coerce').fillna(0.0)
                if hist_values.empty or hist_values.isna().all(): continue
                
                instance_ml_features[f'hist_avg_{col_name_base_hist}'] = hist_values.mean()
                instance_ml_features[f'hist_sum_{col_name_base_hist}'] = hist_values.sum()
                instance_ml_features[f'hist_max_{col_name_base_hist}'] = hist_values.max()
                
                last_season_val_hist = hist_values.iloc[-1] if not hist_values.empty else 0.0
                current_val_for_growth = instance_ml_features.get(f'current_{col_name_base_hist}', 0.0)
                instance_ml_features[f'growth_{col_name_base_hist}'] = current_val_for_growth - last_season_val_hist
                instance_ml_features[f'growth_ratio_{col_name_base_hist}'] = safe_division(current_val_for_growth, last_season_val_hist, default=1.0 if current_val_for_growth == last_season_val_hist and current_val_for_growth !=0 else 0.0)
                
                if len(df_history) >= 2 and 'season_numeric' in df_history.columns:
                    x_h_series = pd.to_numeric(df_history['season_numeric'], errors='coerce'); y_h_series = hist_values
                    valid_trend_mask = x_h_series.notna() & y_h_series.notna()
                    x_h_valid, y_h_valid = x_h_series[valid_trend_mask].values, y_h_series[valid_trend_mask].values
                    if len(x_h_valid) >= 2:
                        try:
                            # Assegurar que siguin float per polyfit
                            slope, _ = np.polyfit(x_h_valid.astype(float), y_h_valid.astype(float), 1)
                            instance_ml_features[f'hist_trend_{col_name_base_hist}'] = slope
                        except (np.linalg.LinAlgError, TypeError, ValueError): 
                            instance_ml_features[f'hist_trend_{col_name_base_hist}'] = 0.0
    
    # No cal afegir identificadors aquí, ja que és per a una sola instància i es gestionarà fora.
    return instance_ml_features



def get_trainer_all_possible_ml_feature_names():
    """
    Generates a list of all theoretically possible ML feature names
    that the trainer can produce in Pass 2.
    """
    base_metric_names = get_feature_names_for_extraction() # Funció ja existent
    
    possible_ml_features = set()

    # 1. Current features
    for base_fname in base_metric_names:
        possible_ml_features.add(f'current_{base_fname}')

    # 2. Interaction and Polynomial features
    interaction_poly_features_all_pos = [ # Mateixa llista que a la lògica d'entrenament
        'current_inter_goals_x_conversion', 'current_poly_goals_p90_sqrt_sq',
        'current_inter_drib_x_prog_carry', 'current_inter_succpass_x_comprate', 
        'current_poly_successful_passes_p90_sq', 'current_inter_kpsa_x_prog_carry',
        'current_inter_tackles_x_rate', 'current_poly_tackles_won_p90_sq', 'current_inter_aerials_x_rate'
    ]
    for feat_name in interaction_poly_features_all_pos:
        possible_ml_features.add(feat_name)
    
    # 3. Historical and Growth features
    for base_fname_hist in base_metric_names:
        for agg_prefix in ['hist_avg_', 'hist_sum_', 'hist_max_', 'hist_trend_', 'growth_', 'growth_ratio_']:
            possible_ml_features.add(f'{agg_prefix}{base_fname_hist}')
    
    # 4. Other specific ML features (com num_hist_seasons)
    possible_ml_features.add('num_hist_seasons')
    
    return sorted(list(possible_ml_features))


if __name__ == "__main__":
    # Configure basic logging for direct script run
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger_trainer.info("Running trainer.py directly to generate default V14-like models...")
    # Use a subfolder within the project's ml_models, not relative to trainer.py for consistency
    v14_output_dir_main = os.path.join(_PROJECT_ROOT, 'ml_models', 'ml_model_files_v14_rebuild_trainer')
    
    for pos_group in ["Attacker", "Midfielder", "Defender"]:
        logger_trainer.info(f"\n--- Generating V14-like model for: {pos_group} ---")
        success, message = build_and_train_model_from_script_logic(
            custom_model_id="v14_rebuild",
            position_group_to_train=pos_group,
            user_kpi_definitions_for_weight_derivation=KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION,
            user_composite_impact_kpis=COMPOSITE_IMPACT_KPIS,
            user_ml_feature_subset=None, # Use default feature selection logic
            base_output_dir_for_custom_model=v14_output_dir_main
        )
        if success:
            logger_trainer.info(message)
        else:
            logger_trainer.error(f"Failed to build model for {pos_group}: {message}")
            
    logger_trainer.info("\nDefault V14-like model generation process complete.")
