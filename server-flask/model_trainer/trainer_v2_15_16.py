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
import logging 
from ast import literal_eval 
from io import BytesIO, StringIO


logger_trainer = logging.getLogger(__name__ + "_trainer") 

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.feature_extraction.text")
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# --- Configuration  ---
_TRAINER_SCRIPT_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_TRAINER_SCRIPT_DIR, '..', '..')) 
_DATA_DIR_FOR_TRAINER = os.path.join(_PROJECT_ROOT, 'data')

PLAYER_INDEX_PATH = os.path.join(_DATA_DIR_FOR_TRAINER, 'player_index.json')
BASE_EVENT_DATA_PATH = _DATA_DIR_FOR_TRAINER 
PLAYER_MINUTES_PATH = os.path.join(_DATA_DIR_FOR_TRAINER, 'player_season_minutes_with_names.csv')


MIN_90S_PLAYED_FOR_P90_STATS = 3

# --- KPI Definitions and Helper Functions  ---
def generate_kpi_variants(base_name, include_sum=True, include_p90=True, include_p90_sqrt=False):
    variants = []
    if include_sum: variants.append(base_name)
    if include_p90: variants.append(f"{base_name}_p90")
    if include_p90_sqrt and include_p90: variants.append(f"{base_name}_p90_sqrt_")
    return variants

KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION = {
    "Attacker": 
        generate_kpi_variants("goals", include_p90_sqrt=True) +
        generate_kpi_variants("sum_xg", include_p90_sqrt=True) +
        generate_kpi_variants("shots_total") +
        generate_kpi_variants("shots_on_target") +
        ["conversion_rate_excl_xg_kpi"] + 
        generate_kpi_variants("goal_assists", include_p90=True) +
        generate_kpi_variants("dribbles_completed") +
        generate_kpi_variants("carries_total") +
        generate_kpi_variants("pressures") + 
        ["turnovers_p90_inv_kpi_base"] + 
        generate_kpi_variants("aerial_duels_won"),
    "Midfielder": 
        generate_kpi_variants("successful_passes") +
        ["pass_completion_rate_kpi"] +
        generate_kpi_variants("goal_assists", include_p90=True) +
        generate_kpi_variants("carries_total") +
        generate_kpi_variants("dribbles_completed") +
        generate_kpi_variants("interceptions") + 
        generate_kpi_variants("tackles_won") +
        generate_kpi_variants("ball_recoveries") +
        generate_kpi_variants("pressures") +
        ["turnovers_p90_inv_kpi_base"],
    "Defender":
        generate_kpi_variants("tackles_won") +
        ["tackle_win_rate_kpi"] +
        generate_kpi_variants("interceptions") +
        generate_kpi_variants("clearances") + 
        generate_kpi_variants("blocks_total") +  
        generate_kpi_variants("aerial_duels_won") +
        ["aerial_duel_win_rate_kpi"] +
        generate_kpi_variants("successful_passes") +
        ["pass_completion_rate_kpi"] +
        generate_kpi_variants("carries_total") +
        ["turnovers_p90_inv_kpi_base"],
}
for pos, kpis in KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION.items():
    KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION[pos] = sorted(list(set(kpis)))

COMPOSITE_IMPACT_KPIS = {
    "Attacker": ["sum_xg_p90_sqrt_", "goals_p90_sqrt_", "dribbles_completed_p90"],
    "Midfielder": ["interceptions_p90", "goal_assists_p90", "carries_total_p90"],
    "Defender": ["tackles_won_p90", "interceptions_p90", "aerial_duels_won_p90"]
}

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
        if not (loc_str.startswith('[') and loc_str.endswith(']')) and \
           not (loc_str.startswith('(') and loc_str.endswith(')')):
            parts = loc_str.split(',')
            if len(parts) >= 2: return tuple(map(float, parts))
            return None
        return tuple(map(float, literal_eval(loc_str.strip('[]()'))))
    except: return None

# --- Feature Extraction Functions ---
def get_feature_names_for_extraction():
    kpi_direct_names = [
        'conversion_rate_excl_xg_kpi', 'xg_performance', 'pass_completion_rate_kpi',
        'avg_pass_length_kpi', 'dribble_success_rate_kpi', 'tackle_win_rate_kpi',
        'aerial_duel_win_rate_kpi', 'turnovers_p90_inv_kpi_base',
        'avg_carry_duration'
    ]
    canonical_event_counts = [
        'passes_total', 'shots_total', 'dribbles_attempted', 'duels_total', 'interceptions', 'clearances', 
        'fouls_committed', 'fouls_won', 'ball_recoveries', 'miscontrols', 'dispossessed_events', 
        'pressures', 'carries_total', 'blocks_total', 'fifty_fifties_total', 'shields_total', 
        'errors_leading_to_shot_or_goal', 'bad_behaviours_total'
    ]
    other_specific_aggregates = [
        'goals', 'shots_on_target', 'sum_xg', 'shot_assists',
        'goal_assists',
        'shots_first_time', 'shots_open_goal', 'shots_deflected', 'shots_aerial_won',
        'shots_blocked_by_opponent', 'shots_hit_post', 'shots_off_target',
        'shots_penalty', 'shots_freekick',
        'successful_passes', 'crosses_total', 'switches_total', 'through_balls_total',
        'passes_ground', 'passes_low', 'passes_high',
        'passes_outcome_incomplete', 'passes_outcome_out', 'passes_outcome_offside', 'passes_outcome_injury_clearance',
        'passes_backheel', 'passes_deflected_by_opponent', 'passes_miscommunication',
        'dribbles_completed', 'dribbles_nutmeg', 'dribbles_overrun', 'dribbles_no_touch',
        'tackles_attempted', 'tackles_won',
        'aerial_duels_total', 'aerial_duels_won', 
        'duels_tackle_type', 
        'duels_aerial_lost',
        'fifty_fifties_won', 'fifty_fifties_lost',
        'counterpress_actions', 'actions_under_pressure', 'turnovers_total',
        'ball_recoveries_offensive', 'ball_recoveries_failed',
        'blocks_deflection', 'blocks_offensive', 'blocks_save_attempt',
        'clearances_aerial_won',
        'fouls_committed_penalty', 'fouls_won_penalty',
        'yellow_cards', 'red_cards',
        'interceptions_successful_gain_possession', 'interceptions_failed_gain_possession',
        'sum_carry_duration', 
        'player_caused_ball_out'
    ]
    all_base_sum_or_count_metrics = sorted(list(set(
        canonical_event_counts + 
        [m for m in other_specific_aggregates if not m.startswith('avg_')] +
        ['avg_pass_length']
    )))
    metrics_for_p90_conversion = all_base_sum_or_count_metrics.copy()
    p90_versions = [f"{m}_p90" for m in metrics_for_p90_conversion]
    p90_aliases = [] 
    sqrt_transformed_kpis_base_p90 = ["goals_p90", "sum_xg_p90", "goal_assists_p90"]
    sqrt_transformed_kpis = [f"{b}_sqrt_" for b in sqrt_transformed_kpis_base_p90]
    context_features = ['age', 'season_numeric', 'num_90s_played', 'matches_played_events']
    all_features_set = set(
        kpi_direct_names + 
        all_base_sum_or_count_metrics +
        p90_versions + 
        p90_aliases +
        sqrt_transformed_kpis_base_p90 +
        sqrt_transformed_kpis +
        context_features
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
             s[fname] = 0.0 # Initialize all to 0.0

    if event_df.empty or len(event_df) == 0:
        if 'turnovers_p90_inv_kpi_base' in s.index: s['turnovers_p90_inv_kpi_base'] = 999.0
        # Initialize sqrt kpis to 0 if df is empty
        sqrt_kpis_to_init = [k for k in all_expected_features if k.endswith("_sqrt_")]
        for skpi in sqrt_kpis_to_init:
            s[skpi] = 0.0
        return s.reindex(all_expected_features).fillna(0.0)

    # --- Canonical Event Counts ---
    type_counts = event_df['type'].value_counts() if 'type' in event_df.columns else pd.Series(dtype='int64')
    
    event_name_map = {
        'passes_total': 'Pass', 'shots_total': 'Shot', 'dribbles_attempted': 'Dribble', 
        'duels_total': 'Duel', 'interceptions': 'Interception', 'clearances': 'Clearance',
        'fouls_committed': 'Foul Committed', 'fouls_won': 'Foul Won', 
        'ball_recoveries': 'Ball Recovery', 'miscontrols': 'Miscontrol', 
        'dispossessed_events': 'Dispossessed', 'pressures': 'Pressure', 
        'carries_total': 'Carry', 'blocks_total': 'Block', 
        'fifty_fifties_total': '50/50', 
        'shields_total': 'Shield', 'errors_leading_to_shot_or_goal': 'Error', 
        'bad_behaviours_total': 'Bad Behaviour'
    }
    for canonical_name, event_type_str in event_name_map.items():
        if canonical_name in s.index:
            if canonical_name == 'errors_leading_to_shot_or_goal': 
                 error_df = event_df[event_df['type'] == 'Error'] if 'type' in event_df.columns else pd.DataFrame()
                 s[canonical_name] = float(error_df.get('leads_to_shot', pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
            elif canonical_name == 'fifty_fifties_total':
                count_from_type = float(type_counts.get('50/50', 0))
                
                count_from_duel_type = 0
                if 'Duel' in type_counts and 'duel_type_name' in event_df.columns: #
                    duel_df_temp = event_df[event_df['type'] == 'Duel']
                    count_from_duel_type = float((duel_df_temp['duel_type_name'].astype(str) == '50/50').sum())

                s[canonical_name] = count_from_type if count_from_type > 0 else count_from_duel_type

            else:
                s[canonical_name] = float(type_counts.get(event_type_str, 0))

    # --- Other Specific Aggregates & KPIs ---

    # Player caused ball out
    if 'player_caused_ball_out' in s.index and 'out' in event_df.columns:
        s['player_caused_ball_out'] = float(event_df['out'].fillna(False).astype(bool).sum())

    # Shots
    shots_df = event_df[event_df['type'] == 'Shot'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not shots_df.empty:
        shot_outcome_series = shots_df.get('shot_outcome_name', pd.Series(dtype=str)) 
        shot_type_series = shots_df.get('shot_type_name', pd.Series(dtype=str))
        shots_df = event_df[event_df['type'] == 'Shot'].copy() if 'type' in event_df.columns else pd.DataFrame()
        if not shots_df.empty:
            shot_outcome_series = shots_df.get('shot_outcome_name', pd.Series(dtype=str))
            if shot_outcome_series.empty and 'shot_outcome' in shots_df.columns:
                shot_outcome_series = shots_df['shot_outcome'].apply(lambda x: x.get('name') if isinstance(x, dict) else x)
            if 'goals' in s.index:
                s['goals'] = float((shot_outcome_series == 'Goal').sum())
        
        if 'shots_on_target' in s.index: s['shots_on_target'] = float(shot_outcome_series.isin(['Saved', 'Goal', 'Post', 'Saved To Post', 'Saved Off Target']).sum())
        if 'sum_xg' in s.index: s['sum_xg'] = pd.to_numeric(shots_df.get('shot_statsbomb_xg', shots_df.get('statsbomb_xg')), errors='coerce').sum() # Check both common XG col names
        if 'shots_first_time' in s.index: s['shots_first_time'] = (shots_df.get('shot_first_time', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()
        if 'shots_open_goal' in s.index: s['shots_open_goal'] = (shots_df.get('shot_open_goal', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()
        if 'shots_deflected' in s.index: s['shots_deflected'] = ((shots_df.get('deflected', pd.Series(dtype=bool)).fillna(False).astype(bool)) | (shot_outcome_series == 'Deflected')).sum()
        if 'shots_aerial_won' in s.index: s['shots_aerial_won'] = (shots_df.get('shot_aerial_won', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()
        if 'shots_blocked_by_opponent' in s.index: s['shots_blocked_by_opponent'] = float((shot_outcome_series == 'Blocked').sum())
        if 'shots_hit_post' in s.index: s['shots_hit_post'] = float((shot_outcome_series == 'Post').sum())
        if 'shots_off_target' in s.index: s['shots_off_target'] = float((shot_outcome_series.isin(['Off T', 'Wayward'])).sum())
        if 'shots_penalty' in s.index: s['shots_penalty'] = float((shot_type_series == 'Penalty').sum())
        if 'shots_freekick' in s.index: s['shots_freekick'] = float((shot_type_series == 'Free Kick').sum())

    if 'conversion_rate_excl_xg_kpi' in s.index: s['conversion_rate_excl_xg_kpi'] = safe_division(s.get('goals',0.0), s.get('shots_total',0.0)) * 100
    if 'xg_performance' in s.index: s['xg_performance'] = s.get('goals',0.0) - s.get('sum_xg',0.0)

    # Passes
    pass_df = event_df[event_df['type'] == 'Pass'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not pass_df.empty:
        pass_outcome_series = pass_df.get('pass_outcome_name', pd.Series(dtype=str))
        pass_height_series = pass_df.get('pass_height_name', pd.Series(dtype=str))

        if 'successful_passes' in s.index:
            if not pass_outcome_series.empty:
                successful_mask = pass_outcome_series.isna() | (pass_outcome_series == 'nan') | (pass_outcome_series == '')
                s['successful_passes'] = float(successful_mask.sum())
            else: s['successful_passes'] = 0.0
        
        if 'avg_pass_length' in s.index: s['avg_pass_length'] = pd.to_numeric(pass_df.get('pass_length'), errors='coerce').mean()
        if 'goal_assists' in s.index: s['goal_assists'] = float((pass_df.get('pass_goal_assist', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'shot_assists' in s.index: s['shot_assists'] = float((pass_df.get('pass_shot_assist', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'crosses_total' in s.index: s['crosses_total'] = float((pass_df.get('pass_cross', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'switches_total' in s.index: s['switches_total'] = float((pass_df.get('pass_switch', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'through_balls_total' in s.index: s['through_balls_total'] = float((pass_df.get('pass_through_ball', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        
        if 'passes_ground' in s.index: s['passes_ground'] = float((pass_height_series == 'Ground Pass').sum())
        if 'passes_low' in s.index: s['passes_low'] = float((pass_height_series == 'Low Pass').sum())
        if 'passes_high' in s.index: s['passes_high'] = float((pass_height_series == 'High Pass').sum())

        if 'passes_outcome_incomplete' in s.index: s['passes_outcome_incomplete'] = float((pass_outcome_series == 'Incomplete').sum())
        if 'passes_outcome_out' in s.index: s['passes_outcome_out'] = float((pass_outcome_series == 'Out').sum())
        if 'passes_outcome_offside' in s.index: s['passes_outcome_offside'] = float((pass_outcome_series == 'Pass Offside').sum())
        if 'passes_outcome_injury_clearance' in s.index: s['passes_outcome_injury_clearance'] = float((pass_outcome_series == 'Injury Clearance').sum())
        
        if 'passes_backheel' in s.index: s['passes_backheel'] = float((pass_df.get('pass_backheel', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'passes_deflected_by_opponent' in s.index: s['passes_deflected_by_opponent'] = float((pass_df.get('deflected', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'passes_miscommunication' in s.index: s['passes_miscommunication'] = float((pass_df.get('miscommunication', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())

    if 'pass_completion_rate_kpi' in s.index: s['pass_completion_rate_kpi'] = safe_division(s.get('successful_passes',0.0), s.get('passes_total',0.0)) * 100
    if 'avg_pass_length_kpi' in s.index: s['avg_pass_length_kpi'] = s.get('avg_pass_length', 0.0) if pd.notna(s.get('avg_pass_length')) else 0.0

    # Dribbles
    dribble_df = event_df[event_df['type'] == 'Dribble'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not dribble_df.empty:
        dribble_outcome_series = dribble_df.get('dribble_outcome_name', pd.Series(dtype=str))
        if 'dribbles_completed' in s.index: s['dribbles_completed'] = float((dribble_outcome_series == 'Complete').sum())
        if 'dribbles_nutmeg' in s.index: s['dribbles_nutmeg'] = float((dribble_df.get('nutmeg', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'dribbles_overrun' in s.index: s['dribbles_overrun'] = float((dribble_df.get('overrun', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'dribbles_no_touch' in s.index: s['dribbles_no_touch'] = float((dribble_df.get('no_touch', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())

    if 'dribble_success_rate_kpi' in s.index: s['dribble_success_rate_kpi'] = safe_division(s.get('dribbles_completed', 0.0), s.get('dribbles_attempted',0.0)) * 100

    # Duels (Tackles, Aerials)
    duel_df = event_df[event_df['type'] == 'Duel'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not duel_df.empty:
        duel_type_series = duel_df.get('duel_type_name', pd.Series(dtype=str))
        duel_outcome_series = duel_df.get('duel_outcome_name', pd.Series(dtype=str))

        if 'duels_tackle_type' in s.index: s['duels_tackle_type'] = float((duel_type_series == 'Tackle').sum())
        if 'tackles_attempted' in s.index: s['tackles_attempted'] = s.get('duels_tackle_type', 0.0) # Àlies

        aerial_duels_mask = duel_type_series.str.contains("Aerial", case=False, na=False)
        if 'aerial_duels_total' in s.index: s['aerial_duels_total'] = float(aerial_duels_mask.sum())
        if 'duels_aerial_lost' in s.index: s['duels_aerial_lost'] = float((duel_type_series == 'Aerial Lost').sum())
        
        if 'tackles_won' in s.index:
            s['tackles_won'] = float(((duel_type_series == 'Tackle') & 
                                     (duel_outcome_series.isin(['Won', 'Success', 'Success In Play', 'Success Out']))).sum())
        if 'aerial_duels_won' in s.index:
             s['aerial_duels_won'] = float((aerial_duels_mask & duel_outcome_series.isin(['Won', 'Success'])).sum())
    
    if 'tackle_win_rate_kpi' in s.index: s['tackle_win_rate_kpi'] = safe_division(s.get('tackles_won',0.0), s.get('tackles_attempted',0.0)) * 100
    if 'aerial_duel_win_rate_kpi' in s.index: s['aerial_duel_win_rate_kpi'] = safe_division(s.get('aerial_duels_won',0.0), s.get('aerial_duels_total',0.0)) * 100
    
    # 50/50 Events (si és un tipus d'esdeveniment separat)
    fifty_fifty_df = event_df[event_df['type'] == '50/50'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not fifty_fifty_df.empty:
        fifty_outcome_series = fifty_fifty_df.get('outcome_name', fifty_fifty_df.get('outcome', pd.Series(dtype=str))) # outcome_name si ja parsejat
        if 'fifty_fifties_won' in s.index: s['fifty_fifties_won'] = float(fifty_outcome_series.isin(['Won', 'Success To Team']).sum())
        if 'fifty_fifties_lost' in s.index: s['fifty_fifties_lost'] = float(fifty_outcome_series.isin(['Lost', 'Success To Opposition']).sum())

    # Ball Recovery
    ball_recovery_df = event_df[event_df['type'] == 'Ball Recovery'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not ball_recovery_df.empty: 
        if 'ball_recoveries_offensive' in s.index: s['ball_recoveries_offensive'] = float((ball_recovery_df.get('offensive', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'ball_recoveries_failed' in s.index: s['ball_recoveries_failed'] = float((ball_recovery_df.get('recovery_failure', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())

    # Blocks
    block_df = event_df[event_df['type'] == 'Block'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not block_df.empty:
        if 'blocks_deflection' in s.index: s['blocks_deflection'] = float((block_df.get('deflection', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'blocks_offensive' in s.index: s['blocks_offensive'] = float((block_df.get('offensive', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
        if 'blocks_save_attempt' in s.index: s['blocks_save_attempt'] = float((block_df.get('save_block', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())

    # Clearances
    clearance_df = event_df[event_df['type'] == 'Clearance'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not clearance_df.empty:
        if 'clearances_aerial_won' in s.index: s['clearances_aerial_won'] = float((clearance_df.get('aerial_won', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())

    # Fouls
    foul_committed_df = event_df[event_df['type'] == 'Foul Committed'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not foul_committed_df.empty: 
        if 'fouls_committed_penalty' in s.index: s['fouls_committed_penalty'] = float((foul_committed_df.get('penalty', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
    
    foul_won_df = event_df[event_df['type'] == 'Foul Won'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not foul_won_df.empty: 
        if 'fouls_won_penalty' in s.index: s['fouls_won_penalty'] = float((foul_won_df.get('penalty', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())

    # Cards (from Bad Behaviour)
    bad_behaviour_df = event_df[event_df['type'] == 'Bad Behaviour'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not bad_behaviour_df.empty:
        card_series = bad_behaviour_df.get('bad_behaviour_card_name', pd.Series(dtype=str))
        if 'yellow_cards' in s.index: s['yellow_cards'] = float((card_series == 'Yellow Card').sum())
        if 'red_cards' in s.index: s['red_cards'] = float((card_series.isin(['Red Card', 'Second Yellow'])).sum())

    # Interceptions
    interception_df = event_df[event_df['type'] == 'Interception'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not interception_df.empty:
        interception_outcome_series = interception_df.get('interception_outcome_name', pd.Series(dtype=str)) 
        if 'interceptions_successful_gain_possession' in s.index: s['interceptions_successful_gain_possession'] = float(interception_outcome_series.isin(['Success', 'Success In Play', 'Won']).sum())
        if 'interceptions_failed_gain_possession' in s.index: s['interceptions_failed_gain_possession'] = float(interception_outcome_series.isin(['Lost', 'Lost In Play', 'Lost Out']).sum())
    
    # Carries (duration)
    carry_df = event_df[event_df['type'] == 'Carry'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not carry_df.empty and 'duration' in carry_df.columns:
        valid_durations = pd.to_numeric(carry_df['duration'], errors='coerce').dropna()
        if 'sum_carry_duration' in s.index: s['sum_carry_duration'] = float(valid_durations.sum())
        if 'avg_carry_duration' in s.index: s['avg_carry_duration'] = float(valid_durations.mean()) if not valid_durations.empty else 0.0
    
    # Miscontrol (aerial_won)
    miscontrol_df = event_df[event_df['type'] == 'Miscontrol'].copy() if 'type' in event_df.columns else pd.DataFrame()
    if not miscontrol_df.empty:
         if 'count_miscontrol_aerial_won' in s.index: 
             s['count_miscontrol_aerial_won'] = float((miscontrol_df.get('aerial_won', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum())
    
    # General defensive / pressure
    if 'counterpress_actions' in s.index: s['counterpress_actions'] = (event_df.get('counterpress', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()
    if 'actions_under_pressure' in s.index: s['actions_under_pressure'] = (event_df.get('under_pressure', pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()
    
    if 'turnovers_total' in s.index:
        s['turnovers_total'] = s.get('miscontrols', 0.0) + s.get('dispossessed_events', 0.0) + \
                               (s.get('dribbles_attempted', 0.0) - s.get('dribbles_completed', 0.0))
    if 'turnovers_p90_inv_kpi_base' in s.index:
        s['turnovers_p90_inv_kpi_base'] = safe_division(s.get('turnovers_total',0.0), num_90s_played) if use_p90 else (999.0 if s.get('turnovers_total',0.0) == 0 else s.get('turnovers_total',0.0))


    # --- P90 Calculations ---
    metrics_for_p90_conversion_from_func = [
        m for m in get_feature_names_for_extraction() 
        if not m.endswith(('_p90', '_kpi', '_sqrt_', '_base')) and 
           not m in ['age', 'season_numeric', 'num_90s_played', 'matches_played_events', 'avg_carry_duration']
    ]
    
    for col_raw in metrics_for_p90_conversion_from_func:
        if f'{col_raw}_p90' in s.index:
            s[f'{col_raw}_p90'] = safe_division(s.get(col_raw, 0.0), num_90s_played) if use_p90 else 0.0
    if 'progressive_carries_p90' in s.index and 'carries_total_p90' in s.index :
        s['progressive_carries_p90'] = s['carries_total_p90']
    if 'interceptions_p90' in s.index and 'interceptions_p90' in s.index:
        pass # ja calculat
    if 'clearances_p90' in s.index and 'clearances_p90' in s.index: 
        pass
    if 'blocks_p90' in s.index and 'blocks_total_p90' in s.index:
        s['blocks_p90'] = s['blocks_total_p90']
    if 'pressures_p90' in s.index and 'pressures_p90' in s.index: 
        pass

    # SQRT P90
    sqrt_transformed_kpis_base_p90 = ["goals_p90", "sum_xg_p90", "goal_assists_p90"]
    for kpi_base_p90_name in sqrt_transformed_kpis_base_p90:
        if f"{kpi_base_p90_name}_sqrt_" in s.index: 
            val = s.get(kpi_base_p90_name, 0.0) 
            s[f"{kpi_base_p90_name}_sqrt_"] = np.sqrt(val) if pd.notna(val) and val > 0 else 0.0
        
    return s.reindex(all_expected_features).fillna(0.0)

# --- Target Generation Functions  ---
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

def generate_potential_target(df_all_player_seasons, derived_kpi_weights_config):
    df = df_all_player_seasons.copy()
    df['raw_composite_score'] = 0.0
    df['potential_target'] = 0.0
    for position_group, weights in derived_kpi_weights_config.items():
        pos_mask = (df['general_position_identifier'] == position_group)
        if pos_mask.sum() == 0: 
            logger_trainer.debug(f"No players found for position group {position_group} in generate_potential_target. Skipping.")
            continue
        current_total_weight = sum(w for w in weights.values() if isinstance(w, (int, float)))
        if current_total_weight == 0: 
            logger_trainer.warning(f"Total weight is 0 for {position_group}. KPIs in this group will have 0 contribution.")
            current_total_weight = 1.0
        position_composite_score_series = pd.Series(0.0, index=df[pos_mask].index)
        df_pos_group_subset = df[pos_mask].copy()
        for kpi_col_name_in_weights, weight_value in weights.items():
            actual_weight = safe_division(weight_value, current_total_weight)
            data_col_for_calc = kpi_col_name_in_weights.replace('_inv_kpi', '_inv_kpi_base') if kpi_col_name_in_weights.endswith('_inv_kpi') else kpi_col_name_in_weights
            if data_col_for_calc not in df_pos_group_subset.columns: 
                logger_trainer.warning(f"KPI column {data_col_for_calc} not found for position {position_group}.")
                continue
            kpi_data_for_pos = df_pos_group_subset[data_col_for_calc].copy()
            min_val_kpi_pos, max_val_kpi_pos = kpi_data_for_pos.min(), kpi_data_for_pos.max()
            norm_value_series = pd.Series(0.0, index=kpi_data_for_pos.index)
            if pd.notna(min_val_kpi_pos) and pd.notna(max_val_kpi_pos):
                if max_val_kpi_pos > min_val_kpi_pos :
                    norm_value_series = (kpi_data_for_pos - min_val_kpi_pos) / (max_val_kpi_pos - min_val_kpi_pos)
                elif max_val_kpi_pos == min_val_kpi_pos and max_val_kpi_pos != 0:
                     norm_value_series[:] = 0.5
            if data_col_for_calc.endswith(('_p90', '_sqrt_', '_base')):
                 if 'num_90s_played' in df_pos_group_subset.columns:
                    low_mins_mask = df_pos_group_subset['num_90s_played'] < MIN_90S_PLAYED_FOR_P90_STATS
                    if not kpi_col_name_in_weights.endswith('_inv_kpi_base'):
                        norm_value_series[low_mins_mask] = 0.0
            if kpi_col_name_in_weights.endswith('_inv_kpi_base'):
                 position_composite_score_series += norm_value_series.fillna(0.0) * actual_weight
            else:
                position_composite_score_series += norm_value_series.fillna(0.0) * actual_weight
        df.loc[pos_mask, 'raw_composite_score'] = position_composite_score_series
        if pos_mask.sum() > 0:
            min_raw_score_group = df.loc[pos_mask, 'raw_composite_score'].min()
            max_raw_score_group = df.loc[pos_mask, 'raw_composite_score'].max()
            if max_raw_score_group == min_raw_score_group or pd.isna(max_raw_score_group) or pd.isna(min_raw_score_group):
                df.loc[pos_mask, 'potential_target'] = 100.0
            else:
                scaled_potential = ((df.loc[pos_mask, 'raw_composite_score'] - min_raw_score_group) / (max_raw_score_group - min_raw_score_group)) * 200.0
                df.loc[pos_mask, 'potential_target'] = scaled_potential.clip(0, 200).round(2)
    return df[['player_id_identifier', 'target_season_identifier', 'potential_target', 'raw_composite_score']]

# --- Config Saving Function ---
def trainer_save_model_run_config(filepath, model_name, feature_cols, model_params, 
                                  user_kpi_definitions_for_weights,
                                  user_composite_impact_kpis,
                                  derived_kpi_weights_actually_used,
                                  position_group_trained,
                                  best_params_from_search=None,
                                  evaluation_metrics=None):
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
        "description": f"Custom Model: Position-Specific ({position_group_trained}) XGBoost. Predicts PEAK CAREER POTENTIAL based on U21 data. Trained on all player data.",
        "features_used_for_ml_model": feature_cols,
        "ml_model_parameters": safe_model_params,
        "target_variable_generation": {
            "method": "Target is player's PEAK career potential score. Derived from max seasonal score across entire career. Seasonal score from user KPIs, correlation-derived weights, and position-group MinMax normalization. Scaled 0-200.",
            "user_selected_kpi_definitions_for_target_weights": user_kpi_definitions_for_weights.get(position_group_trained, []),
            "user_selected_composite_impact_kpis": user_composite_impact_kpis.get(position_group_trained, []),
            "derived_kpi_weights_for_target": derived_kpi_weights_actually_used.get(position_group_trained, {}),
            "base_features_list_source": "get_trainer_feature_names_for_extraction()",
            "min_90s_for_p90_kpi_reliability": MIN_90S_PLAYED_FOR_P90_STATS
        },
        "hyperparameter_search_used": best_params_from_search is not None,
        "position_group_trained_for": position_group_trained
    }
    if evaluation_metrics:
        config["evaluation_metrics_on_test_set"] = evaluation_metrics
    try:
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(config, f, indent=4)
        logger_trainer.info(f"Custom Model Run Configuration for {position_group_trained} saved to {filepath}")
    except IOError: logger_trainer.error(f"Error: Could not save custom model run configuration for {position_group_trained} to {filepath}")
    except TypeError as e: logger_trainer.error(f"TypeError during JSON serialization for {position_group_trained} custom model config: {e}.")


# --- Main Training Function  ---
# ... (tot el codi anterior a la funció es manté igual) ...

# --- Main Training Function (MODIFIED FOR 2015/2016 EVALUATION) ---
# def build_and_train_model_from_script_logic(
#     custom_model_id: str,
#     position_group_to_train: str,
#     user_kpi_definitions_for_weight_derivation: dict,
#     user_composite_impact_kpis: dict,
#     base_output_dir_for_custom_model: str,
#     user_ml_feature_subset: list = None
# ):
#     # <<< MODIFICACIÓ: Definim la temporada que serà el nostre conjunt de test
#     EVALUATION_SEASON = "2015_2016"
    
#     logger_trainer.info(f"Starting Custom Model Build (ID: {custom_model_id}) for Position: {position_group_to_train}")
#     # <<< MODIFICACIÓ: Actualitzem el log per reflectir la nova estratègia d'avaluació
#     logger_trainer.info(f"  STRATEGY: Train on all U21 data EXCEPT {EVALUATION_SEASON}, Evaluate EXCLUSIVELY on {EVALUATION_SEASON}.")

#     # ... (La primera part de la funció, fins a la construcció de 'full_ml_features_df', es manté igual) ...
#     try:
#         with open(PLAYER_INDEX_PATH, 'r', encoding='utf-8') as f: player_index = json.load(f)
#     except FileNotFoundError: 
#         msg = f"Trainer Error: Player index file not found at {PLAYER_INDEX_PATH}"
#         logger_trainer.error(msg); return False, msg
#     try:
#         minutes_df = pd.read_csv(PLAYER_MINUTES_PATH)
#         minutes_df['season_name_std'] = minutes_df['season_name'].str.replace('/', '_', regex=False)
#         minutes_df_dict = { (str(row['player_id']), row['season_name_std']): row['total_minutes_played']
#                             for _, row in minutes_df.iterrows() }
#     except FileNotFoundError: logger_trainer.warning(f"Trainer Warning: Player minutes file '{PLAYER_MINUTES_PATH}' not found."); minutes_df_dict = {}
#     except Exception as e: logger_trainer.error(f"Trainer Error loading minutes file: {e}."); minutes_df_dict = {}

#     all_season_features = []
#     logger_trainer.info("Trainer Pass 1: Extracting base features for ALL player-seasons to define performance universe.")
    
#     player_items = []
#     if isinstance(player_index, dict): player_items = player_index.items()
#     elif isinstance(player_index, list): player_items = [(p.get("name", str(p.get("player_id"))), p) for p in player_index]

#     for i, (player_name_from_key, p_info) in enumerate(player_items):
#         if (i + 1) % 200 == 0: logger_trainer.info(f"  Trainer Pass 1 - Processed {i+1}/{len(player_items)} players...")
#         player_id_str, dob, specific_pos_idx = str(p_info.get("player_id")), p_info.get("dob"), p_info.get("position")
#         if not all([player_id_str, dob, specific_pos_idx]): continue
#         general_pos_idx = get_general_position(specific_pos_idx)
#         if general_pos_idx in ["Goalkeeper", "Unknown"]: continue

#         for season_str in p_info.get("seasons", []):
#             if not (isinstance(season_str, str) and '_' in season_str): continue
            
#             age_at_season = get_age_at_fixed_point_in_season(dob, season_str)
#             if age_at_season is None: continue 
            
#             season_numeric = int(season_str.split('_')[0])
#             total_minutes = minutes_df_dict.get((player_id_str, season_str), 0.0); num_90s = safe_division(total_minutes, 90.0)
#             event_file_path = os.path.join(BASE_EVENT_DATA_PATH, season_str, "players", f"{player_id_str}_{season_str}.csv")
#             current_season_event_df = pd.DataFrame()
#             try:
#                 temp_df = pd.read_csv(event_file_path, dtype=object, low_memory=False)
#                 current_season_event_df = temp_df
#             except: pass 
            
#             base_features_series = extract_season_features(current_season_event_df, age_at_season, season_numeric, num_90s)
#             base_features_series['player_id_identifier'] = player_id_str
#             base_features_series['player_name_identifier'] = player_name_from_key
#             base_features_series['target_season_identifier'] = season_str
#             base_features_series['general_position_identifier'] = general_pos_idx
#             all_season_features.append(base_features_series)

#     if not all_season_features: 
#         msg = "Trainer: No player seasons data found for Pass 1. Cannot build model."
#         logger_trainer.error(msg); return False, msg
    
#     df_all_seasons_with_base_features = pd.DataFrame(all_season_features).fillna(0.0)
#     logger_trainer.info(f"Trainer Pass 1 Complete. Extracted base features for {len(df_all_seasons_with_base_features)} player-seasons (all ages).")

#     logger_trainer.info(f"\nTrainer: Deriving KPI weights using data from all players...")
#     derived_kpi_weights_all_groups = {} 
#     original_kpi_defs = KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION
#     original_impact_kpis = COMPOSITE_IMPACT_KPIS

#     for pos_g_loop in ["Attacker", "Midfielder", "Defender"]:
#         impact_kpis_to_use = user_composite_impact_kpis.get(pos_g_loop, original_impact_kpis.get(pos_g_loop, []))
#         target_kpis_to_use = user_kpi_definitions_for_weight_derivation.get(pos_g_loop, original_kpi_defs.get(pos_g_loop, []))
#         if not impact_kpis_to_use or not target_kpis_to_use:
#             logger_trainer.warning(f"  Trainer: KPI definitions missing for {pos_g_loop}. Using equal weights.")
        
#         derived_kpi_weights_all_groups[pos_g_loop] = derive_kpi_weights_from_impact_correlation(
#             df_all_seasons_with_base_features, pos_g_loop, impact_kpis_to_use, target_kpis_to_use
#         )
    
#     df_with_heuristic_targets = generate_potential_target(df_all_seasons_with_base_features.copy(), derived_kpi_weights_all_groups)
#     df_all_seasons_with_base_features = pd.merge(
#         df_all_seasons_with_base_features,
#         df_with_heuristic_targets[['player_id_identifier', 'target_season_identifier', 'potential_target', 'raw_composite_score']],
#         on=['player_id_identifier', 'target_season_identifier'], how='left').fillna(0.0)

#     logger_trainer.info("Trainer: Calculating PEAK career potential for each player.")
#     peak_potentials = df_all_seasons_with_base_features.groupby('player_id_identifier')['potential_target'].max().reset_index()
#     peak_potentials.rename(columns={'potential_target': 'peak_potential_target'}, inplace=True)
    
#     df_all_seasons_with_base_features = pd.merge(
#         df_all_seasons_with_base_features,
#         peak_potentials,
#         on='player_id_identifier',
#         how='left'
#     )

#     logger_trainer.info("Trainer: Filtering dataset to U21 seasons to create ML training instances.")
#     df_u21_instances_for_ml = df_all_seasons_with_base_features[df_all_seasons_with_base_features['age'] <= 21].copy()
    
#     if df_u21_instances_for_ml.empty:
#         msg = "Trainer: No U21 player seasons found to use as training instances. Cannot build model."
#         logger_trainer.error(msg); return False, msg

#     logger_trainer.info(f"\nTrainer Pass 2: Constructing full ML input features for {len(df_u21_instances_for_ml)} U21 instances...")
#     all_player_ml_feature_vectors = []
#     base_metric_names = get_feature_names_for_extraction()
    
#     df_all_seasons_with_base_features.sort_values(by=['player_id_identifier', 'season_numeric'], inplace=True)

#     for idx, current_u21_season_row in df_u21_instances_for_ml.iterrows():
#         if (idx + 1) % 100 == 0:
#             logger_trainer.info(f"  Trainer Pass 2 - Processed ML features for {idx + 1}/{len(df_u21_instances_for_ml)} U21 instances...")

#         player_id = current_u21_season_row['player_id_identifier']
#         current_season_numeric = current_u21_season_row['season_numeric']

#         historical_df_for_player = df_all_seasons_with_base_features[
#             (df_all_seasons_with_base_features['player_id_identifier'] == player_id) &
#             (df_all_seasons_with_base_features['season_numeric'] < current_season_numeric)
#         ].copy()

#         instance_ml_features = trainer_construct_ml_features_for_player_season(
#             current_season_base_features_row=current_u21_season_row,
#             historical_base_features_df=historical_df_for_player,
#             all_base_metric_names=base_metric_names
#         )

#         instance_ml_features['player_id_identifier'] = player_id
#         instance_ml_features['player_name_identifier'] = current_u21_season_row['player_name_identifier']
#         instance_ml_features['target_season_identifier'] = current_u21_season_row['target_season_identifier']
#         instance_ml_features['general_position_identifier'] = current_u21_season_row['general_position_identifier']
#         instance_ml_features['peak_potential_target'] = current_u21_season_row['peak_potential_target']
#         instance_ml_features['raw_composite_score_heuristic_value'] = current_u21_season_row.get('raw_composite_score', 0.0)
#         all_player_ml_feature_vectors.append(instance_ml_features)

#     if not all_player_ml_feature_vectors:
#         msg = "Trainer: No ML feature vectors constructed in Pass 2. Cannot train."
#         logger_trainer.error(msg); return False, msg
#     full_ml_features_df = pd.DataFrame(all_player_ml_feature_vectors).fillna(0.0)
#     logger_trainer.info(f"Trainer Pass 2 Complete. Full ML features constructed for {len(full_ml_features_df)} U21 instances.")

#     pos_df_for_training_all_features = full_ml_features_df[full_ml_features_df['general_position_identifier'] == position_group_to_train].copy()
#     if pos_df_for_training_all_features.empty or len(pos_df_for_training_all_features) < 10:
#         msg = f"Trainer: Not enough data for {position_group_to_train} ({len(pos_df_for_training_all_features)}) after ML feature construction. Cannot train model."
#         logger_trainer.error(msg); return False, msg

#     id_cols_ml = ['player_id_identifier', 'player_name_identifier', 'target_season_identifier',
#                   'general_position_identifier', 'peak_potential_target', 'raw_composite_score_heuristic_value']
#     all_available_ml_features_for_pos = [c for c in pos_df_for_training_all_features.columns if c not in id_cols_ml]
    
#     final_ml_feature_cols_for_model = []
#     if user_ml_feature_subset and isinstance(user_ml_feature_subset, list) and len(user_ml_feature_subset) > 0:
#         logger_trainer.info(f"  Trainer: Using user-defined subset of {len(user_ml_feature_subset)} ML features for training.")
#         final_ml_feature_cols_for_model = [feat for feat in user_ml_feature_subset if feat in all_available_ml_features_for_pos]
#         if not final_ml_feature_cols_for_model:
#             logger_trainer.warning("  Trainer: None of the user-selected ML features are valid/generated. Using all available as fallback.")
#             final_ml_feature_cols_for_model = all_available_ml_features_for_pos
#     else:
#         logger_trainer.info(f"  Trainer: Deriving ML feature set from user-selected target KPIs for {position_group_to_train}.")
#         selected_base_kpis_for_features = user_kpi_definitions_for_weight_derivation.get(position_group_to_train, [])
#         if not selected_base_kpis_for_features:
#             logger_trainer.warning(f"  Trainer: No base KPIs from user to guide feature selection for {position_group_to_train}. Using all {len(all_available_ml_features_for_pos)} generated ML features.");
#             final_ml_feature_cols_for_model = all_available_ml_features_for_pos
#         else:
#             temp_feature_list = []
#             for ml_feat_candidate in all_available_ml_features_for_pos:
#                 is_related = False
#                 for user_base_kpi in selected_base_kpis_for_features:
#                     if user_base_kpi in ml_feat_candidate:
#                         is_related = True; break
#                 if is_related: temp_feature_list.append(ml_feat_candidate)
#             context_features_to_add = ['current_age', 'current_season_numeric', 'current_num_90s_played', 'current_matches_played_events', 'num_hist_seasons']
#             for cf in context_features_to_add:
#                 if cf in all_available_ml_features_for_pos: temp_feature_list.append(cf)
#             final_ml_feature_cols_for_model = sorted(list(set(temp_feature_list)))
#             if not final_ml_feature_cols_for_model:
#                  logger_trainer.warning(f"  Trainer: No ML features derived from selected base KPIs for {position_group_to_train}. Using all generated features as fallback.")
#                  final_ml_feature_cols_for_model = all_available_ml_features_for_pos
    
#     if not final_ml_feature_cols_for_model:
#         msg = f"Trainer: No ML feature columns identified for {position_group_to_train}. Cannot train."
#         logger_trainer.error(msg); return False, msg
#     logger_trainer.info(f"  Trainer: Final ML features for {position_group_to_train} model ({len(final_ml_feature_cols_for_model)}): {final_ml_feature_cols_for_model[:5]}...")

#     X = pos_df_for_training_all_features[final_ml_feature_cols_for_model].copy()
#     y = pos_df_for_training_all_features['peak_potential_target'].copy()
    
#     for col in X.columns: X[col] = pd.to_numeric(X[col], errors='coerce')
#     X.fillna(0, inplace=True)
    
#     # <<< MODIFICACIÓ: SEPARACIÓ MANUAL DE TRAIN/TEST PER TEMPORADA >>>
#     logger_trainer.info(f"  Trainer: Manually splitting data. Test set = season {EVALUATION_SEASON}.")
    
#     # Identifiquem els índexs per a cada conjunt
#     test_indices = pos_df_for_training_all_features['target_season_identifier'] == EVALUATION_SEASON
#     # train_indices = pos_df_for_training_all_features['target_season_identifier'] != EVALUATION_SEASON
#     EVALUATION_SEASON_START_YEAR = int(EVALUATION_SEASON.split('_')[0])

#     # Afegim la columna 'season_numeric' a 'pos_df_for_training_all_features' si no existeix
#     # (Normalment es crea a 'all_player_ml_feature_vectors', però assegurem-nos que hi és)
#     if 'season_numeric' not in pos_df_for_training_all_features.columns:
#         # Aquesta línia potser no és necessària si el DataFrame ja la conté, però és una bona pràctica de seguretat
#         pos_df_for_training_all_features['season_numeric'] = pos_df_for_training_all_features['target_season_identifier'].apply(lambda x: int(x.split('_')[0]))

#     # La divisió correcta: entrenar NOMÉS amb temporades ANTERIORS a la d'avaluació
#     test_indices = pos_df_for_training_all_features['target_season_identifier'] == EVALUATION_SEASON
#     train_indices = pos_df_for_training_all_features['season_numeric'] < EVALUATION_SEASON_START_YEAR

#     X_train_df = X[train_indices]
#     y_train = y[train_indices]
#     X_test_df = X[test_indices]
#     y_test = y[test_indices]

#     # <<< MODIFICACIÓ: Informem de la mida dels conjunts
#     logger_trainer.info(f"  Trainer: Training set size: {len(X_train_df)} instances.")
#     logger_trainer.info(f"  Trainer: Test set (season {EVALUATION_SEASON}) size: {len(X_test_df)} instances.")
    
#     if X_train_df.empty:
#         msg = f"Trainer: Training set is empty after removing {EVALUATION_SEASON}. Cannot train."
#         logger_trainer.error(msg); return False, msg
#     if X_test_df.empty:
#         logger_trainer.warning(f"  Trainer: Test set for season {EVALUATION_SEASON} is empty. No evaluation will be possible.")
    
#     # <<< MODIFICACIÓ: Entrenem l'escalador NOMÉS amb les dades d'entrenament
#     pos_model_output_dir = os.path.join(base_output_dir_for_custom_model, custom_model_id, position_group_to_train.lower())
#     os.makedirs(pos_model_output_dir, exist_ok=True)
    
#     scaler_pos = StandardScaler()
#     X_train_scaled = scaler_pos.fit_transform(X_train_df)
    
#     # Si hi ha dades de test, les transformem amb l'escalador ja entrenat
#     X_test_scaled = np.array([])
#     if not X_test_df.empty:
#         X_test_scaled = scaler_pos.transform(X_test_df)
    
#     # <<< MODIFICACIÓ: Guardem l'escalador i els altres artefactes
#     pos_trained_model_path = os.path.join(pos_model_output_dir, f'potential_model_{position_group_to_train.lower()}_{custom_model_id}.joblib')
#     pos_model_config_path = os.path.join(pos_model_output_dir, f'model_config_{position_group_to_train.lower()}_{custom_model_id}.json')
#     pos_scaler_path = os.path.join(pos_model_output_dir, f'feature_scaler_{position_group_to_train.lower()}_{custom_model_id}.joblib')
#     joblib.dump(scaler_pos, pos_scaler_path)
    
#     # <<< MODIFICACIÓ: La secció de GroupKFold i train_test_split ja no és necessària.
#     # El RandomizedSearchCV es farà ara només sobre el conjunt d'entrenament.
    
#     # Per a la cerca d'hiperparàmetres, podem seguir utilitzant GroupKFold dins del conjunt d'entrenament
#     groups_train_for_search = pos_df_for_training_all_features[train_indices]['player_id_identifier']
#     unique_groups_train = groups_train_for_search.nunique()
    
#     cv_for_search = 3 # CV simple per defecte
#     if unique_groups_train >= 2:
#         n_cv_splits_inner = min(3, unique_groups_train)
#         if X_train_scaled.shape[0] >= n_cv_splits_inner * 2:
#             cv_for_search = GroupKFold(n_splits=n_cv_splits_inner)
#             logger_trainer.info(f"  Trainer: Using inner GroupKFold ({n_cv_splits_inner} splits) on the training set for RandomizedSearch.")
#         else:
#             groups_train_for_search = None # No es pot fer GroupKFold
#     else:
#         groups_train_for_search = None # No es pot fer GroupKFold
        
#     xgb_model_for_search = XGBRegressor(random_state=42, objective='reg:squarederror', n_jobs=-1)
#     xgb_param_grid = { 'n_estimators': [100, 200, 300, 500], 'learning_rate': [0.01, 0.03, 0.05, 0.1], 'max_depth': [3, 4, 5, 6, 7], 'subsample': [0.6, 0.7, 0.8, 0.9, 1.0], 'colsample_bytree': [0.6, 0.7, 0.8, 0.9], 'gamma': [0, 0.1, 0.2], 'reg_alpha': [0, 0.005, 0.01, 0.05], 'reg_lambda': [0.1, 0.5, 1, 1.5] }
#     n_iter_search = 20 if X_train_scaled.shape[0] > 50 else max(1, int(X_train_scaled.shape[0] * 0.1))
#     if X_train_scaled.shape[0] < 10: n_iter_search = max(1, X_train_scaled.shape[0] // 2)
#     random_search = RandomizedSearchCV(estimator=xgb_model_for_search, param_distributions=xgb_param_grid, n_iter=n_iter_search, cv=cv_for_search, scoring='r2', random_state=42, n_jobs=-1, verbose=0)
    
#     logger_trainer.info(f"  Trainer: Starting RandomizedSearchCV for {position_group_to_train} on {X_train_scaled.shape[0]} training samples (n_iter={n_iter_search}).")
#     best_xgb_model, best_params_for_config, hyperparam_search_done = None, None, False
    
#     try:
#         search_groups_param = groups_train_for_search if isinstance(cv_for_search, GroupKFold) else None
#         random_search.fit(X_train_scaled, y_train, groups=search_groups_param)
#         best_params_from_search = random_search.best_params_
#         logger_trainer.info(f"  Trainer: Best XGBoost Params for {position_group_to_train} from Search: {best_params_from_search}")
#         best_xgb_model = XGBRegressor(**best_params_from_search, random_state=42, objective='reg:squarederror', n_jobs=-1)
        
#         # <<< MODIFICACIÓ: Early stopping amb el nostre conjunt de test específic
#         if X_test_scaled.shape[0] > 0:
#             best_xgb_model.set_params(early_stopping_rounds=10)
#             best_xgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)
#         else:
#             best_xgb_model.fit(X_train_scaled, y_train, verbose=False)
        
#         best_params_for_config, hyperparam_search_done = best_params_from_search, True
#     except Exception as e_search:
#         logger_trainer.error(f"  Trainer: Error during RandomizedSearchCV for {position_group_to_train}: {e_search}. Training with default params.")
#         default_params = {'n_estimators': 100, 'max_depth': 4, 'learning_rate': 0.05, 'random_state': 42, 'objective': 'reg:squarederror', 'n_jobs': -1}
#         best_xgb_model = XGBRegressor(**default_params)
#         if X_test_scaled.shape[0] > 0:
#             best_xgb_model.set_params(early_stopping_rounds=10)
#             best_xgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)
#         else:
#             best_xgb_model.fit(X_train_scaled, y_train, verbose=False)
#         best_params_for_config, hyperparam_search_done = best_xgb_model.get_params(), False
    
#     joblib.dump(best_xgb_model, pos_trained_model_path)
    
#     # <<< MODIFICACIÓ: L'avaluació es fa sempre sobre el conjunt de test (2015/2016), si existeix.
#     evaluation_metrics_dict = None
#     if X_test_scaled.shape[0] > 0 and y_test.shape[0] > 0:
#         y_pred_test = np.clip(best_xgb_model.predict(X_test_scaled), 0, 200)
#         mae = mean_absolute_error(y_test, y_pred_test)
#         mse = mean_squared_error(y_test, y_pred_test)
#         rmse = np.sqrt(mse)
#         r2 = r2_score(y_test, y_pred_test)
#         evaluation_metrics_dict = {'MAE': round(mae, 3), 'MSE': round(mse, 3), 'RMSE': round(rmse, 3), 'R2': round(r2, 3)}
        
#         # <<< MODIFICACIÓ: El log ara especifica clarament sobre què s'avalua.
#         logger_trainer.info(f"  Trainer: Evaluation for {position_group_to_train} (ID: {custom_model_id}) on test set (SEASON {EVALUATION_SEASON}, {X_test_scaled.shape[0]} samples):")
#         logger_trainer.info(f"    MAE: {mae:.3f}, MSE: {mse:.3f}, RMSE: {rmse:.3f}, R^2: {r2:.3f}")
        
#         if hasattr(best_xgb_model, 'feature_importances_'):
#             importances = best_xgb_model.feature_importances_
#             if len(final_ml_feature_cols_for_model) == len(importances):
#                 feat_imp_df = pd.DataFrame({'feature': final_ml_feature_cols_for_model, 'importance': importances}).sort_values('importance', ascending=False).head(20)
#                 logger_trainer.info(f"  Trainer: Top Feature Importances for {position_group_to_train} (ID: {custom_model_id}):\n{feat_imp_df.to_string(index=False)}")

#     trainer_save_model_run_config(
#         pos_model_config_path, model_name=f"XGBRegressor_Custom_{custom_model_id}", feature_cols=final_ml_feature_cols_for_model, 
#         model_params=best_xgb_model.get_params(), user_kpi_definitions_for_weights=user_kpi_definitions_for_weight_derivation,
#         user_composite_impact_kpis=user_composite_impact_kpis, derived_kpi_weights_actually_used=derived_kpi_weights_all_groups,
#         position_group_trained=position_group_to_train, best_params_from_search=best_params_for_config if hyperparam_search_done else None,
#         evaluation_metrics=evaluation_metrics_dict
#     )
    
#     logger_trainer.info(f"Custom Model for {position_group_to_train} (ID: {custom_model_id}) trained and artifacts saved to {pos_model_output_dir}")
#     return True, f"Model for {position_group_to_train} (ID: {custom_model_id}) built successfully."

def build_and_train_model_from_script_logic(
    s3_client,
    r2_bucket_name,
    custom_model_id: str,
    position_group_to_train: str,
    user_kpi_definitions_for_weight_derivation: dict,
    user_composite_impact_kpis: dict,
    base_output_dir_for_custom_model: str, # Ja no es fa servir per a rutes, però es manté per compatibilitat de la crida
    user_ml_feature_subset: list = None
):
    EVALUATION_SEASON = "2015_2016"
    
    logger_trainer.info(f"Starting Custom Model Build (ID: {custom_model_id}) for Position: {position_group_to_train}")
    logger_trainer.info(f"  STRATEGY: Train on all U21 data EXCEPT {EVALUATION_SEASON}, Evaluate EXCLUSIVELY on {EVALUATION_SEASON}.")

    if not s3_client:
        return False, "Trainer Error: S3 client is not available."

    try:
        response = s3_client.get_object(Bucket=r2_bucket_name, Key="data/player_index.json")
        content = response['Body'].read().decode('utf-8')
        player_index = json.loads(content)
    except Exception as e:
        msg = f"Trainer Error: Player index file not found in R2. Error: {e}"
        logger_trainer.error(msg); return False, msg

    try:
        response_minutes = s3_client.get_object(Bucket=r2_bucket_name, Key="data/player_season_minutes_with_names.csv")
        minutes_content = response_minutes['Body'].read().decode('utf-8')
        minutes_df = pd.read_csv(StringIO(minutes_content))
        minutes_df['season_name_std'] = minutes_df['season_name'].str.replace('/', '_', regex=False)
        minutes_df_dict = { (str(row['player_id']), row['season_name_std']): row['total_minutes_played'] for _, row in minutes_df.iterrows() }
    except Exception as e:
        logger_trainer.warning(f"Trainer Warning: Player minutes file not found in R2. Error: {e}");
        minutes_df_dict = {}

    all_season_features = []
    logger_trainer.info("Trainer Pass 1: Extracting base features for ALL player-seasons from R2.")
    
    player_items = list(player_index.items()) if isinstance(player_index, dict) else [(p.get("name", str(p.get("player_id"))), p) for p in player_index]

    for i, (player_name_from_key, p_info) in enumerate(player_items):
        if (i + 1) % 200 == 0: logger_trainer.info(f"  Trainer Pass 1 - Processed {i+1}/{len(player_items)} players...")
        player_id_str, dob, specific_pos_idx = str(p_info.get("player_id")), p_info.get("dob"), p_info.get("position")
        if not all([player_id_str, dob, specific_pos_idx]): continue
        general_pos_idx = get_general_position(specific_pos_idx)
        if general_pos_idx in ["Goalkeeper", "Unknown"]: continue

        for season_str in p_info.get("seasons", []):
            if not (isinstance(season_str, str) and '_' in season_str): continue
            
            age_at_season = get_age_at_fixed_point_in_season(dob, season_str)
            if age_at_season is None: continue 
            
            season_numeric = int(season_str.split('_')[0])
            total_minutes = minutes_df_dict.get((player_id_str, season_str), 0.0); num_90s = safe_division(total_minutes, 90.0)
            
            event_file_key = f"data/{season_str}/players/{player_id_str}_{season_str}.csv"
            current_season_event_df = pd.DataFrame()
            try:
                response_event = s3_client.get_object(Bucket=r2_bucket_name, Key=event_file_key)
                event_content = response_event['Body'].read().decode('utf-8')
                current_season_event_df = pd.read_csv(StringIO(event_content), dtype=object, low_memory=False)
            except s3_client.exceptions.NoSuchKey:
                pass
            except Exception as e:
                 logger_trainer.warning(f"Could not load event file {event_file_key} from R2: {e}")

            base_features_series = extract_season_features(current_season_event_df, age_at_season, season_numeric, num_90s)
            base_features_series['player_id_identifier'] = player_id_str
            base_features_series['player_name_identifier'] = player_name_from_key
            base_features_series['target_season_identifier'] = season_str
            base_features_series['general_position_identifier'] = general_pos_idx
            all_season_features.append(base_features_series)

    if not all_season_features: 
        msg = "Trainer: No player seasons data found for Pass 1. Cannot build model."
        logger_trainer.error(msg); return False, msg
    
    df_all_seasons_with_base_features = pd.DataFrame(all_season_features).fillna(0.0)
    
    # ... [LA RESTA DEL CODI DE LÒGICA D'ENTRENAMENT ES MANTÉ EXACTAMENT IGUAL FINS AL FINAL] ...
    # ... Aquesta part no canvia perquè només opera sobre DataFrames en memòria ...
    logger_trainer.info(f"Trainer Pass 1 Complete. Extracted base features for {len(df_all_seasons_with_base_features)} player-seasons (all ages).")
    logger_trainer.info(f"\nTrainer: Deriving KPI weights using data from all players...")
    derived_kpi_weights_all_groups = {} 
    original_kpi_defs = KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION
    original_impact_kpis = COMPOSITE_IMPACT_KPIS
    for pos_g_loop in ["Attacker", "Midfielder", "Defender"]:
        impact_kpis_to_use = user_composite_impact_kpis.get(pos_g_loop, original_impact_kpis.get(pos_g_loop, []))
        target_kpis_to_use = user_kpi_definitions_for_weight_derivation.get(pos_g_loop, original_kpi_defs.get(pos_g_loop, []))
        if not impact_kpis_to_use or not target_kpis_to_use:
            logger_trainer.warning(f"  Trainer: KPI definitions missing for {pos_g_loop}. Using equal weights.")
        
        derived_kpi_weights_all_groups[pos_g_loop] = derive_kpi_weights_from_impact_correlation(
            df_all_seasons_with_base_features, pos_g_loop, impact_kpis_to_use, target_kpis_to_use
        )
    df_with_heuristic_targets = generate_potential_target(df_all_seasons_with_base_features.copy(), derived_kpi_weights_all_groups)
    df_all_seasons_with_base_features = pd.merge(
        df_all_seasons_with_base_features,
        df_with_heuristic_targets[['player_id_identifier', 'target_season_identifier', 'potential_target', 'raw_composite_score']],
        on=['player_id_identifier', 'target_season_identifier'], how='left').fillna(0.0)
    logger_trainer.info("Trainer: Calculating PEAK career potential for each player.")
    peak_potentials = df_all_seasons_with_base_features.groupby('player_id_identifier')['potential_target'].max().reset_index()
    peak_potentials.rename(columns={'potential_target': 'peak_potential_target'}, inplace=True)
    df_all_seasons_with_base_features = pd.merge(
        df_all_seasons_with_base_features, peak_potentials, on='player_id_identifier', how='left'
    )
    logger_trainer.info("Trainer: Filtering dataset to U21 seasons to create ML training instances.")
    df_u21_instances_for_ml = df_all_seasons_with_base_features[df_all_seasons_with_base_features['age'] <= 21].copy()
    if df_u21_instances_for_ml.empty:
        msg = "Trainer: No U21 player seasons found to use as training instances. Cannot build model."
        logger_trainer.error(msg); return False, msg
    logger_trainer.info(f"\nTrainer Pass 2: Constructing full ML input features for {len(df_u21_instances_for_ml)} U21 instances...")
    all_player_ml_feature_vectors = []
    base_metric_names = get_feature_names_for_extraction()
    df_all_seasons_with_base_features.sort_values(by=['player_id_identifier', 'season_numeric'], inplace=True)
    for idx, current_u21_season_row in df_u21_instances_for_ml.iterrows():
        if (idx + 1) % 100 == 0:
            logger_trainer.info(f"  Trainer Pass 2 - Processed ML features for {idx + 1}/{len(df_u21_instances_for_ml)} U21 instances...")
        player_id = current_u21_season_row['player_id_identifier']
        current_season_numeric = current_u21_season_row['season_numeric']
        historical_df_for_player = df_all_seasons_with_base_features[
            (df_all_seasons_with_base_features['player_id_identifier'] == player_id) &
            (df_all_seasons_with_base_features['season_numeric'] < current_season_numeric)
        ].copy()
        instance_ml_features = trainer_construct_ml_features_for_player_season(
            current_season_base_features_row=current_u21_season_row,
            historical_base_features_df=historical_df_for_player,
            all_base_metric_names=base_metric_names
        )
        instance_ml_features['player_id_identifier'] = player_id
        instance_ml_features['player_name_identifier'] = current_u21_season_row['player_name_identifier']
        instance_ml_features['target_season_identifier'] = current_u21_season_row['target_season_identifier']
        instance_ml_features['general_position_identifier'] = current_u21_season_row['general_position_identifier']
        instance_ml_features['peak_potential_target'] = current_u21_season_row['peak_potential_target']
        instance_ml_features['raw_composite_score_heuristic_value'] = current_u21_season_row.get('raw_composite_score', 0.0)
        all_player_ml_feature_vectors.append(instance_ml_features)
    if not all_player_ml_feature_vectors:
        msg = "Trainer: No ML feature vectors constructed in Pass 2. Cannot train."
        logger_trainer.error(msg); return False, msg
    full_ml_features_df = pd.DataFrame(all_player_ml_feature_vectors).fillna(0.0)
    logger_trainer.info(f"Trainer Pass 2 Complete. Full ML features constructed for {len(full_ml_features_df)} U21 instances.")
    pos_df_for_training_all_features = full_ml_features_df[full_ml_features_df['general_position_identifier'] == position_group_to_train].copy()
    if pos_df_for_training_all_features.empty or len(pos_df_for_training_all_features) < 10:
        msg = f"Trainer: Not enough data for {position_group_to_train} ({len(pos_df_for_training_all_features)}) after ML feature construction. Cannot train model."
        logger_trainer.error(msg); return False, msg
    id_cols_ml = ['player_id_identifier', 'player_name_identifier', 'target_season_identifier', 'general_position_identifier', 'peak_potential_target', 'raw_composite_score_heuristic_value']
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
    X = pos_df_for_training_all_features[final_ml_feature_cols_for_model].copy()
    y = pos_df_for_training_all_features['peak_potential_target'].copy()
    for col in X.columns: X[col] = pd.to_numeric(X[col], errors='coerce')
    X.fillna(0, inplace=True)
    logger_trainer.info(f"  Trainer: Manually splitting data. Test set = season {EVALUATION_SEASON}.")
    if 'season_numeric' not in pos_df_for_training_all_features.columns:
        pos_df_for_training_all_features['season_numeric'] = pos_df_for_training_all_features['target_season_identifier'].apply(lambda x: int(x.split('_')[0]))
    EVALUATION_SEASON_START_YEAR = int(EVALUATION_SEASON.split('_')[0])
    test_indices = pos_df_for_training_all_features['target_season_identifier'] == EVALUATION_SEASON
    train_indices = pos_df_for_training_all_features['season_numeric'] < EVALUATION_SEASON_START_YEAR
    X_train_df, y_train = X[train_indices], y[train_indices]
    X_test_df, y_test = X[test_indices], y[test_indices]
    logger_trainer.info(f"  Trainer: Training set size: {len(X_train_df)} instances.")
    logger_trainer.info(f"  Trainer: Test set (season {EVALUATION_SEASON}) size: {len(X_test_df)} instances.")
    if X_train_df.empty:
        msg = f"Trainer: Training set is empty after removing {EVALUATION_SEASON}. Cannot train."
        logger_trainer.error(msg); return False, msg
    if X_test_df.empty:
        logger_trainer.warning(f"  Trainer: Test set for season {EVALUATION_SEASON} is empty. No evaluation will be possible.")
    scaler_pos = StandardScaler()
    X_train_scaled = scaler_pos.fit_transform(X_train_df)
    X_test_scaled = np.array([])
    if not X_test_df.empty: X_test_scaled = scaler_pos.transform(X_test_df)
    groups_train_for_search = pos_df_for_training_all_features[train_indices]['player_id_identifier']
    unique_groups_train = groups_train_for_search.nunique()
    cv_for_search = 3
    if unique_groups_train >= 2:
        n_cv_splits_inner = min(3, unique_groups_train)
        if X_train_scaled.shape[0] >= n_cv_splits_inner * 2:
            cv_for_search = GroupKFold(n_splits=n_cv_splits_inner)
            logger_trainer.info(f"  Trainer: Using inner GroupKFold ({n_cv_splits_inner} splits) on the training set for RandomizedSearch.")
        else: groups_train_for_search = None
    else: groups_train_for_search = None
    xgb_model_for_search = XGBRegressor(random_state=42, objective='reg:squarederror', n_jobs=-1)
    xgb_param_grid = { 'n_estimators': [100, 200, 300, 500], 'learning_rate': [0.01, 0.03, 0.05, 0.1], 'max_depth': [3, 4, 5, 6, 7], 'subsample': [0.6, 0.7, 0.8, 0.9, 1.0], 'colsample_bytree': [0.6, 0.7, 0.8, 0.9], 'gamma': [0, 0.1, 0.2], 'reg_alpha': [0, 0.005, 0.01, 0.05], 'reg_lambda': [0.1, 0.5, 1, 1.5] }
    n_iter_search = 20 if X_train_scaled.shape[0] > 50 else max(1, int(X_train_scaled.shape[0] * 0.1))
    if X_train_scaled.shape[0] < 10: n_iter_search = max(1, X_train_scaled.shape[0] // 2)
    random_search = RandomizedSearchCV(estimator=xgb_model_for_search, param_distributions=xgb_param_grid, n_iter=n_iter_search, cv=cv_for_search, scoring='r2', random_state=42, n_jobs=-1, verbose=0)
    logger_trainer.info(f"  Trainer: Starting RandomizedSearchCV for {position_group_to_train} on {X_train_scaled.shape[0]} training samples (n_iter={n_iter_search}).")
    best_xgb_model, best_params_for_config, hyperparam_search_done = None, None, False
    try:
        search_groups_param = groups_train_for_search if isinstance(cv_for_search, GroupKFold) else None
        random_search.fit(X_train_scaled, y_train, groups=search_groups_param)
        best_params_from_search = random_search.best_params_
        logger_trainer.info(f"  Trainer: Best XGBoost Params for {position_group_to_train} from Search: {best_params_from_search}")
        best_xgb_model = XGBRegressor(**best_params_from_search, random_state=42, objective='reg:squarederror', n_jobs=-1)
        if X_test_scaled.shape[0] > 0:
            best_xgb_model.set_params(early_stopping_rounds=10)
            best_xgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)
        else: best_xgb_model.fit(X_train_scaled, y_train, verbose=False)
        best_params_for_config, hyperparam_search_done = best_params_from_search, True
    except Exception as e_search:
        logger_trainer.error(f"  Trainer: Error during RandomizedSearchCV for {position_group_to_train}: {e_search}. Training with default params.")
        default_params = {'n_estimators': 100, 'max_depth': 4, 'learning_rate': 0.05, 'random_state': 42, 'objective': 'reg:squarederror', 'n_jobs': -1}
        best_xgb_model = XGBRegressor(**default_params)
        if X_test_scaled.shape[0] > 0:
            best_xgb_model.set_params(early_stopping_rounds=10)
            best_xgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)
        else: best_xgb_model.fit(X_train_scaled, y_train, verbose=False)
        best_params_for_config, hyperparam_search_done = best_xgb_model.get_params(), False
    evaluation_metrics_dict = None
    if X_test_scaled.shape[0] > 0 and y_test.shape[0] > 0:
        y_pred_test = np.clip(best_xgb_model.predict(X_test_scaled), 0, 200)
        mae = mean_absolute_error(y_test, y_pred_test); mse = mean_squared_error(y_test, y_pred_test)
        rmse = np.sqrt(mse); r2 = r2_score(y_test, y_pred_test)
        evaluation_metrics_dict = {'MAE': round(mae, 3), 'MSE': round(mse, 3), 'RMSE': round(rmse, 3), 'R2': round(r2, 3)}
        logger_trainer.info(f"  Trainer: Evaluation for {position_group_to_train} (ID: {custom_model_id}) on test set (SEASON {EVALUATION_SEASON}, {X_test_scaled.shape[0]} samples):")
        logger_trainer.info(f"    MAE: {mae:.3f}, MSE: {mse:.3f}, RMSE: {rmse:.3f}, R^2: {r2:.3f}")

    # --- INICI DEL BLOC PER GUARDAR A R2 ---
    
    # 1. Guardar l'escalador a R2
    try:
        with BytesIO() as f_scaler:
            joblib.dump(scaler_pos, f_scaler)
            f_scaler.seek(0)
            scaler_key = f"ml_models/custom_models/{custom_model_id}/{position_group_to_train.lower()}/feature_scaler_{position_group_to_train.lower()}_{custom_model_id}.joblib"
            s3_client.upload_fileobj(f_scaler, r2_bucket_name, scaler_key)
            logger_trainer.info(f"Scaler for {custom_model_id} uploaded to R2: {scaler_key}")
    except Exception as e:
        msg = f"Failed to upload scaler to R2 for {custom_model_id}: {e}"
        logger_trainer.error(msg); return False, msg

    # 2. Guardar el model a R2
    try:
        with BytesIO() as f_model:
            joblib.dump(best_xgb_model, f_model)
            f_model.seek(0)
            model_key = f"ml_models/custom_models/{custom_model_id}/{position_group_to_train.lower()}/potential_model_{position_group_to_train.lower()}_{custom_model_id}.joblib"
            s3_client.upload_fileobj(f_model, r2_bucket_name, model_key)
            logger_trainer.info(f"Model for {custom_model_id} uploaded to R2: {model_key}")
    except Exception as e:
        msg = f"Failed to upload model to R2 for {custom_model_id}: {e}"
        logger_trainer.error(msg); return False, msg
        
    # 3. Construir i guardar la configuració a R2
    safe_model_params = {}
    actual_params_to_save = best_params_for_config if hyperparam_search_done else best_xgb_model.get_params()
    for k, v in actual_params_to_save.items():
        if isinstance(v, np.generic): safe_model_params[k] = v.item()
        else: safe_model_params[k] = v
    
    config = {
        "model_type": f"XGBRegressor_Custom_{custom_model_id}_for_{position_group_to_train}",
        "description": f"Custom Model: Position-Specific ({position_group_to_train}) XGBoost. Predicts PEAK CAREER POTENTIAL based on U21 data. Trained on all player data.",
        "features_used_for_ml_model": final_ml_feature_cols_for_model,
        "ml_model_parameters": safe_model_params,
        "target_variable_generation": {
            "method": "Target is player's PEAK career potential score. Derived from max seasonal score across entire career. Seasonal score from user KPIs, correlation-derived weights, and position-group MinMax normalization. Scaled 0-200.",
            "user_selected_kpi_definitions_for_target_weights": user_kpi_definitions_for_weight_derivation.get(position_group_to_train, []),
            "user_selected_composite_impact_kpis": user_composite_impact_kpis.get(position_group_to_train, []),
            "derived_kpi_weights_for_target": derived_kpi_weights_all_groups.get(position_group_to_train, {}),
            "base_features_list_source": "get_trainer_feature_names_for_extraction()",
            "min_90s_for_p90_kpi_reliability": MIN_90S_PLAYED_FOR_P90_STATS
        },
        "hyperparameter_search_used": hyperparam_search_done,
        "position_group_trained_for": position_group_to_train
    }
    if evaluation_metrics_dict:
        config["evaluation_metrics_on_test_set"] = evaluation_metrics_dict

    try:
        config_json_string = json.dumps(config, indent=4)
        config_key = f"ml_models/custom_models/{custom_model_id}/{position_group_to_train.lower()}/model_config_{position_group_to_train.lower()}_{custom_model_id}.json"
        s3_client.put_object(Bucket=r2_bucket_name, Key=config_key, Body=config_json_string.encode('utf-8'))
        logger_trainer.info(f"Config for {custom_model_id} uploaded to R2: {config_key}")
    except Exception as e:
        msg = f"Failed to upload config to R2 for {custom_model_id}: {e}"
        logger_trainer.error(msg); return False, msg

    # --- FINAL DEL BLOC PER GUARDAR A R2 ---
    
    logger_trainer.info(f"Custom Model for {position_group_to_train} (ID: {custom_model_id}) trained and artifacts saved to R2.")
    return True, f"Model for {position_group_to_train} (ID: {custom_model_id}) built successfully and saved to cloud storage."


# --- Functions to expose constants and logic to main.py (no changes needed) ---
def get_trainer_kpi_definitions_for_weight_derivation():
    return KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION

def get_trainer_composite_impact_kpis_definitions():
    return COMPOSITE_IMPACT_KPIS

def trainer_construct_ml_features_for_player_season(
    current_season_base_features_row: pd.Series, 
    historical_base_features_df: pd.DataFrame,   
    all_base_metric_names: list                    
):
    instance_ml_features = pd.Series(dtype='float64')
    for base_fname in all_base_metric_names:
        instance_ml_features[f'current_{base_fname}'] = current_season_base_features_row.get(base_fname, 0.0)
    general_pos_current = current_season_base_features_row.get('general_position_identifier')
    interaction_poly_features_all_pos = [ 'current_inter_goals_x_conversion', 'current_poly_goals_p90_sqrt_sq', 'current_inter_drib_x_prog_carry', 'current_inter_succpass_x_comprate', 'current_poly_successful_passes_p90_sq', 'current_inter_kpsa_x_prog_carry', 'current_inter_tackles_x_rate', 'current_poly_tackles_won_p90_sq', 'current_inter_aerials_x_rate' ]
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
    for base_fname_hist in all_base_metric_names:
        for agg_prefix in ['hist_avg_', 'hist_sum_', 'hist_max_', 'hist_trend_', 'growth_', 'growth_ratio_']:
            instance_ml_features[f'{agg_prefix}{base_fname_hist}'] = 0.0
    instance_ml_features['num_hist_seasons'] = 0.0
    if historical_base_features_df is not None and not historical_base_features_df.empty:
        df_history = historical_base_features_df.copy()
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
                            slope, _ = np.polyfit(x_h_valid.astype(float), y_h_valid.astype(float), 1)
                            instance_ml_features[f'hist_trend_{col_name_base_hist}'] = slope
                        except (np.linalg.LinAlgError, TypeError, ValueError): 
                            instance_ml_features[f'hist_trend_{col_name_base_hist}'] = 0.0
    return instance_ml_features

def get_trainer_all_possible_ml_feature_names():
    base_metric_names = get_feature_names_for_extraction()
    possible_ml_features = set()
    for base_fname in base_metric_names:
        possible_ml_features.add(f'current_{base_fname}')
    interaction_poly_features_all_pos = [ 'current_inter_goals_x_conversion', 'current_poly_goals_p90_sqrt_sq', 'current_inter_drib_x_prog_carry', 'current_inter_succpass_x_comprate',  'current_poly_successful_passes_p90_sq', 'current_inter_kpsa_x_prog_carry', 'current_inter_tackles_x_rate', 'current_poly_tackles_won_p90_sq', 'current_inter_aerials_x_rate' ]
    for feat_name in interaction_poly_features_all_pos:
        possible_ml_features.add(feat_name)
    for base_fname_hist in base_metric_names:
        for agg_prefix in ['hist_avg_', 'hist_sum_', 'hist_max_', 'hist_trend_', 'growth_', 'growth_ratio_']:
            possible_ml_features.add(f'{agg_prefix}{base_fname_hist}')
    possible_ml_features.add('num_hist_seasons')
    return sorted(list(possible_ml_features))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger_trainer.info("Running trainer.py directly to generate default models with peak performance logic...")
    v14_output_dir_main = os.path.join(_PROJECT_ROOT, 'ml_models', 'ml_model_files_peak_potential')
    for pos_group in ["Attacker", "Midfielder", "Defender"]:
        logger_trainer.info(f"\n--- Generating peak potential model for: {pos_group} ---")
        success, message = build_and_train_model_from_script_logic(
            custom_model_id="peak_potential_v2_15_16",
            position_group_to_train=pos_group,
            user_kpi_definitions_for_weight_derivation=KPI_DEFINITIONS_FOR_WEIGHT_DERIVATION,
            user_composite_impact_kpis=COMPOSITE_IMPACT_KPIS,
            user_ml_feature_subset=None,
            base_output_dir_for_custom_model=v14_output_dir_main
        )
        if success: logger_trainer.info(message)
        else: logger_trainer.error(f"Failed to build model for {pos_group}: {message}")
    logger_trainer.info("\nDefault peak potential model generation process complete.")