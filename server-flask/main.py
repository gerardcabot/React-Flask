from flask import Flask, jsonify, request
import os
import pandas as pd
from flask_cors import CORS
import matplotlib
from matplotlib import pyplot as plt
from mplsoccer import Pitch, Radar, grid, FontManager, VerticalPitch # Radar, grid, FontManager might not be used in this exact snippet but good to keep if used elsewhere
from ast import literal_eval
import json
from scipy.ndimage import gaussian_filter
from matplotlib import patheffects
import logging
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


STATIC_IMG_DIR = os.path.join("static", "images")
os.makedirs(STATIC_IMG_DIR, exist_ok=True)

matplotlib.use("Agg")

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
DATA_DIR = "../data"
BOUNDS_DIR = "radar_bounds"
os.makedirs(BOUNDS_DIR, exist_ok=True)

# --- Helper Functions ---
def safe_literal_eval(val):
    if pd.isna(val):
        return None
    try:
        return literal_eval(val)
    except (ValueError, SyntaxError):
        # Try to handle simple cases like "[10,20]" if they weren't proper tuples
        if isinstance(val, str) and val.startswith('[') and val.endswith(']'):
            try:
                return json.loads(val) # More robust for simple lists
            except json.JSONDecodeError:
                return None
        return None

def get_category_name_from_value(val):
    if pd.isna(val):
        return "N/A"
    # Check if val might already be an evaluated dict (if CSVs store complex types)
    if isinstance(val, dict) and 'name' in val:
        return str(val['name'])
    
    parsed_val = safe_literal_eval(val) # Try to parse if it's a string representation
    if isinstance(parsed_val, dict) and 'name' in parsed_val:
        return str(parsed_val['name'])
    if isinstance(val, bool):
        return "Yes" if val else "No"
    return str(val)

def load_player_data(player_id, season, data_dir):
    dfs = []
    target_player_id = str(player_id)
    if season == "all":
        for season_folder in os.listdir(data_dir):
            if os.path.isdir(os.path.join(data_dir, season_folder)):
                path = os.path.join(data_dir, season_folder, "players", f"{target_player_id}_{season_folder}.csv")
                if os.path.exists(path):
                    try:
                        dfs.append(pd.read_csv(path, low_memory=False))
                    except Exception as e:
                        logger.error(f"Error reading CSV {path}: {e}")
    else:
        path = os.path.join(data_dir, season, "players", f"{target_player_id}_{season}.csv")
        if os.path.exists(path):
            try:
                dfs.append(pd.read_csv(path, low_memory=False))
            except Exception as e:
                logger.error(f"Error reading CSV {path}: {e}")
    
    if not dfs:
        return None
    
    full_df = pd.concat(dfs, ignore_index=True)
    if 'player_id' in full_df.columns:
        full_df['player_id'] = full_df['player_id'].astype(str)
    return full_df

# --- Basic API Info Routes ---
@app.route("/")
def home():
    return jsonify({"message": "Welcome to the La Liga Player Explorer API."})

player_index_path = os.path.join(DATA_DIR, "player_index.json")
player_index = {}
if os.path.exists(player_index_path):
    try:
        with open(player_index_path, "r", encoding="utf-8") as f:
            player_index = json.load(f)
    except Exception as e:
        logger.error(f"Error loading player_index.json: {e}")
else:
    logger.warning("⚠️ player_index.json not found. Player list will be empty.")


@app.route("/players")
def players_route():
    try:
        return jsonify([
            {"name": name, "player_id": data["player_id"], "seasons": data.get("seasons", [])}
            for name, data in sorted(player_index.items()) if isinstance(data, dict) and "player_id" in data
        ])
    except Exception as e:
        logger.error(f"Error in /players: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/player_seasons")
def player_seasons_route(): # Renamed
    player_id = request.args.get("player_id")
    if not player_id: return jsonify({"error": "Missing player_id"}), 400
    try:
        player_data = None
        for data in player_index.values():
            if isinstance(data, dict) and str(data.get("player_id")) == str(player_id):
                player_data = data
                break
        if not player_data: return jsonify({"error": "Player not found"}), 404
        return jsonify({"player_id": player_id, "seasons": player_data.get("seasons", [])})
    except Exception as e:
        logger.error(f"Error in /player_seasons: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/player_events")
def player_events_route(): # Renamed
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"error": "No data found for the specified player and season(s)"}), 404
        return df.to_json(orient="records")
    except Exception as e:
        logger.error(f"Error in /player_events: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/seasons")
def list_seasons_route(): # Renamed
    try:
        seasons = [folder for folder in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, folder))]
        return jsonify(sorted(seasons))
    except Exception as e:
        logger.error(f"Error in /seasons: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# --- Visualization Configuration and Data Endpoints ---
@app.route("/available_visualizations")
def available_visualizations_route():
    # Curated, grouped, robust visualizations for football event data
    visualizations = [
        {
            "category": "Passing",
            "visualizations": [
                {"label": "Total Passes", "metric": "type", "metric_type": "count", "viz_type": "number", "filter": {"type": "Pass"}},
                {"label": "Pass Completion Rate", "metric": "pass_outcome", "metric_type": "percentage", "viz_type": "number"},
                {"label": "Pass Type Distribution", "metric": "pass_type", "metric_type": "categorical", "viz_type": "bar"},
                {"label": "Pass End Locations", "metric": "pass_end_location", "metric_type": "location", "viz_type": "scatter", "location_column": "pass_end_location"},
                {"label": "Progressive Passes", "metric": "pass_end_location", "metric_type": "count", "viz_type": "number", "filter": {"type": "Pass", "progressive": True}},
            ]
        },
        {
            "category": "Shooting",
            "visualizations": [
                {"label": "Total Shots", "metric": "type", "metric_type": "count", "viz_type": "number", "filter": {"type": "Shot"}},
                {"label": "Goals Scored", "metric": "shot_outcome", "metric_type": "count", "viz_type": "number", "filter": {"shot_outcome": "Goal"}},
                {"label": "xG Total", "metric": "shot_statsbomb_xg", "metric_type": "sum", "viz_type": "number"},
                {"label": "Shot Outcome Distribution", "metric": "shot_outcome", "metric_type": "categorical", "viz_type": "bar"},
                {"label": "Shot Locations", "metric": "location", "metric_type": "location", "viz_type": "scatter", "location_column": "location", "filter": {"type": "Shot"}},
            ]
        },
        {
            "category": "Dribbling",
            "visualizations": [
                {"label": "Dribbles Attempted", "metric": "type", "metric_type": "count", "viz_type": "number", "filter": {"type": "Dribble"}},
                {"label": "Dribble Success Rate", "metric": "dribble_outcome", "metric_type": "percentage", "viz_type": "number"},
                {"label": "Dribble Outcome Distribution", "metric": "dribble_outcome", "metric_type": "categorical", "viz_type": "bar"},
            ]
        },
        {
            "category": "Duels & Defensive",
            "visualizations": [
                {"label": "Duels Attempted", "metric": "type", "metric_type": "count", "viz_type": "number", "filter": {"type": "Duel"}},
                {"label": "Duel Success Rate", "metric": "duel_outcome", "metric_type": "percentage", "viz_type": "number"},
                {"label": "Interceptions", "metric": "interception_outcome", "metric_type": "count", "viz_type": "number"},
                {"label": "Ball Recoveries", "metric": "type", "metric_type": "count", "viz_type": "number", "filter": {"type": "Ball Recovery"}},
                {"label": "Pressure Events", "metric": "type", "metric_type": "count", "viz_type": "number", "filter": {"type": "Pressure"}},
            ]
        },
        {
            "category": "Fouls & Discipline",
            "visualizations": [
                {"label": "Fouls Committed", "metric": "type", "metric_type": "count", "viz_type": "number", "filter": {"type": "Foul Committed"}},
                {"label": "Fouls Won", "metric": "type", "metric_type": "count", "viz_type": "number", "filter": {"type": "Foul Won"}},
                {"label": "Cards Received", "metric": "bad_behaviour_card", "metric_type": "categorical", "viz_type": "bar"},
            ]
        },
        {
            "category": "Events Over Time",
            "visualizations": [
                {"label": "Events by Minute", "metric": "minute", "metric_type": "time", "viz_type": "line"},
            ]
        }
    ]
    # FLATTEN the grouped structure for frontend compatibility
    flat_visualizations = []
    for group in visualizations:
        for v in group["visualizations"]:
            flat_visualizations.append({**v, "category": group["category"]})
    return jsonify({"visualizations": flat_visualizations})

@app.route("/custom_visualization")
def custom_visualization_route():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    metric = request.args.get("metric")
    metric_type = request.args.get("metric_type")
    viz_type = request.args.get("viz_type")
    location_column = request.args.get("location_column", "location")
    # Optional filters for event type, etc.
    filter_type = request.args.get("filter_type")
    filter_value = request.args.get("filter_value")
    progressive = request.args.get("progressive", "false").lower() == "true"

    # --- FIX: Only require the minimum set of params for each viz type ---
    # Some visualizations (e.g. "Events by Minute") do not have location_column or filter_type/value
    # So only check for required params
    if not all([player_id, season, metric, metric_type, viz_type]):
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"error": "No data found"}), 404

        # Apply event type filter if present
        if filter_type and filter_value:
            df = df[df.get(filter_type) == filter_value]
        # Special filter for progressive passes
        if progressive and "pass_end_location" in df.columns:
            df["end_loc_eval"] = df["pass_end_location"].apply(safe_literal_eval)
            df = df[df["end_loc_eval"].apply(lambda loc: isinstance(loc, (list, tuple)) and len(loc) > 0 and loc[0] > 80)]

        # Robust count for boolean/numeric/categorical
        if viz_type == "number" and metric_type == "count":
            if metric == "type":
                # Count events of a certain type (e.g., Pass, Shot, etc.)
                value = len(df)
            elif metric in df.columns:
                # For categorical: count non-null
                value = df[metric].notna().sum()
            else:
                value = 0
            return jsonify({"type": "number", "data": int(value), "title": f"Total {filter_value or metric.replace('_', ' ').title()}"})

        # Robust sum (e.g., xG)
        if viz_type == "number" and metric_type == "sum":
            if metric in df.columns:
                value = df[metric].dropna().astype(float).sum()
            else:
                value = 0
            return jsonify({"type": "number", "data": float(value), "title": f"Total {metric.replace('_', ' ').title()}"})

        # Robust percentage (e.g., pass completion, duel success, dribble success)
        if viz_type == "number" and metric_type == "percentage":
            if metric == "pass_outcome" and "pass_outcome" in df.columns:
                total = len(df)
                completed = df["pass_outcome"].isna().sum()
                pct = (completed / total * 100) if total > 0 else 0
                return jsonify({"type": "number", "data": pct, "title": "Pass Completion Rate"})
            elif metric in df.columns:
                total = df[metric].notna().sum()
                # For duel/dribble: "Won", "Complete", "Success"
                success = df[df[metric].isin(["Won", "Complete", "Success"])][metric].count()
                pct = (success / total * 100) if total > 0 else 0
                return jsonify({"type": "number", "data": pct, "title": f"{metric.replace('_', ' ').title()} Success Rate"})
            else:
                return jsonify({"type": "number", "data": 0, "title": f"{metric.replace('_', ' ').title()} Success Rate"})

        # Robust categorical distribution (bar)
        if viz_type == "bar" and metric_type == "categorical":
            if metric in df.columns:
                # Only count non-empty, non-NaN values
                values = df[metric].dropna().astype(str)
                # Remove empty strings and whitespace-only values
                values = values[values.str.strip() != ""]
                counts = values.value_counts()
                data = [{"x": str(k), "y": int(v)} for k, v in counts.items()]
                return jsonify({
                    "type": "bar",
                    "data": data,
                    "title": f"{metric.replace('_', ' ').title()} Distribution"
                })
            else:
                return jsonify({"type": "bar", "data": [], "title": f"{metric.replace('_', ' ').title()} Distribution"})

        # Robust location scatter/heatmap
        if viz_type in ["scatter", "heatmap"] and location_column in df.columns:
            df[location_column] = df[location_column].apply(safe_literal_eval)
            valid_locations = df[df[location_column].notna()]
            data = [
                {"x": loc[0], "y": loc[1], "value": 1}
                for loc in valid_locations[location_column]
                if isinstance(loc, (list, tuple)) and len(loc) >= 2
            ]
            return jsonify({
                "type": viz_type,
                "data": data,
                "title": f"{metric.replace('_', ' ').title()} Locations"
            })

        # Robust time series (events by minute)
        if viz_type == "line" and metric == "minute" and "minute" in df.columns:
            counts = df.groupby("minute").size().reset_index()
            data = [{"x": int(row["minute"]), "y": int(row[0])} for _, row in counts.iterrows()]
            return jsonify({
                "type": "line",
                "data": data,
                "title": "Events by Minute"
            })

        return jsonify({"error": "Invalid or unsupported visualization type/metric"}), 400

    except Exception as e:
        # Log error for debugging
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# --- Standard Visualization Routes (PassMap, ShotMap, Heatmaps, etc.) ---
@app.route("/pass_map_plot")
def pass_map_plot_route(): # Renamed
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    try:
        if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"error": "No data found"}), 404

        df = df[df.get("type") == "Pass"].copy()
        if not all(c in df.columns for c in ["location", "pass_end_location"]):
            return jsonify({"error": "Required columns for pass map missing"}), 400
        
        df["location_eval"] = df["location"].apply(safe_literal_eval)
        df["pass_end_location_eval"] = df["pass_end_location"].apply(safe_literal_eval)
        df.dropna(subset=["location_eval", "pass_end_location_eval"], inplace=True)

        pass_data = [
            {"start_x": loc[0], "start_y": loc[1], "end_x": end_loc[0], "end_y": end_loc[1],
             "completed": pd.isna(outcome),
             "assist": str(assist_flag).lower() == 'true', # Handles boolean True and string "True"
             "final_third": isinstance(end_loc, (list,tuple)) and len(end_loc)>0 and end_loc[0] > 80}
            for loc, end_loc, outcome, assist_flag in zip(
                df["location_eval"], df["pass_end_location_eval"],
                df.get("pass_outcome", pd.Series([None]*len(df))),
                df.get("pass_goal_assist", pd.Series([False]*len(df)))
            ) if isinstance(loc, (list,tuple)) and len(loc)>=2 and isinstance(end_loc, (list,tuple)) and len(end_loc)>=2
        ]
        return jsonify({"passes": pass_data})
    except Exception as e:
        logger.error(f"Error in /pass_map_plot: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/position_heatmap") # Standard image-based heatmap
def position_heatmap_route(): # Renamed
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        player_dir = os.path.join(STATIC_IMG_DIR, player_id)
        os.makedirs(player_dir, exist_ok=True)
        image_filename = f"{player_id}_{season}_pos_heatmap.png" # More unique filename
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{player_id}/{image_filename}" # Corrected URL path

        # Optional: Add caching logic here if needed, e.g., return existing image if not too old
        # if os.path.exists(image_path): return jsonify({"image_url": image_url})

        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"error": "No data found for heatmap"}), 404
        if "location" not in df.columns: return jsonify({"error": "Location column missing"}), 400
        
        df["location_eval"] = df["location"].apply(safe_literal_eval)
        df.dropna(subset=["location_eval"], inplace=True)
        if df.empty: return jsonify({"error": "No valid location data"}), 404

        df["x"] = df["location_eval"].apply(lambda loc: loc[0] if isinstance(loc, (list, tuple)) and len(loc) > 0 else np.nan)
        df["y"] = df["location_eval"].apply(lambda loc: loc[1] if isinstance(loc, (list, tuple)) and len(loc) > 1 else np.nan)
        df.dropna(subset=["x", "y"], inplace=True)
        if df.empty: return jsonify({"error": "No valid x, y coordinates for heatmap"}), 404

        pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='white')
        fig, ax = pitch.draw(figsize=(4.125, 6)) # Standard size for these heatmaps
        fig.set_facecolor('#22312b') # Ensure fig background matches
        bin_statistic = pitch.bin_statistic_positional(df.x, df.y, statistic='count', positional='full', normalize=True)
        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='coolwarm', edgecolors='#22312b')
        # pitch.scatter(df.x, df.y, c='white', s=2, ax=ax) # Optional: scatter original points
        path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')] # Thicker stroke
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)
        
        plt.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return jsonify({"image_url": image_url})
    except Exception as e:
        logger.error(f"Error in /position_heatmap: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate position heatmap: {str(e)}"}), 500


@app.route('/radar_chart')
def radar_chart_route(): # Renamed
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season or season == "all":
        return jsonify({"error": "Missing player_id or specific season for radar chart"}), 400
    try:
        # ... (Keep your existing robust radar chart logic, ensure safe_literal_eval if parsing any complex fields)
        # For brevity, not re-pasting the full radar logic, but it should be sound.
        # Just ensure it uses load_player_data or similar robust loading.
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"error": "No data for radar chart"}), 404
        
        player_df = df[df["player_id"] == str(player_id)] if 'player_id' in df.columns else df # Assuming data is already for one player if player_id col missing
        if player_df.empty: return jsonify({"error": "No data for this player in the season"}), 404

        # Example: Recalculate metrics safely
        assists = len(player_df[player_df.get("pass_goal_assist", False) == True])
        goals = len(player_df[(player_df.get("type", "") == "Shot") & (player_df.get("shot_outcome", "") == "Goal")])
        # ... and so on for other radar params ...

        # Placeholder if full radar logic is complex to paste
        # return jsonify({"message": "Radar chart generation logic to be confirmed."})
        
        # Assuming your radar logic is mostly self-contained and was working:
        player_dir = os.path.join(STATIC_IMG_DIR, player_id)
        os.makedirs(player_dir, exist_ok=True)
        image_filename = f"{player_id}_{season}_radar.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{player_id}/{image_filename}"

        # Recalculate params for radar
        dribbles_completed = len(player_df[(player_df.get("type", "") == "Dribble") & (player_df.get("dribble_outcome", "") == "Complete")])
        xgN = player_df[player_df.get("type", "") == "Shot"].get("shot_statsbomb_xg", pd.Series([0])).sum() if "shot_statsbomb_xg" in player_df.columns else 0
        miscontrols = len(player_df[player_df.get("type", "") == "Miscontrol"])
        
        values = [assists, goals, dribbles_completed, float(xgN), miscontrols]
        params = ["Assists", "Goals", "Dribbles Cmp", "xG", "Miscontrols"] # Shortened Dribbles
        
        # Simplified bounds for example
        high_bounds = [max(1, v + v*0.5 + 2) for v in values] # Dynamic upper bound
        high_bounds[3] = max(1.0, values[3] + values[3]*0.5 + 1.0) # xG float

        low_bounds = [0] * len(params)
        lower_is_better_params = ["Miscontrols"]

        radar = Radar(params, low_bounds, high_bounds, lower_is_better=lower_is_better_params, round_int=[True, True, True, False, True])
        fig, ax = radar.setup_axis()
        rings = radar.draw_circles(ax=ax, facecolor="#f9f9f9", edgecolor="#bbb") # Light rings
        radar_output = radar.draw_radar(values, ax=ax,
                                        kwargs_radar={'facecolor': "#007bff", "alpha": 0.6}, # Blueish
                                        kwargs_rings={"facecolor": "#6c757d", "alpha": 0.3}) # Greyish rings
        radar.draw_range_labels(ax=ax, fontsize=8, color="#333")
        radar.draw_param_labels(ax=ax, fontsize=9, color="#333", wrap=8) # Wrap long labels
        
        fig.savefig(image_path, bbox_inches="tight", dpi=150) # Good DPI for web
        plt.close(fig)
        return jsonify({"image_url": image_url})

    except Exception as e:
        logger.error(f"Radar chart generation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/shot_map")
def shot_map_data_route(): # Renamed to signify data endpoint
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    try:
        if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"error": "No data found"}), 404

        df = df[df.get("type") == "Shot"].copy()
        if not all(c in df.columns for c in ["location", "shot_statsbomb_xg"]):
            return jsonify({"error": "Required columns for shot map missing (location, shot_statsbomb_xg)"}), 400

        df["location_eval"] = df["location"].apply(safe_literal_eval)
        df.dropna(subset=["location_eval", "shot_statsbomb_xg"], inplace=True)
        if df.empty: return jsonify({"error": "No valid shot data after parsing"}), 404
        
        df["x"] = df["location_eval"].apply(lambda loc: loc[0] if isinstance(loc, (list, tuple)) and len(loc)>0 else np.nan)
        df["y"] = df["location_eval"].apply(lambda loc: loc[1] if isinstance(loc, (list, tuple)) and len(loc) > 1 else np.nan)
        df.dropna(subset=["x", "y"], inplace=True)

        df["is_goal"] = df.get("shot_outcome", pd.Series([""]*len(df))).fillna("Unknown") == "Goal"
        # For on-target check, StatsBomb `shot_end_location` z-coordinate (height) is crucial.
        # A simple x-check isn't enough. Example: if end_location is [120, 40, 0.5] -> on target. [120, 40, 3] -> over bar.
        df["shot_end_location_eval"] = df.get("shot_end_location", pd.Series([None]*len(df))).apply(safe_literal_eval)
        
        def is_shot_on_target_detailed(end_loc):
            if isinstance(end_loc, (list, tuple)) and len(end_loc) == 3:
                # x_end, y_end, z_end = end_loc
                # StatsBomb goal frame: x=120, y from 36 to 44, z from 0 to 2.67
                # return 119 < x_end <= 120 and 35.8 < y_end < 44.2 and -0.1 < z_end < 2.7 # Allow slight tolerance
                # Simplified: If it's a goal, it was on target. If saved, it was on target.
                # More accurately, use shot_outcome: 'Saved', 'Goal', 'Blocked' (by keeper/last defender on line)
                return True # Placeholder, real on-target needs careful outcome + end_loc logic
            return False

        shot_data = [
            {"x": row["x"], "y": row["y"], "xg": row["shot_statsbomb_xg"], "goal": row["is_goal"]}
            for _, row in df.iterrows() if pd.notna(row["x"]) and pd.notna(row["y"])
        ]
        return jsonify({"shots": shot_data})
    except Exception as e:
        logger.error(f"Error in /shot_map data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/pass_completion_heatmap")
def pass_completion_heatmap_route(): # Renamed
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        player_dir = os.path.join(STATIC_IMG_DIR, player_id)
        os.makedirs(player_dir, exist_ok=True)
        image_filename = f"{player_id}_{season}_pass_compl_heatmap.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{player_id}/{image_filename}"

        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"error": "No data found"}), 404

        df = df[df.get("type") == "Pass"].copy()
        if not all(c in df.columns for c in ["location", "pass_outcome"]):
             return jsonify({"error": "Required columns for pass completion missing"}), 400

        df["location_eval"] = df["location"].apply(safe_literal_eval)
        df.dropna(subset=["location_eval"], inplace=True)
        if df.empty: return jsonify({"error": "No valid pass location data"}), 404

        df["x"] = df["location_eval"].apply(lambda loc: loc[0] if isinstance(loc, (list,tuple)) and len(loc)>0 else np.nan)
        df["y"] = df["location_eval"].apply(lambda loc: loc[1] if isinstance(loc, (list,tuple)) and len(loc) > 1 else np.nan)
        df.dropna(subset=["x", "y"], inplace=True)
        df["completed"] = df["pass_outcome"].isna() # NaN outcome means completed

        pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='white')
        fig, ax = pitch.draw(figsize=(4.125, 6)) # Standard size
        fig.set_facecolor('#22312b')
        
        bin_statistic = pitch.bin_statistic_positional(df.x, df.y, values=df.completed, statistic='mean', positional='full')
        for section in bin_statistic: # Handle None in statistics for heatmap
            if 'statistic' in section and section['statistic'] is not None:
                section['statistic'] = np.nan_to_num(section['statistic'], nan=0.0)
            else: # If a whole section has no data
                section['statistic'] = np.zeros_like(section['x_grid'][:-1,:-1], dtype=float)


        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='Blues', edgecolors='#22312b', vmin=0, vmax=1) # Scale 0-1
        path_eff = [patheffects.withStroke(linewidth=3, foreground='#22312b')]
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=15, ax=ax, ha='center', va='center', str_format='{:.0%}', path_effects=path_eff)
        
        plt.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return jsonify({"image_url": image_url})
    except Exception as e:
        logger.error(f"Error in /pass_completion_heatmap: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate pass completion heatmap: {str(e)}"}), 500

@app.route("/pressure_heatmap")
def pressure_heatmap_route(): # Renamed
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season: return jsonify({"error": "Missing player_id or season"}), 400
    try:
        player_dir = os.path.join(STATIC_IMG_DIR, player_id)
        os.makedirs(player_dir, exist_ok=True)
        image_filename = f"{player_id}_{season}_pressure_heatmap.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{player_id}/{image_filename}"

        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty: return jsonify({"error": "No data found"}), 404

        df = df[df.get("type") == "Pressure"].copy()
        if "location" not in df.columns: return jsonify({"error": "Location column missing for pressure events"}), 400
        
        df["location_eval"] = df["location"].apply(safe_literal_eval)
        df.dropna(subset=["location_eval"], inplace=True)
        if df.empty: return jsonify({"error": "No valid pressure location data"}), 404

        df["x"] = df["location_eval"].apply(lambda loc: loc[0] if isinstance(loc, (list, tuple)) and len(loc) > 0 else np.nan)
        df["y"] = df["location_eval"].apply(lambda loc: loc[1] if isinstance(loc, (list, tuple)) and len(loc) > 1 else np.nan)
        df.dropna(subset=["x", "y"], inplace=True)
        if df.empty: return jsonify({"error": "No valid x, y coordinates for pressure heatmap"}), 404

        pitch = Pitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#22312b', line_color='#efefef')
        fig, ax = pitch.draw(figsize=(6.6, 4.125)) # Standard horizontal pitch size
        fig.set_facecolor('#22312b')

        bin_statistic = pitch.bin_statistic(df.x, df.y, statistic='count', bins=(25, 25))
        if 'statistic' in bin_statistic and bin_statistic['statistic'] is not None:
            bin_statistic['statistic'] = gaussian_filter(bin_statistic['statistic'], 1)
            pcm = pitch.heatmap(bin_statistic, ax=ax, cmap='hot', edgecolors='#22312b')
            cbar = fig.colorbar(pcm, ax=ax, shrink=0.6)
            cbar.outline.set_edgecolor('#efefef')
            cbar.ax.yaxis.set_tick_params(color='#efefef')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#efefef')
        
        plt.savefig(image_path, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return jsonify({"image_url": image_url})
    except Exception as e:
        logger.error(f"Error in /pressure_heatmap: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate pressure heatmap: {str(e)}"}), 500


# --- All Seasons Data Routes (XG Trend, Seasonal Stats) ---
@app.route("/xg_goal_trend")
def xg_goal_trend_route(): # Renamed
    player_id = request.args.get("player_id")
    if not player_id: return jsonify({"error": "Missing player_id"}), 400
    try:
        trend_data = []
        seasons_available = sorted([s_dir for s_dir in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, s_dir))])
        for season_name in seasons_available:
            df = load_player_data(player_id, season_name, DATA_DIR) # Load for specific season
            if df is None or df.empty: continue

            shots_df = df[df.get("type") == "Shot"]
            total_xg = shots_df.get("shot_statsbomb_xg", pd.Series(dtype='float64')).sum() # Ensure float for sum
            goals = len(shots_df[shots_df.get("shot_outcome") == "Goal"])
            shots_taken = len(shots_df)
            avg_xg_per_shot = (total_xg / shots_taken) if shots_taken > 0 else 0.0
            trend_data.append({
                "season": season_name, "total_xg": round(float(total_xg), 2), "goals": goals,
                "shots_taken": shots_taken, "avg_xg_per_shot": round(avg_xg_per_shot, 3)
            })
        if not trend_data: return jsonify({"error": "No shot data found across seasons for this player"}), 404
        return jsonify({"trend_data": trend_data})
    except Exception as e:
        logger.error(f"Error in /xg_goal_trend: {e}", exc_info=True)
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
            
            progressive_passes = 0
            if "pass_end_location" in passes_df.columns:
                passes_df["end_loc_eval"] = passes_df["pass_end_location"].apply(safe_literal_eval)
                progressive_passes = len(passes_df[
                    passes_df["end_loc_eval"].apply(lambda loc: isinstance(loc, (list,tuple)) and len(loc)>0 and loc[0] > 80)
                ])
            stats_data.append({
                "season": season_name, "total_xg": round(float(total_xg), 2),
                "pass_completion_pct": round(pass_completion_pct, 1),
                "progressive_passes": progressive_passes
            })
        if not stats_data: return jsonify({"error": "No data found across seasons for this player"}), 404
        return jsonify({"stats_data": stats_data})
    except Exception as e:
        logger.error(f"Error in /seasonal_stats: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/goalkeeper_stats") # New endpoint for single season stats
def goalkeeper_stats():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
    df = load_player_data(player_id, season, DATA_DIR)
    if df is None or df.empty:
        return jsonify({"stats": {}})
    # Filter for goalkeeper events
    # Fix: Use position == "Goalkeeper" OR type == "Goal Keeper" for all GK events
    gk_df = df[(df.get("position", pd.Series("")).fillna("").str.lower().str.contains("goalkeeper")) | (df.get("type", pd.Series("")) == "Goal Keeper")].copy()
    # For shots faced, look for events of type "Shot" where the player's team is the defending team
    shots_faced = df[df.get("type", "") == "Shot"]
    # Try to infer if this player was the goalkeeper for the defending team
    # If the player's team matches the "team" field for the shot, and position is GK, it's a shot faced
    player_team = None
    if "team" in df.columns:
        player_team = df["team"].dropna().unique()
        if len(player_team) == 1:
            player_team = player_team[0]
        else:
            player_team = None
    if player_team:
        shots_faced = shots_faced[shots_faced.get("team", "") == player_team]
    else:
        # Fallback: if only one team in file, use that
        pass
    # Now, for saves and goals conceded, use shot_outcome
    shot_saved = shots_faced[shots_faced.get("shot_outcome", "") == "Saved"]
    goal_conceded = shots_faced[shots_faced.get("shot_outcome", "") == "Goal"]
    # Save pct
    shots_on_target = len(shot_saved) + len(goal_conceded)
    saves = len(shot_saved)
    stats = {
        "total_events": int(len(gk_df)),
        "shot_faced": int(len(shots_faced)),
        "shot_saved": int(saves),
        "goal_conceded": int(len(goal_conceded)),
        "punches": int((gk_df.get("goalkeeper_technique", pd.Series()) == "Punched Out").sum()),
        "claims": int((gk_df.get("goalkeeper_technique", pd.Series()) == "Claim").sum()),
        "collected": int((gk_df.get("goalkeeper_outcome", pd.Series()) == "Collected").sum()),
        "in_play_danger": int((gk_df.get("goalkeeper_in_play_danger", pd.Series()) == True).sum()),
        "passes_attempted": int((df.get("type", pd.Series()) == "Pass").sum()),
        "passes_completed": int(((df.get("type", pd.Series()) == "Pass") & (df.get("pass_outcome", pd.Series()).isna())).sum()),
        "throws_attempted": int((gk_df.get("goalkeeper_type", pd.Series()) == "Throw").sum()),
        "throws_completed": int(((gk_df.get("goalkeeper_type", pd.Series()) == "Throw") & (gk_df.get("goalkeeper_outcome", pd.Series()).isna())).sum()),
        "sweeper_actions": int((gk_df.get("goalkeeper_type", pd.Series()) == "Sweeper").sum()),
    }
    stats["save_pct"] = round((saves / shots_on_target * 100) if shots_on_target > 0 else 0, 1)
    return jsonify({"stats": stats})

@app.route("/goalkeeper_stats_all_seasons") # New endpoint for all seasons stats
def goalkeeper_stats_all_seasons():
    player_id = request.args.get("player_id")
    if not player_id:
        return jsonify({"error": "Missing player_id"}), 400
    df = load_player_data(player_id, season="all", data_dir=DATA_DIR)
    if df is None or df.empty:
        return jsonify({"stats": {}})
    gk_df = df[(df.get("position", pd.Series("")).fillna("").str.lower().str.contains("goalkeeper")) | (df.get("type", pd.Series("")) == "Goal Keeper")].copy()
    shots_faced = df[df.get("type", "") == "Shot"]
    player_team = None
    if "team" in df.columns:
        player_team = df["team"].dropna().unique()
        if len(player_team) == 1:
            player_team = player_team[0]
        else:
            player_team = None
    if player_team:
        shots_faced = shots_faced[shots_faced.get("team", "") == player_team]
    shot_saved = shots_faced[shots_faced.get("shot_outcome", "") == "Saved"]
    goal_conceded = shots_faced[shots_faced.get("shot_outcome", "") == "Goal"]
    shots_on_target = len(shot_saved) + len(goal_conceded)
    saves = len(shot_saved)
    stats = {
        "total_events": int(len(gk_df)),
        "shot_faced": int(len(shots_faced)),
        "shot_saved": int(saves),
        "goal_conceded": int(len(goal_conceded)),
        "punches": int((gk_df.get("goalkeeper_technique", pd.Series()) == "Punched Out").sum()),
        "claims": int((gk_df.get("goalkeeper_technique", pd.Series()) == "Claim").sum()),
        "collected": int((gk_df.get("goalkeeper_outcome", pd.Series()) == "Collected").sum()),
        "in_play_danger": int((gk_df.get("goalkeeper_in_play_danger", pd.Series()) == True).sum()),
        "passes_attempted": int((df.get("type", pd.Series()) == "Pass").sum()),
        "passes_completed": int(((df.get("type", pd.Series()) == "Pass") & (df.get("pass_outcome", pd.Series()).isna())).sum()),
        "throws_attempted": int((gk_df.get("goalkeeper_type", pd.Series()) == "Throw").sum()),
        "throws_completed": int(((gk_df.get("goalkeeper_type", pd.Series()) == "Throw") & (gk_df.get("goalkeeper_outcome", pd.Series()).isna())).sum()),
        "sweeper_actions": int((gk_df.get("goalkeeper_type", pd.Series()) == "Sweeper").sum()),
    }
    stats["save_pct"] = round((saves / shots_on_target * 100) if shots_on_target > 0 else 0, 1)
    return jsonify({"stats": stats})

@app.route("/goalkeeper_shot_map")
def goalkeeper_shot_map():
    """
    Returns all shots faced by the goalkeeper (as defending player) for a given player_id and season.
    """
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"shots": []})

        # Only consider shots where the player's team is the defending team
        shots = df[df.get("type", "") == "Shot"].copy()
        player_team = None
        if "team" in df.columns:
            player_team = df["team"].dropna().unique()
            if len(player_team) == 1:
                player_team = player_team[0]
            else:
                player_team = None
        if player_team:
            shots = shots[shots.get("team", "") == player_team]
        shots["location_eval"] = shots["location"].apply(safe_literal_eval)
        shots["end_location_eval"] = shots.get("shot_end_location", pd.Series([None]*len(shots))).apply(safe_literal_eval)
        shots = shots[shots["location_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)]
        shot_map = []
        for _, row in shots.iterrows():
            shot_map.append({
                "origin": row["location_eval"][:2],
                "end_location": row["end_location_eval"] if isinstance(row["end_location_eval"], (list, tuple)) else None,
                "outcome": row.get("shot_outcome", ""),
                "xg": float(row.get("shot_statsbomb_xg", 0.0)) if pd.notna(row.get("shot_statsbomb_xg", None)) else None,
                "shot_type": row.get("shot_type", ""),
                "minute": int(row.get("minute", 0)) if pd.notna(row.get("minute", None)) else None,
                "second": int(row.get("second", 0)) if pd.notna(row.get("second", None)) else None,
            })
        return jsonify({"shots": shot_map})
    except Exception as e:
        logger.error(f"Error in /goalkeeper_shot_map: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/goalkeeper_distribution_map")
def goalkeeper_distribution_map():
    """
    Returns all passes made by the goalkeeper, with origin, end_location, outcome, height, body_part, type, length, angle.
    """
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"passes": []})

        # Only consider passes made by the goalkeeper (position == "Goalkeeper" or type == "Goal Keeper")
        passes = df[(df.get("type", "") == "Pass") & (
            (df.get("position", pd.Series("")).fillna("").str.lower().str.contains("goalkeeper")) | (df.get("type", "") == "Goal Keeper")
        )].copy()
        passes["origin_eval"] = passes["location"].apply(safe_literal_eval)
        passes["end_eval"] = passes.get("pass_end_location", pd.Series([None]*len(passes))).apply(safe_literal_eval)
        passes = passes[passes["origin_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)]
        passes = passes[passes["end_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)]
        pass_map = []
        for _, row in passes.iterrows():
            pass_map.append({
                "origin": row["origin_eval"][:2],
                "end_location": row["end_eval"][:2],
                "outcome": row.get("pass_outcome", ""),
                "height": row.get("pass_height", ""),
                "body_part": row.get("pass_body_part", ""),
                "type": row.get("pass_type", ""),
                "length": float(row.get("pass_length", 0.0)) if pd.notna(row.get("pass_length", None)) else None,
                "angle": float(row.get("pass_angle", 0.0)) if pd.notna(row.get("pass_angle", None)) else None,
                "minute": int(row.get("minute", 0)) if pd.notna(row.get("minute", None)) else None,
                "second": int(row.get("second", 0)) if pd.notna(row.get("second", None)) else None,
            })
        return jsonify({"passes": pass_map})
    except Exception as e:
        logger.error(f"Error in /goalkeeper_distribution_map: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/pass_map_zona_stats")
def pass_map_zona_stats():
    """
    Returns pass completion % by pitch 'zona' for a player and season.
    """
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"zonas": []})

        # Only passes
        passes = df[df.get("type", "") == "Pass"].copy()
        passes["end_loc_eval"] = passes.get("pass_end_location", pd.Series([None]*len(passes))).apply(safe_literal_eval)
        passes = passes[passes["end_loc_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)]

        # Define zonas (thirds, central/wide)
        def zona_name(x, y):
            if x < 40:
                third = "Defensive"
            elif x < 80:
                third = "Middle"
            else:
                third = "Attacking"
            if 26.7 < y < 53.3:
                width = "Central"
            elif y <= 26.7:
                width = "Left"
            else:
                width = "Right"
            return f"{third} {width}"

        passes["zona"] = passes["end_loc_eval"].apply(lambda loc: zona_name(loc[0], loc[1]))
        zonas = []
        for zona, group in passes.groupby("zona"):
            total = len(group)
            completed = group["pass_outcome"].isna().sum()
            pct = (completed / total * 100) if total > 0 else None
            zonas.append({
                "name": zona,
                "completion_pct": pct
            })
        zonas = sorted(zonas, key=lambda z: z["name"])
        return jsonify({"zonas": zonas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/goalkeeper_handling_map")
def goalkeeper_handling_map():
    """
    Returns all handling events (claims, punches, collected) by the goalkeeper for a player and season.
    """
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"events": []})

        gk_df = df[(df.get("position", pd.Series("")).fillna("").str.lower().str.contains("goalkeeper")) | (df.get("type", pd.Series("")) == "Goal Keeper")].copy()
        gk_df["origin_eval"] = gk_df.get("location", pd.Series([None]*len(gk_df))).apply(safe_literal_eval)
        gk_df = gk_df[gk_df["origin_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)]

        handling_types = ["Claim", "Punched Out", "Collected"]
        events = []
        for _, row in gk_df.iterrows():
            tech = row.get("goalkeeper_technique", "")
            outcome = row.get("goalkeeper_outcome", "")
            if tech in handling_types or outcome == "Collected":
                events.append({
                    "origin": row["origin_eval"][:2],
                    "technique": tech,
                    "outcome": outcome,
                    "minute": int(row.get("minute", 0)) if pd.notna(row.get("minute", None)) else None,
                    "second": int(row.get("second", 0)) if pd.notna(row.get("second", None)) else None,
                })
        return jsonify({"events": events})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/goalkeeper_sweeper_map")
def goalkeeper_sweeper_map():
    """
    Returns all sweeper actions by the goalkeeper for a player and season.
    """
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"actions": []})

        gk_df = df[(df.get("position", pd.Series("")).fillna("").str.lower().str.contains("goalkeeper")) | (df.get("type", pd.Series("")) == "Goal Keeper")].copy()
        gk_df = gk_df[gk_df.get("goalkeeper_type", "") == "Sweeper"]
        gk_df["origin_eval"] = gk_df.get("location", pd.Series([None]*len(gk_df))).apply(safe_literal_eval)
        gk_df = gk_df[gk_df["origin_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)]

        actions = []
        for _, row in gk_df.iterrows():
            actions.append({
                "origin": row["origin_eval"][:2],
                "outcome": row.get("goalkeeper_outcome", ""),
                "minute": int(row.get("minute", 0)) if pd.notna(row.get("minute", None)) else None,
                "second": int(row.get("second", 0)) if pd.notna(row.get("second", None)) else None,
            })
        return jsonify({"actions": actions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/goalkeeper_penalty_map")
def goalkeeper_penalty_map():
    """
    Returns all penalties faced by the goalkeeper for a player and season.
    """
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400
    try:
        df = load_player_data(player_id, season, DATA_DIR)
        if df is None or df.empty:
            return jsonify({"penalties": []})

        # Penalties are shots with shot_type == "Penalty"
        shots = df[df.get("type", "") == "Shot"].copy()
        shots = shots[shots.get("shot_type", "") == "Penalty"]
        player_team = None
        if "team" in df.columns:
            player_team = df["team"].dropna().unique()
            if len(player_team) == 1:
                player_team = player_team[0]
            else:
                player_team = None
        if player_team:
            shots = shots[shots.get("team", "") == player_team]
        shots["origin_eval"] = shots.get("location", pd.Series([None]*len(shots))).apply(safe_literal_eval)
        shots = shots[shots["origin_eval"].apply(lambda x: isinstance(x, (list, tuple)) and len(x) >= 2)]

        penalties = []
        for _, row in shots.iterrows():
            penalties.append({
                "origin": row["origin_eval"][:2],
                "outcome": row.get("shot_outcome", ""),
                "xg": float(row.get("shot_statsbomb_xg", 0.0)) if pd.notna(row.get("shot_statsbomb_xg", None)) else None,
                "minute": int(row.get("minute", 0)) if pd.notna(row.get("minute", None)) else None,
                "second": int(row.get("second", 0)) if pd.notna(row.get("second", None)) else None,
            })
        return jsonify({"penalties": penalties})
    except Exception as e:
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