import os
import json
import pandas as pd

DATA_DIR = "../data"
PLAYER_INDEX_PATH = os.path.join(DATA_DIR, "player_index.json")

def safe_literal_eval(val):
    from ast import literal_eval
    try:
        return literal_eval(val) if isinstance(val, str) else val
    except Exception:
        return None

def infer_position_from_events(player_id, seasons):
    # Try to infer the most common position from all available event files
    positions = []
    for season in seasons:
        # Try JSON
        json_path = os.path.join(DATA_DIR, str(season), f"{player_id}.json")
        if os.path.exists(json_path):
            try:
                df = pd.read_json(json_path, convert_dates=False)
            except Exception:
                df = None
        else:
            # Try CSV
            csv_path = os.path.join(DATA_DIR, str(season), "players", f"{player_id}_{season}.csv")
            if os.path.exists(csv_path):
                try:
                    df = pd.read_csv(csv_path, low_memory=False)
                except Exception:
                    df = None
            else:
                df = None
        if df is not None and not df.empty and "position" in df.columns:
            # Use only non-null, non-empty positions
            pos_vals = df["position"].dropna().astype(str)
            pos_vals = pos_vals[pos_vals.str.strip() != ""]
            positions.extend(pos_vals.tolist())
    if positions:
        # Return the most frequent position
        from collections import Counter
        return Counter(positions).most_common(1)[0][0]
    return None

def main():
    with open(PLAYER_INDEX_PATH, "r", encoding="utf-8") as f:
        player_index = json.load(f)

    updated = False
    for name, pdata in player_index.items():
        if not isinstance(pdata, dict):
            continue
        if "position" not in pdata or not pdata["position"]:
            player_id = pdata.get("player_id")
            seasons = pdata.get("seasons", [])
            inferred_pos = infer_position_from_events(player_id, seasons)
            if inferred_pos:
                pdata["position"] = inferred_pos
                print(f"Added position '{inferred_pos}' for player '{name}' (ID: {player_id})")
                updated = True
            else:
                print(f"Could not infer position for player '{name}' (ID: {player_id})")

    if updated:
        with open(PLAYER_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(player_index, f, indent=2, ensure_ascii=False)
        print("player_index.json updated with inferred positions.")
    else:
        print("No positions were added. All players already have positions or could not be inferred.")

if __name__ == "__main__":
    main()
