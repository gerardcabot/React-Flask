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
from mplsoccer import Pitch, Radar, grid, FontManager
from ast import literal_eval
import json
from scipy.ndimage import gaussian_filter

matplotlib.use("Agg")  # Force non-interactive backend


robotto_thin = FontManager('https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Thin.ttf')
robotto_bold = FontManager('https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf')

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})  # Allow Vite's default port
DATA_DIR = "../data"

@app.route("/")
def home():
    return jsonify({"message": "Welcome to the La Liga Player Explorer API. Available endpoints: /seasons, /players, /player_seasons, /player_events"})

# player_index = defaultdict(lambda: {"player_id": None, "seasons": []})

# # Build player index on startup
# for season in os.listdir(DATA_DIR):
#     season_path = os.path.join(DATA_DIR, season, "players")
#     if not os.path.isdir(season_path):
#         continue
#     for file in os.listdir(season_path):
#         if file.endswith(".csv"):
#             player_id, *_ = file.split("_")
#             csv_path = os.path.join(season_path, file)
#             try:
#                 df = pd.read_csv(csv_path, usecols=["player"], nrows=1)
#                 player_name = df["player"].iloc[0]
#                 player_index[player_name]["player_id"] = player_id
#                 player_index[player_name]["seasons"].append(season)
#             except Exception as e:
#                 print(f"Error reading {csv_path}: {e}")

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
        dfs = []
        columns_needed = ["type", "location", "pass_end_location", "pass_outcome"]

        if season == "all":
            for season_folder in os.listdir(DATA_DIR):
                path = os.path.join(DATA_DIR, season_folder, "players", f"{player_id}_{season_folder}.csv")
                if os.path.exists(path):
                    dfs.append(pd.read_csv(path, usecols=columns_needed, low_memory=False))
        else:
            season_folder = season
            path = os.path.join(DATA_DIR, season_folder, "players", f"{player_id}_{season_folder}.csv")
            if os.path.exists(path):
                dfs.append(pd.read_csv(path, usecols=columns_needed, low_memory=False))

        if not dfs:
            return jsonify({"error": "No data found"}), 404

        df = pd.concat(dfs, ignore_index=True)

        # Filtrar eventos de tipo "Pass"
        passes = df[
            (df["type"] == "Pass") &
            (df["location"].notna()) &
            (df["pass_end_location"].notna())
        ].copy()

        # Convertir coordenadas string a listas
        passes["location"] = passes["location"].apply(literal_eval)
        passes["pass_end_location"] = passes["pass_end_location"].apply(literal_eval)

        # Dibujar pitch y pases
        pitch = Pitch(pitch_type='statsbomb', axis=True, label=True, pitch_color='white', line_color='black')
        fig, ax = pitch.draw(figsize=(10, 7))

        for _, row in passes.iterrows():
            x1, y1 = row["location"]
            x2, y2 = row["pass_end_location"]
            color = "green" if pd.isna(row.get("pass_outcome")) else "red"
            pitch.arrows(x1, y1, x2, y2, ax=ax, width=1, headwidth=3, color=color, alpha=0.5)

        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return jsonify({"image": f"data:image/png;base64,{img_base64}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/position_heatmap")
def position_heatmap():
    player_id = request.args.get("player_id")
    season = request.args.get("season")
    try:
        dfs = []
        columns_needed = ["location", "type"]
        if season == "all":
            for season_folder in os.listdir(DATA_DIR):
                path = os.path.join(DATA_DIR, season_folder, "players", f"{player_id}_{season_folder}.csv")
                if os.path.exists(path):
                    dfs.append(pd.read_csv(path, usecols=columns_needed, low_memory=False))
        else:
            path = os.path.join(DATA_DIR, season, "players", f"{player_id}_{season}.csv")
            if os.path.exists(path):
                dfs.append(pd.read_csv(path, usecols=columns_needed, low_memory=False))

        if not dfs:
            return jsonify({"error": "No data found"}), 404

        df = pd.concat(dfs, ignore_index=True)
        df = df[df["location"].notna()].copy()
        if df.empty:
            return jsonify({"error": "No location data found"}), 404

        df["location"] = df["location"].apply(literal_eval)
        df["x"] = df["location"].apply(lambda loc: loc[0])
        df["y"] = df["location"].apply(lambda loc: loc[1])

        # Crear grid amb pitch.grid
        pitch = Pitch(
            pitch_type='statsbomb',
            pitch_color='#2E8B57',  
            line_color='white',      # Línies blanques per a contrast
            stripe=True              # Afegir ratlles al camp per estètica
        )
        fig, axs = pitch.grid(
            endnote_height=0.03, endnote_space=0,
            grid_width=0.88, left=0.025,
            title_height=0.06, title_space=0,
            axis=False,
            grid_height=0.86
        )
        fig.set_facecolor('black')  # Fons fosc per al gràfic

        # Dibuixar el camp explícitament abans del heatmap
        pitch.draw(ax=axs['pitch'])

        # Plot heatmap amb transparència
        bin_statistic = pitch.bin_statistic(df["x"], df["y"], statistic='count', bins=(25, 25))
        bin_statistic['statistic'] = gaussian_filter(bin_statistic['statistic'], 1)
        pcm = pitch.heatmap(
            bin_statistic,
            ax=axs['pitch'],
            cmap='Reds',  # Canviem a 'Reds' per millor contrast amb el verd
            alpha=0.7,    # Afegim transparència per veure el camp al fons
            edgecolors='#22312b'
        )

        # Afegir barra de colors
        ax_cbar = fig.add_axes((0.915, 0.093, 0.03, 0.786))
        cbar = plt.colorbar(pcm, cax=ax_cbar)
        cbar.outline.set_edgecolor('#efefef')
        cbar.ax.yaxis.set_tick_params(color='#efefef')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#efefef')

        # Títol i nota final
        player_name = next((name for name, data in player_index.items() if data["player_id"] == player_id), player_id)
        axs['title'].text(0.5, 0.5, f"Position Heatmap for {player_name}", color='white',
                         va='center', ha='center', fontsize=20)
        axs['endnote'].text(1, 0.5, '', va='center', ha='right', fontsize=12, color='#dee6ea')

        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return jsonify({"image": f"data:image/png;base64,{img_base64}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/radar_chart', methods=['GET'])
def generate_radar_chart():
    # Get player_id and season from query parameters
    player_id = request.args.get('player_id')
    season = request.args.get('season')
    
    if not player_id or not season:
        abort(400, description="player_id and season are required query parameters")
    
    # Construct the filename
    filename = f"data/{player_id}_{season}.csv"
    if not os.path.exists(filename):
        abort(404, description="Data file not found for the given player_id and season")
    
    # Load and process the CSV data
    try:
        with open(filename, 'r') as f:
            df = pd.read_csv(f)
        
        # Filter for the specified player
        player_df = df[df['player_id'] == player_id]
        
        # Calculate metrics
        passes_completed = len(player_df[(player_df['type'] == 'Pass') & (~player_df['pass_outcome'].isin(['Incomplete', 'Out', 'Unknown']))])
        shots = len(player_df[player_df['type'] == 'Shot'])
        goals = len(player_df[(player_df['type'] == 'Shot') & (player_df['shot_outcome'] == 'Goal')])
        dribbles_completed = len(player_df[(player_df['type'] == 'Dribble') & (player_df['dribble_outcome'] == 'Complete')])
        fouls_won = len(player_df[player_df['type'] == 'Foul Won'])
        
        # Define raw values
        player_values = [passes_completed, shots, goals, dribbles_completed, fouls_won]
        
        # Set min and max ranges for normalization
        low = [0, 0, 0, 0, 0]
        high = [500, 50, 10, 50, 20]
        
        # Define parameter labels
        params = ['Passes Completed', 'Shots', 'Goals', 'Dribbles Completed', 'Fouls Won']
        
        # Create the figure using the grid function from mplsoccer
        fig, axs = grid(figheight=14, grid_height=0.915, title_height=0.06, endnote_height=0.025,
                        title_space=0, endnote_space=0, grid_key='radar', axis=False)
        
        # Set up the radar chart
        radar = Radar(params=params, min_range=low, max_range=high)
        
        # Plot the radar
        radar.setup_axis(ax=axs['radar'])
        rings_inner = radar.draw_circles(ax=axs['radar'], facecolor='#ffb2b2', edgecolor='#fc5f5f')
        radar_output = radar.draw_radar(player_values, ax=axs['radar'],
                                        kwargs_radar={'facecolor': '#aa65b2'},
                                        kwargs_rings={'facecolor': '#66d8ba'})
        radar_poly, rings_outer, vertices = radar_output
        
        # Add range and parameter labels
        range_labels = radar.draw_range_labels(ax=axs['radar'], fontsize=25,
                                               fontproperties=robotto_thin.prop)
        param_labels = radar.draw_param_labels(ax=axs['radar'], fontsize=25,
                                               fontproperties=robotto_thin.prop)
        
        # Add the endnote and title text (using placeholder player info, to be replaced dynamically if available)
        player_name = player_df['player_name'].iloc[0] if 'player_name' in player_df.columns and not player_df['player_name'].iloc[0] == '' else f"Player {player_id}"
        team = player_df['team_name'].iloc[0] if 'team_name' in player_df.columns and not player_df['team_name'].iloc[0] == '' else "Unknown Team"
        position = player_df['position'].iloc[0] if 'position' in player_df.columns and not player_df['position'].iloc[0] == '' else "Unknown Position"
        
        endnote_text = axs['endnote'].text(0.99, 0.5, 'Inspired By: StatsBomb / Rami Moghadam', fontsize=15,
                                           fontproperties=robotto_thin.prop, ha='right', va='center')
        title1_text = axs['title'].text(0.01, 0.65, player_name, fontsize=25,
                                        fontproperties=robotto_bold.prop, ha='left', va='center')
        title2_text = axs['title'].text(0.01, 0.25, team, fontsize=20,
                                        fontproperties=robotto_thin.prop,
                                        ha='left', va='center', color='#B6282F')
        title3_text = axs['title'].text(0.99, 0.65, 'Radar Chart', fontsize=25,
                                        fontproperties=robotto_bold.prop, ha='right', va='center')
        title4_text = axs['title'].text(0.99, 0.25, position, fontsize=20,
                                        fontproperties=robotto_thin.prop,
                                        ha='right', va='center', color='#B6282F')
        
        # Save the figure to a BytesIO object
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0)
        
        # Return the image
        return send_file(img_buffer, mimetype='image/png')
    
    except Exception as e:
        abort(500, description=f"Error generating radar chart: {str(e)}")
        plt.close()

if __name__ == "__main__":
    app.run(debug=True)