from flask import Flask, jsonify, request
from flask import Flask, request, send_file, abort
import os
import pandas as pd
from flask_cors import CORS
from collections import defaultdict
import io
from io import BytesIO
import base64
import matplotlib
from matplotlib import pyplot as plt
from mplsoccer import Pitch, Radar, grid, FontManager, VerticalPitch
from ast import literal_eval
import json
from scipy.ndimage import gaussian_filter
from datetime import datetime
from matplotlib import patheffects
from matplotlib.lines import Line2D
import logging
from matplotlib import patheffects
import numpy as np





STATIC_IMG_DIR = os.path.join("static", "images")
os.makedirs(STATIC_IMG_DIR, exist_ok=True)


matplotlib.use("Agg")  # Force non-interactive backend


robotto_thin = FontManager('https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Thin.ttf')
robotto_bold = FontManager('https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf')

# app = Flask(__name__)
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})  # Allow Vite's default port
DATA_DIR = "../data"
STATIC_IMG_DIR = "static/images"
BOUNDS_DIR = "radar_bounds"
os.makedirs(BOUNDS_DIR, exist_ok=True)

@app.route("/")
def home():
    return jsonify({"message": "Welcome to the La Liga Player Explorer API. Available endpoints: /seasons, /players, /player_seasons, /player_events"})

player_index_path = os.path.join(DATA_DIR, "player_index.json")
if os.path.exists(player_index_path):
    with open(player_index_path, "r", encoding="utf-8") as f:
        player_index = json.load(f)
else:
    player_index = {}
    print("⚠️ Warning: player_index.json not found.")



@app.route("/all_players")
def all_players():
    try:
        return jsonify([
            {"name": name, "player_id": data["player_id"], "seasons": data["seasons"]}
            for name, data in sorted(player_index.items())
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/player_events")
def player_events():
    player_id = request.args.get("player_id")
    season = request.args.get("season")  # can be 'all'

    try:
        dfs = []
        if season == "all":
            for season_folder in os.listdir(DATA_DIR):
                # season_folder = season.replace("/", "_")  # Normaliza
                path = os.path.join(DATA_DIR, season_folder, "players", f"{player_id}_{season_folder}.csv")
                if os.path.exists(path):
                    dfs.append(pd.read_csv(path, low_memory=False))

        else:
            # season_folder = season.replace("/", "_")  # Normaliza
            path = os.path.join(DATA_DIR, season, "players", f"{player_id}_{season}.csv")
            if os.path.exists(path):
                dfs.append(pd.read_csv(path, low_memory=False))


        if dfs:
            full_df = pd.concat(dfs, ignore_index=True)
            return full_df.to_json(orient="records")
        else:
            return jsonify({"error": "No data found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/seasons")
def list_seasons():
    try:
        seasons = [folder for folder in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, folder))]
        return jsonify(sorted(seasons))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/pass_map_plot")
def pass_map_plot():
    player_id = request.args.get("player_id")
    season = request.args.get("season")

    try:
        if not player_id or not season:
            return jsonify({"error": "Missing player_id or season"}), 400

        dfs = []
        columns_needed = ["type", "location", "pass_end_location", "pass_outcome", "pass_goal_assist"]

        if season == "all":
            for folder in os.listdir(DATA_DIR):
                path = os.path.join(DATA_DIR, folder, "players", f"{player_id}_{folder}.csv")
                if os.path.exists(path):
                    dfs.append(pd.read_csv(path, usecols=columns_needed))
        else:
            path = os.path.join(DATA_DIR, season, "players", f"{player_id}_{season}.csv")
            if os.path.exists(path):
                dfs.append(pd.read_csv(path, usecols=columns_needed))

        if not dfs:
            return jsonify({"error": "No data found"}), 404

        df = pd.concat(dfs)
        df = df[df["type"] == "Pass"]
        df = df[df["location"].notna() & df["pass_end_location"].notna()]
        df["location"] = df["location"].apply(literal_eval)
        df["pass_end_location"] = df["pass_end_location"].apply(literal_eval)

        # Add flags for pass attributes
        pass_data = [
            {
                "start_x": row["location"][0],
                "start_y": row["location"][1],
                "end_x": row["pass_end_location"][0],
                "end_y": row["pass_end_location"][1],
                "completed": pd.isna(row["pass_outcome"]),
                "assist": row.get("pass_goal_assist") in [True, 1, "True", "true"],
                "final_third": row["pass_end_location"][0] > 80
            }
            for _, row in df.iterrows()
        ]

        return jsonify({"passes": pass_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route("/position_heatmap")
def position_heatmap():
    player_id = request.args.get("player_id")
    season = request.args.get("season")

    try:
        player_dir = os.path.join(STATIC_IMG_DIR, player_id)
        os.makedirs(player_dir, exist_ok=True)

        image_filename = f"{season}_heatmap.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{player_id}/{image_filename}"

        if os.path.exists(image_path):
            return jsonify({"image_url": image_url})

        dfs = []
        columns_needed = ["location"]
        if season == "all":
            for folder in os.listdir(DATA_DIR):
                path = os.path.join(DATA_DIR, folder, "players", f"{player_id}_{folder}.csv")
                if os.path.exists(path):
                    dfs.append(pd.read_csv(path, usecols=columns_needed))
        else:
            path = os.path.join(DATA_DIR, season, "players", f"{player_id}_{season}.csv")
            if os.path.exists(path):
                dfs.append(pd.read_csv(path, usecols=columns_needed))

        if not dfs:
            return jsonify({"error": "No data found"}), 404
        
        
        df = pd.concat(dfs)
        df = df[df["location"].notna()].copy()
        if df.empty:
            return jsonify({"error": "No location data"}), 404

        # Convert location column
        df["location"] = df["location"].apply(literal_eval)
        df["x"] = df["location"].apply(lambda loc: loc[0])
        df["y"] = df["location"].apply(lambda loc: loc[1])

        # Set up pitch
        pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2,
                              pitch_color='#22312b', line_color='white')
        fig, ax = pitch.draw(figsize=(4.125, 6))

        # Positional heatmap
        bin_statistic = pitch.bin_statistic_positional(df.x, df.y, statistic='count',
                                                       positional='full', normalize=True)

        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='coolwarm', edgecolors='#22312b')
        pitch.scatter(df.x, df.y, c='white', s=2, ax=ax)

        # Optional: Labels (percentages)
        from matplotlib import patheffects
        path_eff = [patheffects.withStroke(linewidth=2, foreground='black')]
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=18,
                            ax=ax, ha='center', va='center',
                            str_format='{:.0%}', path_effects=path_eff)

        fig.savefig(image_path, format='png', bbox_inches='tight')
        plt.close(fig)

        return jsonify({"image_url": image_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/radar_chart')
def radar_chart():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    if not player_id or not season:
        return jsonify({"error": "Missing player_id or season"}), 400

    try:
        # File and image path
        player_dir = os.path.join(STATIC_IMG_DIR, player_id)
        os.makedirs(player_dir, exist_ok=True)
        image_filename = f"{season}_radar.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{player_id}/{image_filename}"

        if os.path.exists(image_path):
            return jsonify({"image_url": image_url})

        # Load player data
        path = os.path.join(DATA_DIR, season, "players", f"{player_id}_{season}.csv")
        if not os.path.exists(path):
            return jsonify({"error": "Player data not found"}), 404

        df = pd.read_csv(path, low_memory=False)
        df["player_id"] = df["player_id"].astype(str)
        player_df = df[df["player_id"] == player_id]

        if player_df.empty:
            return jsonify({"error": "No data for this player"}), 404

        # Compute player stats
        assists = len(player_df[player_df["pass_goal_assist"] == True])
        goals = len(player_df[(player_df["type"] == "Shot") & (player_df["shot_outcome"] == "Goal")])
        dribbles_completed = len(player_df[(player_df["type"] == "Dribble") & (player_df["dribble_outcome"] == "Complete")])
        xg = player_df[player_df["type"] == "Shot"]["shot_statsbomb_xg"].sum() if "shot_statsbomb_xg" in player_df.columns else 0
        miscontrols = len(player_df[player_df["type"] == "Miscontrol"])

        values = [assists, goals, dribbles_completed, xg, miscontrols]

        # Define radar parameters
        params = ["Assists", "Goals", "Dribbles Completed", "xG", "Miscontrols"]

        # Check if bounds file exists for the season
        bounds_file = os.path.join(BOUNDS_DIR, f"{season}_bounds.json")
        if os.path.exists(bounds_file):
            with open(bounds_file, "r") as f:
                bounds = json.load(f)
            high = bounds["high"]
        else:
            # Compute maximum values for the season
            season_path = os.path.join(DATA_DIR, season, "players")
            if not os.path.exists(season_path):
                return jsonify({"error": "Season data not found"}), 404

            max_assists = 0
            max_goals = 0
            max_dribbles = 0
            max_xg = 0
            max_miscontrols = 0

            for file in os.listdir(season_path):
                if file.endswith(".csv"):
                    file_path = os.path.join(season_path, file)
                    try:
                        season_df = pd.read_csv(file_path, low_memory=False)
                        season_df["player_id"] = season_df["player_id"].astype(str)

                        for pid in season_df["player_id"].unique():
                            p_df = season_df[season_df["player_id"] == pid]
                            p_assists = len(p_df[p_df["pass_goal_assist"] == True])
                            p_goals = len(p_df[(p_df["type"] == "Shot") & (p_df["shot_outcome"] == "Goal")])
                            p_dribbles = len(p_df[(p_df["type"] == "Dribble") & (p_df["dribble_outcome"] == "Complete")])
                            p_xg = p_df[p_df["type"] == "Shot"]["shot_statsbomb_xg"].sum() if "shot_statsbomb_xg" in p_df.columns else 0
                            p_miscontrols = len(p_df[p_df["type"] == "Miscontrol"])

                            max_assists = max(max_assists, p_assists)
                            max_goals = max(max_goals, p_goals)
                            max_dribbles = max(max_dribbles, p_dribbles)
                            max_xg = max(max_xg, p_xg)
                            max_miscontrols = max(max_miscontrols, p_miscontrols)
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
                        continue

            # Ensure non-zero maximums to avoid division by zero in radar scaling
            high = [
                max(max_assists, 1),
                max(max_goals, 1),
                max(max_dribbles, 1),
                max(max_xg, 1),
                max(max_miscontrols, 1)
            ]

            # Save bounds to file
            bounds = {"high": high}
            with open(bounds_file, "w") as f:
                json.dump(bounds, f)

        low = [0] * len(params)
        lower_is_better = ["Miscontrols"]

        radar = Radar(params, low, high, lower_is_better=lower_is_better, round_int=[True] * len(params))

        # Create radar plot
        fig, ax = radar.setup_axis()
        rings = radar.draw_circles(ax=ax, facecolor="#f9f9f9", edgecolor="#bbb")
        radar_output = radar.draw_radar(values, ax=ax,
                                        kwargs_radar={'facecolor': "#003f5c", "alpha": 0.7},
                                        kwargs_rings={"facecolor": "#7a5195", "alpha": 0.4})
        radar.draw_range_labels(ax=ax, fontsize=10)
        radar.draw_param_labels(ax=ax, fontsize=11)

        # Save image
        fig.savefig(image_path, bbox_inches="tight")
        plt.close(fig)

        return jsonify({"image_url": image_url})

    except Exception as e:
        print(f"Radar chart generation error: {e}")
        return jsonify({"error": str(e)}), 500
    

@app.route("/shot_map")
def shot_map():
    player_id = request.args.get("player_id")
    season = request.args.get("season")

    try:
        if not player_id or not season:
            return jsonify({"error": "Missing player_id or season"}), 400

        path = os.path.join(DATA_DIR, season, "players", f"{player_id}_{season}.csv")
        if not os.path.exists(path):
            return jsonify({"error": "File not found"}), 404

        df = pd.read_csv(path, low_memory=False)
        df = df[df["type"] == "Shot"]
        df = df[df["location"].notna() & df["shot_statsbomb_xg"].notna()].copy()

        df["location"] = df["location"].apply(literal_eval)
        df["start_location_x"] = df["location"].apply(lambda loc: loc[0])
        df["start_location_y"] = df["location"].apply(lambda loc: loc[1])
        df["statsbomb_xg"] = df["shot_statsbomb_xg"]

        # Handle shot_outcome for goal detection
        df["goal"] = df["shot_outcome"].fillna("Unknown") == "Goal"

        # Parse shot_end_location for additional goal confirmation (optional)
        df["shot_end_location"] = df["shot_end_location"].apply(
            lambda x: literal_eval(x) if pd.notna(x) else [0, 0, 0]
        )
        df["end_x"] = df["shot_end_location"].apply(lambda loc: loc[0] if loc else 0)
        df["is_on_target"] = df["end_x"].between(118.0, 122.0)  # Goal area approximation

        # Prepare shot data with goal indicator
        shot_data = [
            {
                "x": row["start_location_x"],
                "y": row["start_location_y"],
                "xg": row["statsbomb_xg"],
                "goal": row["goal"] or (row["is_on_target"] and row["shot_outcome"] == "Goal")
            }
            for _, row in df.iterrows()
        ]

        return jsonify({"shots": shot_data})

    except Exception as e:
        logging.error(f"Error in /shot_map: {str(e)}")
        return jsonify({"error": str(e)}), 500
    


@app.route("/pass_completion_heatmap")
def pass_completion_heatmap():
    player_id = request.args.get("player_id")
    season = request.args.get("season")

    try:
        player_dir = os.path.join(STATIC_IMG_DIR, player_id)
        os.makedirs(player_dir, exist_ok=True)

        image_filename = f"{season}_pass_completion_heatmap.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{player_id}/{image_filename}"

        if os.path.exists(image_path):
            return jsonify({"image_url": image_url})

        dfs = []
        columns_needed = ["type", "location", "pass_outcome"]
        if season == "all":
            for folder in os.listdir(DATA_DIR):
                path = os.path.join(DATA_DIR, folder, "players", f"{player_id}_{folder}.csv")
                if os.path.exists(path):
                    dfs.append(pd.read_csv(path, usecols=columns_needed))
        else:
            path = os.path.join(DATA_DIR, season, "players", f"{player_id}_{season}.csv")
            if os.path.exists(path):
                dfs.append(pd.read_csv(path, usecols=columns_needed))

        if not dfs:
            return jsonify({"error": "No data found"}), 404
        
        df = pd.concat(dfs)
        df = df[df["type"] == "Pass"]
        df = df[df["location"].notna()].copy()
        if df.empty:
            return jsonify({"error": "No pass data"}), 404

        df["location"] = df["location"].apply(literal_eval)
        df["x"] = df["location"].apply(lambda loc: loc[0])
        df["y"] = df["location"].apply(lambda loc: loc[1])
        df["completed"] = df["pass_outcome"].isna()

        pitch = VerticalPitch(pitch_type='statsbomb', line_zorder=2,
                              pitch_color='#22312b', line_color='white')
        fig, ax = pitch.draw(figsize=(4.125, 6))

        # Bin passes into positional sections
        bin_statistic = pitch.bin_statistic_positional(df.x, df.y, values=df.completed,
                                                       statistic='mean', positional='full')

        # Replace None values with 0 in the bin_statistic result
        for section in bin_statistic:
            if 'statistic' in section:
                section['statistic'] = [0 if val is None else val for val in section['statistic']]

        # Visualize the pass completion percentages
        pitch.heatmap_positional(bin_statistic, ax=ax, cmap='Blues', edgecolors='#22312b')

        # Overlay the percentages

        path_eff = [patheffects.withStroke(linewidth=2, foreground='black')]
        pitch.label_heatmap(bin_statistic, color='#f4edf0', fontsize=18,
                            ax=ax, ha='center', va='center',
                            str_format='{:.0%}', path_effects=path_eff)

        fig.savefig(image_path, format='png', bbox_inches='tight')
        plt.close(fig)

        return jsonify({"image_url": image_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/pressure_heatmap")
def pressure_heatmap():
    player_id = request.args.get("player_id")
    season = request.args.get("season")

    try:
        player_dir = os.path.join(STATIC_IMG_DIR, player_id)
        os.makedirs(player_dir, exist_ok=True)

        image_filename = f"{season}_pressure_heatmap.png"
        image_path = os.path.join(player_dir, image_filename)
        image_url = f"/static/images/{player_id}/{image_filename}"

        if os.path.exists(image_path):
            return jsonify({"image_url": image_url})

        dfs = []
        columns_needed = ["type", "location", "player_id"]
        if season == "all":
            for folder in os.listdir(DATA_DIR):
                path = os.path.join(DATA_DIR, folder, "players", f"{player_id}_{folder}.csv")
                if os.path.exists(path):
                    dfs.append(pd.read_csv(path, usecols=columns_needed))
        else:
            path = os.path.join(DATA_DIR, season, "players", f"{player_id}_{season}.csv")
            if os.path.exists(path):
                dfs.append(pd.read_csv(path, usecols=columns_needed))

        if not dfs:
            return jsonify({"error": "No data found"}), 404
        
        df = pd.concat(dfs)
        df = df[df["type"] == "Pressure"]
        df = df[df["location"].notna()].copy()
        if df.empty:
            return jsonify({"error": "No pressure data"}), 404

        df["location"] = df["location"].apply(literal_eval)
        df["x"] = df["location"].apply(lambda loc: loc[0])
        df["y"] = df["location"].apply(lambda loc: loc[1])

        pitch = Pitch(pitch_type='statsbomb', line_zorder=2,
                      pitch_color='#22312b', line_color='#efefef')
        fig, ax = pitch.draw(figsize=(6.6, 4.125))
        fig.set_facecolor('#22312b')

        bin_statistic = pitch.bin_statistic(df.x, df.y, statistic='count', bins=(25, 25))
        bin_statistic['statistic'] = gaussian_filter(bin_statistic['statistic'], 1)
        pcm = pitch.heatmap(bin_statistic, ax=ax, cmap='hot', edgecolors='#22312b')

        cbar = fig.colorbar(pcm, ax=ax, shrink=0.6)
        cbar.outline.set_edgecolor('#efefef')
        cbar.ax.yaxis.set_tick_params(color='#efefef')
        ticks = plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#efefef')

        fig.savefig(image_path, format='png', bbox_inches='tight')
        plt.close(fig)

        return jsonify({"image_url": image_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


    except Exception as e:
        logging.error(f"Error in /xt_heatmap: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500



@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    app.run(debug=True)