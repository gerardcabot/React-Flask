import os
import pandas as pd
import json

# Define constants
DATA_DIR = "../data"
PLAYER_INDEX_FILE = os.path.join(DATA_DIR, "player_index.json")

# Initialize player index
player_index = {}

def build_player_index():
    """Build player index by scanning player CSV files across all seasons."""
    index = {}
    # Get all season folders
    seasons = [folder for folder in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, folder))]
    
    for season in seasons:
        season_folder_name = season  # Already in the format like "2020_2021"
        player_data_folder = os.path.join(DATA_DIR, season_folder_name, "players")
        if not os.path.isdir(player_data_folder):
            print(f"No 'players' directory found for season {season}. Skipping.")
            continue
        print(f"Processing season: {season}")
        for file in os.listdir(player_data_folder):
            if file.endswith(".csv"):
                player_id = file.split("_")[0]  # Extract player_id from filename (e.g., "5503_2020_2021.csv")
                path = os.path.join(player_data_folder, file)
                try:
                    df = pd.read_csv(path, usecols=["player"], nrows=1)
                    name = df["player"].iloc[0]
                    if name not in index:
                        index[name] = {"player_id": player_id, "seasons": []}
                    if season not in index[name]["seasons"]:
                        index[name]["seasons"].append(season)
                except Exception as e:
                    print(f"Failed reading {file}: {e}")
    # Save index to JSON file
    with open(PLAYER_INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)
    print(f"Player index saved to {PLAYER_INDEX_FILE} with {len(index)} players.")
    return index

# Load or build player index
if os.path.exists(PLAYER_INDEX_FILE):
    try:
        with open(PLAYER_INDEX_FILE, "r") as f:
            player_index = json.load(f)
        print(f"Loaded player index from {PLAYER_INDEX_FILE} with {len(player_index)} players.")
    except Exception as e:
        print(f"Error loading player index: {e}. Rebuilding index.")
        player_index = build_player_index()
else:
    print("Player index file not found. Building new index.")
    player_index = build_player_index()

print("--- Player Index Generation Complete ---")