import pandas as pd
import requests
import datetime

# Map people to columns
people = ['Bobby', 'Chet', 'Clyde', 'Henry', 'Riley', 'Nick']
away_pick_cols = ['B', 'C', 'D', 'E', 'F', 'G']  # Columns 2-7 for away picks
home_pick_cols = ['K', 'L', 'M', 'N', 'O', 'P']  # Columns 11-16 for home picks

# Hardcoded fallback for Week 1 2025 winners (if API fails)
week1_fallback = {
    "Dallas Cowboys @ Philadelphia Eagles": 'Home',
    "Kansas City Chiefs @ Los Angeles Chargers": 'Home',
    "Arizona Cardinals @ New Orleans Saints": 'Away',
    "Carolina Panthers @ Jacksonville Jaguars": 'Home',
    "Cincinnati Bengals @ Cleveland Browns": 'Away',
    "Las Vegas Raiders @ New England Patriots": 'Away',
    "Miami Dolphins @ Indianapolis Colts": 'Home',
    "New York Giants @ Washington Commanders": 'Home',
    "Pittsburgh Steelers @ New York Jets": 'Away',
    "Tampa Bay Buccaneers @ Atlanta Falcons": 'Away',
    "San Francisco 49ers @ Seattle Seahawks": 'Away',
    "Tennessee Titans @ Denver Broncos": 'Home',
    "Detroit Lions @ Green Bay Packers": 'Home',
    "Houston Texans @ Los Angeles Rams": 'Home',
    "Baltimore Ravens @ Buffalo Bills": 'Home',
    "Minnesota Vikings @ Chicago Bears": 'Away'
}

# Function to fetch NFL game results for a given week (ESPN API)
def fetch_nfl_results(week, season=2025):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}&season={season}"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching Week {week} data from API. Using fallback if available.")
            if week == 1:
                return week1_fallback
            return {}
        data = response.json()
        games = {}
        for event in data.get('events', []):
            competition = event['competitions'][0]
            away_team = competition['competitors'][1]['team']['displayName'].strip().rstrip('¹').strip()  # Away is index 1, clean superscript
            home_team = competition['competitors'][0]['team']['displayName'].strip().rstrip('¹').strip()  # Home is index 0
            away_score = int(competition['competitors'][1]['score'])
            home_score = int(competition['competitors'][0]['score'])
            status = competition['status']['type']['completed']
            if status:
                if away_score > home_score:
                    winner = 'Away'
                elif home_score > away_score:
                    winner = 'Home'
                else:
                    winner = 'Tie'
                game_key = f"{away_team} @ {home_team}"
                games[game_key] = winner
            else:
                games[game_key] = None  # Not completed
        return games
    except Exception as e:
        print(f"API error: {e}. Using fallback if available.")
        if week == 1:
            return week1_fallback
        return {}

# Main function to update Excel
def update_picks(file_path='nfl_picks_2025.xlsx'):
    xl = pd.ExcelFile(file_path)
    all_weekly_results = {}
    
    for sheet_name in xl.sheet_names:
        if not sheet_name.startswith('Sheet'):
            continue  # Skip non-week sheets like Cumulative
        week_num = int(sheet_name.replace('Sheet', ''))  # Sheet1 -> 1
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)  # No header, raw read
        
        # Fetch results for this week
        results = fetch_nfl_results(week_num)
        
        # Process games: Find game rows (assume from row 2/index 2 to before records)
        game_rows = []
        for row_idx in range(2, 22):  # Rows 3-22-ish, adjust if more games
            away_val = df.iloc[row_idx, 7]
            home_val = df.iloc[row_idx, 9]
            if pd.notna(away_val) and pd.notna(home_val) and isinstance(away_val, str) and isinstance(home_val, str):
                away_team = str(away_val).strip().rstrip('¹').strip()
                home_team = str(home_val).strip().rstrip('¹').strip()
                game_key = f"{away_team} @ {home_team}"
                actual_winner = results.get(game_key)
                if actual_winner is None:
                    if df.shape[1] > 16 and pd.notna(df.iloc[row_idx, 16]):
                        actual_winner = df.iloc[row_idx, 16]  # "Away", "Home", or "Tie"
                
                print(f"Processing game in Week {week_num}: {game_key} - Winner found: {actual_winner}")  # Debug print
                
                if actual_winner:
                    # Calculate wins/losses for this game
                    for i, person in enumerate(people):
                        away_pick = df.iloc[row_idx, 1 + i]  # B=1, C=2, etc.
                        home_pick = df.iloc[row_idx, 10 + i]  # K=10, L=11, etc.
                        picked = None
                        if str(away_pick).strip().lower() == 'x':
                            picked = 'Away'
                        elif str(home_pick).strip().lower() == 'x':
                            picked = 'Home'
                        if picked:
                            result = 'Win' if picked == actual_winner else 'Loss' if actual_winner != 'Tie' else 'Tie'
                        else:
                            result = None  # No pick
                        # Collect for weekly
                        if person not in all_weekly_results:
                            all_weekly_results[person] = {'wins': [], 'losses': [], 'ties': []}
                        if result == 'Win':
                            all_weekly_results[person]['wins'].append((week_num, 1))
                        elif result == 'Loss':
                            all_weekly_results[person]['losses'].append((week_num, 1))
                        elif result == 'Tie':
                            all_weekly_results[person]['ties'].append((week_num, 1))
        
        # Update weekly records in this sheet (A23-G26)
        win_row = 24  # 0-index 24 = row25
        loss_row = 25
        tie_row = 26
        df.iloc[22, 1:7] = people  # Ensure labels in B23-G23
        df.iloc[23, 0] = 'record'
        df.iloc[24, 0] = 'win'
        df.iloc[25, 0] = 'lose'
        df.iloc[26, 0] = 'tie'
        for i, person in enumerate(people):
            weekly_wins = sum([v for w, v in all_weekly_results.get(person, {'wins':[]})['wins'] if w == week_num])
            weekly_losses = sum([v for w, v in all_weekly_results.get(person, {'losses':[]})['losses'] if w == week_num])
            weekly_ties = sum([v for w, v in all_weekly_results.get(person, {'ties':[]})['ties'] if w == week_num])
            df.iloc[win_row, 1 + i] = weekly_wins
            df.iloc[loss_row, 1 + i] = weekly_losses
            df.iloc[tie_row, 1 + i] = weekly_ties
        
        # Write updated sheet back
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
    
    # Calculate cumulative
    cumulative_df = pd.DataFrame(columns=['Week'] + people)
    for week in range(1, len(xl.sheet_names) + 1):
        row = {'Week': week}
        for person in people:
            wins_up_to_week = sum([v for w, v in all_weekly_results.get(person, {'wins':[]})['wins'] if w <= week])
            losses_up_to_week = sum([v for w, v in all_weekly_results.get(person, {'losses':[]})['losses'] if w <= week])
            ties_up_to_week = sum([v for w, v in all_weekly_results.get(person, {'ties':[]})['ties'] if w <= week])
            total = wins_up_to_week + losses_up_to_week + ties_up_to_week
            win_pct = (wins_up_to_week / total * 100) if total > 0 else 0
            row[person] = f"{wins_up_to_week}-{losses_up_to_week}-{ties_up_to_week} ({win_pct:.2f}%)"
        cumulative_df = pd.concat([cumulative_df, pd.DataFrame([row])], ignore_index=True)
    
    # Write Cumulative sheet
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        cumulative_df.to_excel(writer, sheet_name='Cumulative', index=False)

# Run it
if __name__ == "__main__":
    update_picks()
    print("Excel updated! Check weekly records and 'Cumulative' sheet.")