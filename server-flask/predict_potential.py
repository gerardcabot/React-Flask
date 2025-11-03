import os
import pandas as pd
import joblib
import json
from datetime import datetime
import numpy as np
import logging
from typing import Optional 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from model_trainer.trainer_v2 import (
        get_age_at_fixed_point_in_season,
        get_general_position,
        extract_season_features,
        trainer_construct_ml_features_for_player_season,
        safe_division
    )
except ImportError:
    logging.error("No s'ha pogut importar des de 'model_trainer.trainer'. Assegura't que l'script 'predict_potential.py' està en el directori correcte (p. ex., 'server-flask/') i que 'model_trainer' té un fitxer '__init__.py'.")
    exit()

_PREDICTOR_SCRIPT_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_PREDICTOR_SCRIPT_DIR, '..'))
_DATA_DIR = os.path.join(_PROJECT_ROOT, 'data')
_MODELS_DIR = os.path.join(_PROJECT_ROOT, 'ml_models', 'ml_model_files_peak_potential')

MODEL_ID = "peak_potential_v2_15_16"
MAX_AGE_FOR_PREDICTION = 35

def generate_predictions(model_id: str, target_season: Optional[str] = None, num_players_to_display: int = 30):
    """
    Funció principal que carrega models i genera prediccions.
    - Si target_season és un string (ex: "2015_2016"), prediu només per a aquesta temporada.
    - Si target_season és None, prediu per a totes les temporades.
    """
    
    if target_season:
        logging.info(f"\n{'#'*60}\n# INICIANT PREDICCIONS PER A LA TEMPORADA ESPECÍFICA: {target_season}\n{'#'*60}")
        output_filename = f"predictions_season_{target_season}.csv"
    else:
        logging.info(f"\n{'#'*60}\n# INICIANT PREDICCIONS PER A TOTES LES TEMPORADES \n{'#'*60}")
        output_filename = "predictions_all_seasons_v15_16_double_new.csv"

    try:
        with open(os.path.join(_DATA_DIR, 'player_index.json'), 'r', encoding='utf-8') as f:
            player_index = json.load(f)
        minutes_df = pd.read_csv(os.path.join(_DATA_DIR, 'player_season_minutes_with_names.csv'))
        minutes_df['season_name_std'] = minutes_df['season_name'].str.replace('/', '_', regex=False)
        minutes_df_dict = {(str(row['player_id']), row['season_name_std']): row['total_minutes_played'] for _, row in minutes_df.iterrows()}
    except FileNotFoundError as e:
        logging.error(f"Error carregant fitxers de dades essencials: {e}")
        return

    all_predictions = []
    positions = ["Attacker", "Midfielder", "Defender"]

    for position in positions:
        logging.info(f"\n{'='*20} Processant posició: {position} {'='*20}")
        
        model_dir = os.path.join(_MODELS_DIR, model_id, position.lower())
        config_path = os.path.join(model_dir, f'model_config_{position.lower()}_{model_id}.json')

        try:
            model = joblib.load(os.path.join(model_dir, f'potential_model_{position.lower()}_{model_id}.joblib'))
            scaler = joblib.load(os.path.join(model_dir, f'feature_scaler_{position.lower()}_{model_id}.joblib'))
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            features_for_model = config['features_used_for_ml_model']
            eval_metrics = config.get('evaluation_metrics_on_test_set', {})
            
            logging.info(f"Model per a '{position}' carregat correctament.")
            if eval_metrics:
                r2 = eval_metrics.get('R2', 'N/A')
                rmse = eval_metrics.get('RMSE', None)
                print("\n--- Mètriques d'Avaluació del Model (calculades durant l'entrenament, SÓN FIXES) ---")
                print(f"  R²: {r2}")
                if rmse is not None:
                    mse = rmse ** 2
                    print(f"  MSE (Mean Squared Error): {mse:.3f}")
                    print(f"  RMSE (Root Mean Squared Error): {rmse:.3f}")
                print("----------------------------------------------------------------------------------\n")
            else:
                logging.warning("No s'han trobat mètriques d'avaluació al fitxer de configuració del model.")

        except FileNotFoundError:
            logging.warning(f"No s'han trobat els fitxers del model per a la posició '{position}'. Saltant...")
            continue

        candidate_instances = []
        player_items = player_index.items() if isinstance(player_index, dict) else [(p.get("name", ""), p) for p in player_index]

        for player_name_key, p_info in player_items:
            general_pos = get_general_position(p_info.get("position"))
            if general_pos != position:
                continue

            seasons_to_check = [target_season] if target_season else p_info.get("seasons", [])
            
            for season in seasons_to_check:
                if season not in p_info.get("seasons", []): continue

                age = get_age_at_fixed_point_in_season(p_info.get("dob"), season)
                if age is not None and age <= MAX_AGE_FOR_PREDICTION:
                    candidate_instances.append({
                        "id": str(p_info["player_id"]),
                        "name": p_info.get("name", player_name_key),
                        "dob": p_info.get("dob"),
                        "age_in_season": age,
                        "position": position,
                        "season_for_prediction": season,
                        "all_seasons_history": sorted(p_info["seasons"])
                    })
        
        if not candidate_instances:
            logging.info(f"No s'han trobat instàncies candidates (jugador-temporada) per a '{position}'.")
            continue
            
        logging.info(f"Trobades {len(candidate_instances)} instàncies candidates per a '{position}'. Generant features...")

        for i, candidate in enumerate(candidate_instances):
            if (i + 1) % 100 == 0:
                logging.info(f"  Processant instància {i+1}/{len(candidate_instances)}...")
            
            player_id = candidate['id']
            season_to_predict_on = candidate['season_for_prediction']
            
            season_numeric_current = int(season_to_predict_on.split('_')[0])
            minutes_current = minutes_df_dict.get((player_id, season_to_predict_on), 0.0)
            num_90s_current = safe_division(minutes_current, 90.0)
            event_file_path_current = os.path.join(_DATA_DIR, season_to_predict_on, "players", f"{player_id}_{season_to_predict_on}.csv")
            try:
                events_df_current = pd.read_csv(event_file_path_current, low_memory=False)
            except FileNotFoundError:
                events_df_current = pd.DataFrame()
            base_features_current = extract_season_features(events_df_current, candidate['age_in_season'], season_numeric_current, num_90s_current)
            base_features_current['general_position_identifier'] = candidate['position']
            
            historical_seasons = [s for s in candidate['all_seasons_history'] if s < season_to_predict_on]
            historical_features_list = []
            if historical_seasons:
                for hist_season in historical_seasons:
                    age_hist = get_age_at_fixed_point_in_season(candidate['dob'], hist_season)
                    if age_hist is None: continue
                    season_numeric_hist = int(hist_season.split('_')[0])
                    minutes_hist = minutes_df_dict.get((player_id, hist_season), 0.0)
                    num_90s_hist = safe_division(minutes_hist, 90.0)
                    event_file_path_hist = os.path.join(_DATA_DIR, hist_season, "players", f"{player_id}_{hist_season}.csv")
                    try: events_df_hist = pd.read_csv(event_file_path_hist, low_memory=False)
                    except FileNotFoundError: events_df_hist = pd.DataFrame()
                    base_features_hist = extract_season_features(events_df_hist, age_hist, season_numeric_hist, num_90s_hist)
                    historical_features_list.append(base_features_hist)
            historical_df = pd.DataFrame(historical_features_list) if historical_features_list else pd.DataFrame()
            
            instance_ml_features = trainer_construct_ml_features_for_player_season(
                current_season_base_features_row=base_features_current,
                historical_base_features_df=historical_df,
                all_base_metric_names=base_features_current.index.tolist()
            )
            
            X = pd.DataFrame([instance_ml_features]).fillna(0.0)
            X = X[features_for_model]
            X_scaled = scaler.transform(X)
            
            prediction = model.predict(X_scaled)[0]
            prediction_clipped = np.clip(prediction, 0, 200)

            candidate['predicted_potential'] = prediction_clipped
            all_predictions.append(candidate)

    if not all_predictions:
        logging.error("No s'ha pogut realitzar cap predicció.")
        return

    final_df = pd.DataFrame(all_predictions)
    final_df.drop(columns=['all_seasons_history', 'dob'], inplace=True, errors='ignore')
    final_df_sorted = final_df.sort_values(by='predicted_potential', ascending=False).reset_index(drop=True)

    try:
        final_df_sorted.to_csv(output_filename, index=False, encoding='utf-8-sig')
        logging.info(f"\nResultats complets desats a '{output_filename}'")
    except Exception as e:
        logging.error(f"No s'ha pogut desar el fitxer CSV '{output_filename}': {e}")

    logging.info(f"\n{'='*25} RESUM DELS RESULTATS {'='*25}")
    print(f"Top {num_players_to_display} prediccions (de {len(final_df_sorted)} totals):\n")
    
    output_df = final_df_sorted.head(num_players_to_display)
    output_df['predicted_potential'] = output_df['predicted_potential'].round(2)
    output_df.index = output_df.index + 1
    
    print(output_df.to_string())

if __name__ == "__main__":
    generate_predictions(
        model_id=MODEL_ID,
        target_season="2015_2016"
    )

    generate_predictions(
        model_id=MODEL_ID,
        target_season=None 
    )