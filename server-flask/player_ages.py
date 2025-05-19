import json
import requests
from datetime import datetime

def get_birthdate_from_wikidata(player_name):
    """
    Queries Wikidata for the birthdate of a given football player.
    """
    endpoint_url = "https://query.wikidata.org/sparql"
    # SPARQL query to find a football player by name and get their birthdate
    # It prioritizes players who are instances of human (Q5) and have occupation as soccer player (Q937857)
    # It also tries to match the label in English, Spanish, or Catalan.
    query = f"""
    SELECT ?player ?playerLabel ?birthDate WHERE {{
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,es,ca,pt,fr,de,it". }}
      
      ?player rdfs:label ?playerLabel.
      FILTER(LCASE(?playerLabel) = LCASE("{player_name}")). # Exact case-insensitive match

      ?player wdt:P31 wd:Q5.          # Instance of human
      ?player wdt:P106 wd:Q937857.  # Occupation: association football player
      
      OPTIONAL {{ ?player wdt:P569 ?birthDate. }} # P569 is "date of birth"
    }}
    LIMIT 1
    """
    # Fallback query if exact name match fails and player is less strictly defined
    # (e.g. missing "occupation" or "instance of human" for some entries)
    fallback_query = f"""
    SELECT ?player ?playerLabel ?birthDate WHERE {{
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,es,ca,pt,fr,de,it". }}
      
      ?player rdfs:label ?playerLabel.
      FILTER(CONTAINS(LCASE(?playerLabel), LCASE("{player_name}"))). # Contains case-insensitive match
      
      # Try to ensure it's a person, and preferably a soccer player if that data exists
      ?player wdt:P31 wd:Q5. # Instance of human
      OPTIONAL {{ ?player wdt:P106 wd:Q937857. }} # Occupation: association football player (optional here)
      OPTIONAL {{ ?player wdt:P569 ?birthDate. }} # P569 is "date of birth"
    }}
    LIMIT 5 # Fetch a few to see if we can find a good one, though we'll use the first with birthdate
    """

    headers = {
        'User-Agent': 'PlayerAgeFetcher/1.0 (mailto:your_email@example.com; project_url_if_any)', # Be a good internet citizen
        'Accept': 'application/sparql-results+json'
    }

    try_queries = [query, fallback_query]
    
    for q_idx, current_query in enumerate(try_queries):
        try:
            response = requests.get(endpoint_url, headers=headers, params={'query': current_query, 'format': 'json'}, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            results = response.json()
            
            bindings = results.get("results", {}).get("bindings", [])
            
            if bindings:
                for item in bindings:
                    if "birthDate" in item and "value" in item["birthDate"]:
                        # Birthdate is often in "YYYY-MM-DDTHH:mm:ssZ" format
                        birthdate_str = item["birthDate"]["value"]
                        # Extract just the date part
                        return birthdate_str.split("T")[0]
                if q_idx == 0 and not any("birthDate" in item and "value" in item["birthDate"] for item in bindings):
                    print(f"Found player '{player_name}' but no birthdate with primary query, trying fallback.")
                    continue # Try fallback if primary found a player but no birthdate
                elif q_idx == 1 and not any("birthDate" in item and "value" in item["birthDate"] for item in bindings):
                     print(f"Found player '{player_name}' with fallback but no birthdate.")


            if q_idx == 0 and not bindings: # If primary query yielded no results, try fallback
                print(f"No result for '{player_name}' with primary query, trying fallback.")
                continue


        except requests.exceptions.RequestException as e:
            print(f"Error querying Wikidata for {player_name} with query type {q_idx}: {e}")
            if q_idx == 0: # If primary query fails, try fallback
                 continue
            return None # Return None if both queries fail
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response for {player_name}: {e}")
            if q_idx == 0:
                continue
            return None

    print(f"Could not find birthdate for {player_name} on Wikidata after all attempts.")
    return None


def calculate_age_at_season_start(birthdate_str, season_start_year_str):
    """
    Calculates age of a player at the start of a given season.
    Assumes season starts on August 1st of the season_start_year.
    """
    if not birthdate_str:
        return None
    try:
        birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
        season_start_year = int(season_start_year_str)
        season_start_date = datetime(season_start_year, 8, 1).date() # Assume August 1st
        
        age = season_start_date.year - birthdate.year - \
              ((season_start_date.month, season_start_date.day) < (birthdate.month, birthdate.day))
        return age
    except ValueError:
        print(f"Could not parse birthdate {birthdate_str} or season year {season_start_year_str}")
        return None

# --- Main script ---
player_index_file = 'player_index.json' # Make sure this file is in the same directory or provide full path

try:
    with open(player_index_file, 'r', encoding='utf-8') as f:
        player_data = json.load(f)
except FileNotFoundError:
    print(f"Error: {player_index_file} not found.")
    exit()
except json.JSONDecodeError:
    print(f"Error: Could not decode JSON from {player_index_file}.")
    exit()

updated_count = 0
not_found_count = 0

print("Starting to update player data with birthdates and ages...")

for player_name, info in player_data.items():
    print(f"\nProcessing player: {player_name}")
    if "birthdate" in info and info["birthdate"]: # Skip if already processed to some extent
        print(f"Skipping {player_name}, already has birthdate: {info['birthdate']}")
        # Optionally, ensure age_at_first_season_start is also calculated if birthdate exists
        if "seasons" in info and info["seasons"] and "age_at_first_season_start" not in info:
            first_season_year_str = info["seasons"][0].split("_")[0]
            info["age_at_first_season_start"] = calculate_age_at_season_start(info["birthdate"], first_season_year_str)
            if info["age_at_first_season_start"] is not None:
                print(f"Calculated missing age_at_first_season_start for {player_name}: {info['age_at_first_season_start']}")
                updated_count +=1 # Count as an update if we added this
        continue

    birthdate = get_birthdate_from_wikidata(player_name)
    
    if birthdate:
        info["birthdate"] = birthdate
        print(f"Found birthdate for {player_name}: {birthdate}")
        
        if "seasons" in info and info["seasons"]:
            # Calculate age at the start of their first listed season
            first_season_year_str = info["seasons"][0].split("_")[0]
            age_at_start = calculate_age_at_season_start(birthdate, first_season_year_str)
            info["age_at_first_season_start"] = age_at_start
            if age_at_start is not None:
                 print(f"Age of {player_name} at start of {info['seasons'][0]}: {age_at_start}")
            else:
                print(f"Could not calculate age for {player_name} for season {info['seasons'][0]}")
        else:
            info["age_at_first_season_start"] = None
            print(f"No seasons listed for {player_name} to calculate age at start.")
            
        updated_count += 1
    else:
        info["birthdate"] = None
        info["age_at_first_season_start"] = None
        not_found_count += 1

    # Optional: add a small delay to be nice to Wikidata's API
    # import time
    # time.sleep(0.5) # Sleep for 0.5 seconds

print(f"\n--- Processing Complete ---")
print(f"Successfully updated information for {updated_count} players.")
print(f"Could not find birthdate for {not_found_count} players.")

# Save the updated data back to the JSON file
updated_player_index_file = 'player_index_with_ages.json'
with open(updated_player_index_file, 'w', encoding='utf-8') as f:
    json.dump(player_data, f, ensure_ascii=False, indent=4)

print(f"\nUpdated player index saved to: {updated_player_index_file}")
print("Please review the file, especially for players where birthdate was not found (set to null).")
print("You might need to manually verify or find data for those players using other sources if critical.")