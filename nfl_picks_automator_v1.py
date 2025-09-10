import pandas as pd
import requests
import datetime
import sqlite3

# Connect to SQLite DB (creates if not exists)
conn = sqlite3.connect('picks.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables if not exist (one for picks per week, one for cumulative)
cursor.execute('''CREATE TABLE IF NOT EXISTS picks (
    week INTEGER, game_id INTEGER, away_team TEXT, home_team TEXT,
    bobby_pick TEXT, chet_pick TEXT, clyde_pick TEXT, henry_pick TEXT, riley_pick TEXT, nick_pick TEXT,
    bobby_total_guess INTEGER, chet_total_guess INTEGER, clyde_total_guess INTEGER, 
    henry_total_guess INTEGER, riley_total_guess INTEGER, nick_total_guess INTEGER,
    actual_winner TEXT, actual_total_points INTEGER
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS cumulative (
    week INTEGER, bobby TEXT, chet TEXT, clyde TEXT, henry TEXT, riley TEXT, nick TEXT
)''')
conn.commit()

people = ['Bobby', 'Chet', 'Clyde', 'Henry', 'Riley', 'Nick']

# Hardcoded fallback for Week 1 2025 winners (if API fails)
week1_fallback = {
    "Dallas Cowboys @ Philadelphia Eagles": {'winner': 'Home', 'total_points': None},
    "Kansas City Chiefs @ Los Angeles Chargers": {'winner': 'Home', 'total_points': None},
    "Arizona Cardinals @ New Orleans Saints": {'winner': 'Away', 'total_points': None},
    "Carolina Panthers @ Jacksonville Jaguars": {'winner': 'Home', 'total_points': None},
    "Cincinnati Bengals @ Cleveland Browns": {'winner': 'Away', 'total_points': None},
    "Las Vegas Raiders @ New England Patriots": {'winner': 'Away', 'total_points': None},
    "Miami Dolphins @ Indianapolis Colts": {'winner': 'Home', 'total_points': None},
    "New York Giants @ Washington Commanders": {'winner': 'Home', 'total_points': None},
    "Pittsburgh Steelers @ New York Jets": {'winner': 'Away', 'total_points': None},
    "Tampa Bay Buccaneers @ Atlanta Falcons": {'winner': 'Away', 'total_points': None},
    "San Francisco 49ers @ Seattle Seahawks": {'winner': 'Away', 'total_points': None},
    "Tennessee Titans @ Denver Broncos": {'winner': 'Home', 'total_points': None},
    "Detroit Lions @ Green Bay Packers": {'winner': 'Home', 'total_points': None},
    "Houston Texans @ Los Angeles Rams": {'winner': 'Home', 'total_points': None},
    "Baltimore Ravens @ Buffalo Bills": {'winner': 'Home', 'total_points': None},
    "Minnesota Vikings @ Chicago Bears": {'winner': 'Away', 'total_points': 51}  # 27 + 24
}

def fetch_nfl_results(week, season=2025):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}"
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
            away_team = competition['competitors'][1]['team']['displayName'].strip().rstrip('¹').strip()
            home_team = competition['competitors'][0]['team']['displayName'].strip().rstrip('¹').strip()
            game_key = f"{away_team} @ {home_team}"
            status = competition['status']['type']['completed']
            if status:
                away_score = int(competition['competitors'][1]['score'])
                home_score = int(competition['competitors'][0]['score'])
                total_points = away_score + home_score
                winner = 'Away' if away_score > home_score else 'Home' if home_score > away_score else 'Tie'
                games[game_key] = {'winner': winner, 'total_points': total_points}
            else:
                games[game_key] = {'winner': None, 'total_points': None}  # Not completed
        return games
    except Exception as e:
        print(f"API error: {e}. Using fallback if available.")
        if week == 1:
            return week1_fallback
        return {}

def import_from_excel(file_path='nfl_picks_2025.xlsx'):
    # Clear picks for re-import
    cursor.execute("DELETE FROM picks")
    conn.commit()
    xl = pd.ExcelFile(file_path)
    for sheet_name in xl.sheet_names:
        if not sheet_name.startswith('Sheet'):
            continue
        week_num = int(sheet_name.replace('Sheet', ''))
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        
        # Get tiebreaker predictions from row 19 (B19-G19)
        tiebreaker_guesses = []
        for i in range(6):  # Bobby through Nick (columns B-G, which are 1-6)
            guess = df.iloc[18, 1 + i]  # Row 19 is index 18, columns B-G are 1-6
            if pd.notna(guess) and str(guess).strip().isdigit():
                tiebreaker_guesses.append(int(guess))
            else:
                tiebreaker_guesses.append(None)
        
        # Find all games first to identify the last one
        games = []
        for row_idx in range(2, 22):  # Rows 3-22
            if pd.notna(df.iloc[row_idx, 7]) and pd.notna(df.iloc[row_idx, 9]):
                away_team = str(df.iloc[row_idx, 7]).strip().rstrip('¹').strip()
                home_team = str(df.iloc[row_idx, 9]).strip().rstrip('¹').strip()
                pick_values = []
                for i in range(6):
                    away_pick = str(df.iloc[row_idx, 1 + i]).strip().lower()
                    home_pick = str(df.iloc[row_idx, 10 + i]).strip().lower()
                    if away_pick == 'x':
                        pick_values.append('Away')
                    elif home_pick == 'x':
                        pick_values.append('Home')
                    else:
                        pick_values.append(None)
                games.append((away_team, home_team, pick_values))
        
        # Now insert games with tiebreaker data for the last game
        game_id = 1
        for away_team, home_team, pick_values in games:
            # Add tiebreaker guesses only for the last game of the week
            is_last_game = (game_id == len(games))
            total_guesses = tiebreaker_guesses if is_last_game else [None] * 6
            
            cursor.execute('''INSERT INTO picks (week, game_id, away_team, home_team, bobby_pick, chet_pick, clyde_pick, henry_pick, riley_pick, nick_pick, bobby_total_guess, chet_total_guess, clyde_total_guess, henry_total_guess, riley_total_guess, nick_total_guess)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (week_num, game_id, away_team, home_team, *pick_values, *total_guesses))
            conn.commit()
            game_id += 1

#import_from_excel()  # Run to import real picks; comment out after

def update_picks(week_num=None):
    weeks = range(1, 19) if not week_num else [week_num]
    all_weekly_results = {}
    for w in weeks:
        results = fetch_nfl_results(w)
        df = pd.read_sql_query(f"SELECT * FROM picks WHERE week = {w}", conn)
        for _, row in df.iterrows():
            game_key = f"{row['away_team']} @ {row['home_team']}"
            game_result = results.get(game_key)
            if game_result and game_result['winner']:
                actual_winner = game_result['winner']
                actual_total = game_result['total_points']
                cursor.execute(f"UPDATE picks SET actual_winner = ?, actual_total_points = ? WHERE week = ? AND game_id = ?", 
                             (actual_winner, actual_total, w, row['game_id']))
                conn.commit()
                for person in people:
                    picked = row[f'{person.lower()}_pick']
                    if picked:
                        result = 'Win' if picked == actual_winner else 'Loss' if actual_winner != 'Tie' else 'Tie'
                        if person not in all_weekly_results:
                            all_weekly_results[person] = {'wins': [], 'losses': [], 'ties': []}
                        if result == 'Win':
                            all_weekly_results[person]['wins'].append((w, 1))
                        elif result == 'Loss':
                            all_weekly_results[person]['losses'].append((w, 1))
                        elif result == 'Tie':
                            all_weekly_results[person]['ties'].append((w, 1))
    cumulative_df = pd.DataFrame(columns=['week'] + [p.lower() for p in people])
    for week in range(1, 19):
        row = {'week': week}
        for person in people:
            wins_up_to_week = sum(v for w, v in all_weekly_results.get(person, {'wins':[]})['wins'] if w <= week)
            losses_up_to_week = sum(v for w, v in all_weekly_results.get(person, {'losses':[]})['losses'] if w <= week)
            ties_up_to_week = sum(v for w, v in all_weekly_results.get(person, {'ties':[]})['ties'] if w <= week)
            total = wins_up_to_week + losses_up_to_week + ties_up_to_week
            win_pct = (wins_up_to_week / total * 100) if total > 0 else 0
            row[person.lower()] = f"{wins_up_to_week}-{losses_up_to_week}-{ties_up_to_week} ({win_pct:.2f}%)"
        cumulative_df = pd.concat([cumulative_df, pd.DataFrame([row])], ignore_index=True)
    cumulative_df.to_sql('cumulative', conn, if_exists='replace', index=False)

if __name__ == "__main__":
    update_picks()
    print("DB updated!")