import pandas as pd
import requests
import datetime
import sqlite3

# Connect to SQLite DB (creates if not exists, with thread safety)
conn = sqlite3.connect('picks.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables if not exist (one for picks per week, one for cumulative)
cursor.execute('''CREATE TABLE IF NOT EXISTS picks (
    week INTEGER, game_id INTEGER, away_team TEXT, home_team TEXT,
    bobby_pick TEXT, chet_pick TEXT, clyde_pick TEXT, henry_pick TEXT, riley_pick TEXT, nick_pick TEXT,
    actual_winner TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS cumulative (
    week INTEGER, bobby TEXT, chet TEXT, clyde TEXT, henry TEXT, riley TEXT, nick TEXT
)''')
conn.commit()

people = ['Bobby', 'Chet', 'Clyde', 'Henry', 'Riley', 'Nick']

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
                winner = 'Away' if away_score > home_score else 'Home' if home_score > away_score else 'Tie'
                games[game_key] = winner
            else:
                games[game_key] = None  # Not completed
        return games
    except Exception as e:
        print(f"API error: {e}. Using fallback if available.")
        if week == 1:
            return week1_fallback
        return {}

# Temporary: Import dummy data for testing (remove or comment out after first run; replace with your real Excel import)
def import_dummy_data():
    # Clear picks for re-test
    cursor.execute("DELETE FROM picks")
    conn.commit()
    # Example for Week 1 games (add all 16 with your actual picks as 'Away' or 'Home' based on 'x')
    games_week1 = [
        (1, 1, 'Dallas Cowboys', 'Philadelphia Eagles', 'Away', 'Home', 'Away', 'Home', 'Away', 'Home'),
        (1, 2, 'Kansas City Chiefs', 'Los Angeles Chargers', 'Home', 'Home', 'Away', 'Home', 'Away', 'Home'),
        (1, 3, 'Arizona Cardinals', 'New Orleans Saints', 'Away', 'Away', 'Away', 'Away', 'Away', 'Away'),
        (1, 4, 'Carolina Panthers', 'Jacksonville Jaguars', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home'),
        (1, 5, 'Cincinnati Bengals', 'Cleveland Browns', 'Away', 'Away', 'Away', 'Away', 'Away', 'Away'),
        (1, 6, 'Las Vegas Raiders', 'New England Patriots', 'Away', 'Away', 'Away', 'Away', 'Away', 'Away'),
        (1, 7, 'Miami Dolphins', 'Indianapolis Colts', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home'),
        (1, 8, 'New York Giants', 'Washington Commanders', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home'),
        (1, 9, 'Pittsburgh Steelers', 'New York Jets', 'Away', 'Away', 'Away', 'Away', 'Away', 'Away'),
        (1, 10, 'Tampa Bay Buccaneers', 'Atlanta Falcons', 'Away', 'Away', 'Away', 'Away', 'Away', 'Away'),
        (1, 11, 'San Francisco 49ers', 'Seattle Seahawks', 'Away', 'Away', 'Away', 'Away', 'Away', 'Away'),
        (1, 12, 'Tennessee Titans', 'Denver Broncos', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home'),
        (1, 13, 'Detroit Lions', 'Green Bay Packers', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home'),
        (1, 14, 'Houston Texans', 'Los Angeles Rams', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home'),
        (1, 15, 'Baltimore Ravens', 'Buffalo Bills', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home'),
        (1, 16, 'Minnesota Vikings', 'Chicago Bears', 'Away', 'Away', 'Away', 'Away', 'Away', 'Away'),
    ]
    for game in games_week1:
        cursor.execute("INSERT INTO picks (week, game_id, away_team, home_team, bobby_pick, chet_pick, clyde_pick, henry_pick, riley_pick, nick_pick) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", game)
    conn.commit()

import_dummy_data()  # Run once to populate; comment out after

def update_picks(week_num=None):
    weeks = range(1, 19) if not week_num else [week_num]
    all_weekly_results = {}
    for w in weeks:
        results = fetch_nfl_results(w)
        df = pd.read_sql_query(f"SELECT * FROM picks WHERE week = {w}", conn)
        for _, row in df.iterrows():
            game_key = f"{row['away_team']} @ {row['home_team']}"
            actual_winner = results.get(game_key)
            if actual_winner:
                cursor.execute(f"UPDATE picks SET actual_winner = ? WHERE week = ? AND game_id = ?", (actual_winner, w, row['game_id']))
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