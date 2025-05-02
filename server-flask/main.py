from flask import Flask, jsonify, request
import os
import pandas as pd
from flask_cors import CORS
from collections import defaultdict

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})  # Allow Vite's default port
DATA_DIR = "../data"

@app.route("/")
def home():
    return jsonify({"message": "Welcome to the La Liga Player Explorer API. Available endpoints: /seasons, /players, /player_seasons, /player_events"})

player_index = defaultdict(lambda: {"player_id": None, "seasons": []})

# Build player index on startup
for season in os.listdir(DATA_DIR):
    season_path = os.path.join(DATA_DIR, season, "players")
    if not os.path.isdir(season_path):
        continue
    for file in os.listdir(season_path):
        if file.endswith(".csv"):
            player_id, *_ = file.split("_")
            csv_path = os.path.join(season_path, file)
            try:
                df = pd.read_csv(csv_path, usecols=["player"], nrows=1)
                player_name = df["player"].iloc[0]
                player_index[player_name]["player_id"] = player_id
                player_index[player_name]["seasons"].append(season)
            except Exception as e:
                print(f"Error reading {csv_path}: {e}")

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
                path = os.path.join(DATA_DIR, season_folder, "players", f"{player_id}_{season_folder}.csv")
                if os.path.exists(path):
                    dfs.append(pd.read_csv(path))
        else:
            path = os.path.join(DATA_DIR, season, "players", f"{player_id}_{season}.csv")
            if os.path.exists(path):
                dfs.append(pd.read_csv(path))

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

if __name__ == "__main__":
    app.run(debug=True)