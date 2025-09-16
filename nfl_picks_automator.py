# Enhanced nfl_picks_automator.py with individual game scores
import requests
import sqlite3
import pandas as pd
from datetime import datetime
import re

def get_game_scores_from_web(week, year=2025):
    """
    Fetch individual game scores from ESPN or similar API
    Returns dict with game details including individual team scores
    """
    try:
        # ESPN API endpoint for NFL scores
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        params = {
            'week': week,
            'seasontype': 2,  # Regular season
            'year': year
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for event in data.get('events', []):
            competition = event.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) >= 2:
                # Get team info
                away_team = competitors[1]  # Usually index 1 is away
                home_team = competitors[0]  # Usually index 0 is home
                
                game_info = {
                    'away_team': away_team['team']['displayName'],
                    'home_team': home_team['team']['displayName'],
                    'away_score': int(away_team.get('score', 0)) if away_team.get('score') else None,
                    'home_score': int(home_team.get('score', 0)) if home_team.get('score') else None,
                    'status': competition.get('status', {}).get('type', {}).get('name', 'Unknown'),
                    'completed': competition.get('status', {}).get('type', {}).get('completed', False)
                }
                
                # Determine winner
                if game_info['completed'] and game_info['away_score'] is not None and game_info['home_score'] is not None:
                    if game_info['away_score'] > game_info['home_score']:
                        game_info['winner'] = 'Away'
                        game_info['actual_winner'] = game_info['away_team']
                    elif game_info['home_score'] > game_info['away_score']:
                        game_info['winner'] = 'Home'
                        game_info['actual_winner'] = game_info['home_team']
                    else:
                        game_info['winner'] = 'Tie'
                        game_info['actual_winner'] = 'Tie'
                    
                    game_info['total_points'] = game_info['away_score'] + game_info['home_score']
                
                games.append(game_info)
        
        return games
    
    except Exception as e:
        print(f"Error fetching scores from ESPN: {e}")
        return []

def update_database_with_scores():
    """
    Enhanced function to update database with individual game scores
    """
    conn = sqlite3.connect('picks.db')
    cursor = conn.cursor()
    
    # Add new columns for individual scores if they don't exist
    try:
        cursor.execute("ALTER TABLE picks ADD COLUMN away_score INTEGER")
        cursor.execute("ALTER TABLE picks ADD COLUMN home_score INTEGER")
        print("Added score columns to database")
    except sqlite3.OperationalError:
        # Columns already exist
        pass
    
    # Get all weeks that have games
    cursor.execute("SELECT DISTINCT week FROM picks ORDER BY week")
    weeks = cursor.fetchall()
    
    for (week,) in weeks:
        print(f"Updating scores for Week {week}...")
        
        # Get scores from web
        game_scores = get_game_scores_from_web(week)
        
        if not game_scores:
            print(f"No scores found for Week {week}")
            continue
        
        # Update each game in the database
        for game in game_scores:
            if game.get('completed'):
                # Find matching game in database
                cursor.execute("""
                    UPDATE picks 
                    SET away_score = ?, home_score = ?, actual_winner = ?, actual_total_points = ?
                    WHERE week = ? AND away_team = ? AND home_team = ?
                """, (
                    game['away_score'],
                    game['home_score'], 
                    game['winner'],
                    game['total_points'],
                    week,
                    game['away_team'],
                    game['home_team']
                ))
                
                if cursor.rowcount > 0:
                    print(f"Updated: {game['away_team']} {game['away_score']} - {game['home_score']} {game['home_team']}")
    
    conn.commit()
    conn.close()
    print("Database update complete!")

# You would call this function instead of or in addition to your existing update_picks()
if __name__ == "__main__":
    update_database_with_scores()