import dash
from dash import dcc, html, Input, Output, dash_table, State
import dash_bootstrap_components as dbc
import pandas as pd
import sqlite3
import base64
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import io

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("NFL Picks Tracker", className="text-center mb-4 text-primary"),
            html.Hr()
        ], width=12)
    ]),
    
    # Upload Controls
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Upload New Picks"),
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-picks',
                        children=dbc.Button("Upload Excel File", color="primary", size="lg"),
                        multiple=False,
                        accept='.xlsx,.xlsm'
                    ),
                    html.Div(id='upload-status', className="mt-3")
                ])
            ], className="mb-4")
        ], width=12, md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Manual Data Entry"),
                dbc.CardBody([
                    dbc.Button("Enter Picks Manually", id='manual-entry-btn', color='info', size="lg", className="w-100 mb-2"),
                    dbc.Button("Update Results", id='update-btn', color='success', size="lg", className="w-100"),
                    html.Div(id='update-status', className="mt-3")
                ])
            ], className="mb-4")
        ], width=12, md=6)
    ]),
    
    # Manual Entry Modal
    dbc.Modal([
        dbc.ModalHeader("Manual Pick Entry"),
        dbc.ModalBody([
            html.Div(id='manual-entry-form')
        ]),
        dbc.ModalFooter([
            dbc.Button("Close", id="close-modal", className="ms-auto", n_clicks=0)
        ])
    ], id="manual-entry-modal", size="lg"),
    
    # Main Content with Statistics Dashboard added
    dbc.Tabs([
        dbc.Tab(label="Leaderboard", tab_id="leaderboard"),
        dbc.Tab(label="Weekly Records", tab_id="weekly_records"),
        dbc.Tab(label="Weekly Picks", tab_id="weekly_picks"),
        dbc.Tab(label="Statistics Dashboard", tab_id="stats_dashboard")
    ], id="main-tabs", active_tab="leaderboard", className="mb-4"),
    
    html.Div(id="tab-content")
], fluid=True)

# Database helper functions
def init_database():
    """Initialize the database with required tables"""
    try:
        conn = sqlite3.connect('picks.db')
        cursor = conn.cursor()
        
        # Create picks table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS picks (
                game_id INTEGER PRIMARY KEY,
                week INTEGER,
                away_team TEXT,
                home_team TEXT,
                bobby_pick TEXT,
                chet_pick TEXT,
                clyde_pick TEXT,
                henry_pick TEXT,
                nick_pick TEXT,
                riley_pick TEXT,
                actual_winner TEXT,
                game_date TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

def get_db_connection():
    try:
        # Initialize database if needed
        if not os.path.exists('picks.db'):
            init_database()
        
        conn = sqlite3.connect('picks.db', check_same_thread=False, timeout=30)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def process_excel_file(contents, filename):
    """Process uploaded Excel file and import to database - Custom format for NFL picks"""
    try:
        # Decode the uploaded file
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Read Excel file with openpyxl engine
        excel_file = io.BytesIO(decoded)
        
        # Get all sheet names
        xl_file = pd.ExcelFile(excel_file)
        sheet_names = xl_file.sheet_names
        
        # Connect to database
        conn = get_db_connection()
        if not conn:
            return "Database connection failed", False
        
        total_games = 0
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        
        # Process each sheet (week)
        for sheet_name in sheet_names:
            # Skip the cumulative sheet
            if sheet_name.lower() == 'cumulative':
                continue
                
            try:
                # Determine week number from sheet name
                if sheet_name.lower().startswith('sheet'):
                    week_num = int(sheet_name.replace('Sheet', '').replace('sheet', ''))
                else:
                    continue
                
                # Read the sheet without headers
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                
                # Clear existing data for this week
                conn.execute("DELETE FROM picks WHERE week = ?", (week_num,))
                
                # Process each row that has game data
                for idx, row in df.iterrows():
                    # Skip header rows and empty rows
                    if idx < 2 or pd.isna(row.iloc[7]) or pd.isna(row.iloc[9]):
                        continue
                    
                    # Extract team names (columns 7 and 9)
                    away_team = str(row.iloc[7]).strip()
                    home_team = str(row.iloc[9]).strip()
                    
                    # Skip if team names are invalid
                    if not away_team or not home_team or away_team == 'nan' or home_team == 'nan':
                        continue
                    
                    # Clean team names (remove extra characters)
                    away_team = away_team.replace(' ¹', '').replace(' ²', '').replace(' ³', '')
                    home_team = home_team.replace(' ¹', '').replace(' ²', '').replace(' ³', '')
                    
                    # Determine each person's pick
                    picks = {}
                    for i, person in enumerate(people):
                        # Check away team pick (columns 1-6)
                        away_pick = row.iloc[i + 1] if i + 1 < len(row) else None
                        # Check home team pick (columns 10-15)  
                        home_pick = row.iloc[i + 10] if i + 10 < len(row) else None
                        
                        # Determine final pick
                        if pd.notna(away_pick) and str(away_pick).strip().lower() == 'x':
                            picks[f'{person}_pick'] = away_team
                        elif pd.notna(home_pick) and str(home_pick).strip().lower() == 'x':
                            picks[f'{person}_pick'] = home_team
                        else:
                            picks[f'{person}_pick'] = None
                    
                    # Insert into database
                    conn.execute('''
                        INSERT INTO picks (week, away_team, home_team, bobby_pick, chet_pick, 
                                         clyde_pick, henry_pick, riley_pick, nick_pick)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        week_num, away_team, home_team,
                        picks.get('bobby_pick'), picks.get('chet_pick'), picks.get('clyde_pick'),
                        picks.get('henry_pick'), picks.get('riley_pick'), picks.get('nick_pick')
                    ))
                    
                    total_games += 1
                    
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        if total_games == 0:
            return "No valid games found in the Excel file", False
        
        return f"Successfully imported {total_games} games from {len([s for s in sheet_names if s.lower() != 'cumulative'])} weeks", True
        
    except Exception as e:
        return f"Error processing file: {str(e)}", False

def update_results_from_api():
    """Update game results from ESPN API"""
    try:
        import requests
        import json
        
        conn = get_db_connection()
        if not conn:
            return "Database connection failed", False
        
        # Get current season (2025)
        current_year = 2025
        updated_games = 0
        
        # Check each week for completed games
        for week in range(1, 19):  # Weeks 1-18
            try:
                # ESPN API endpoint for NFL scoreboard
                url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}&dates={current_year}"
                
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    continue
                
                data = response.json()
                
                # Process each game in the week
                if 'events' in data:
                    for game in data['events']:
                        try:
                            # Extract game information
                            if 'competitions' not in game or not game['competitions']:
                                continue
                            
                            competition = game['competitions'][0]
                            
                            # Check if game is completed
                            status = competition.get('status', {})
                            if status.get('type', {}).get('name') != 'STATUS_FINAL':
                                continue  # Skip if game not finished
                            
                            # Get team information
                            competitors = competition.get('competitors', [])
                            if len(competitors) != 2:
                                continue
                            
                            # Determine home and away teams
                            home_team = None
                            away_team = None
                            home_score = 0
                            away_score = 0
                            
                            for team in competitors:
                                team_name = team.get('team', {}).get('displayName', '')
                                team_score = int(team.get('score', 0))
                                
                                if team.get('homeAway') == 'home':
                                    home_team = team_name
                                    home_score = team_score
                                else:
                                    away_team = team_name
                                    away_score = team_score
                            
                            if not home_team or not away_team:
                                continue
                            
                            # Determine winner
                            if home_score > away_score:
                                winner = home_team
                            elif away_score > home_score:
                                winner = away_team
                            else:
                                winner = "TIE"  # Handle ties (rare in NFL)
                            
                            # Clean team names to match your database format
                            home_team_clean = clean_team_name(home_team)
                            away_team_clean = clean_team_name(away_team)
                            winner_clean = clean_team_name(winner) if winner != "TIE" else "TIE"
                            
                            # Update database - find matching games
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE picks 
                                SET actual_winner = ? 
                                WHERE week = ? 
                                AND (
                                    (LOWER(away_team) LIKE ? AND LOWER(home_team) LIKE ?) OR
                                    (LOWER(away_team) LIKE ? AND LOWER(home_team) LIKE ?)
                                )
                                AND actual_winner IS NULL
                            ''', (
                                winner_clean,
                                week,
                                f'%{away_team_clean.lower()}%',
                                f'%{home_team_clean.lower()}%',
                                f'%{home_team_clean.lower()}%',
                                f'%{away_team_clean.lower()}%'
                            ))
                            
                            if cursor.rowcount > 0:
                                updated_games += cursor.rowcount
                                
                        except Exception as e:
                            print(f"Error processing game: {e}")
                            continue
                            
            except Exception as e:
                print(f"Error processing week {week}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        if updated_games > 0:
            return f"Successfully updated {updated_games} games with results!", True
        else:
            return "No new completed games found to update.", True
            
    except Exception as e:
        return f"Update failed: {str(e)}", False

def clean_team_name(team_name):
    """Clean team names to match database format"""
    if not team_name or team_name == "TIE":
        return team_name
    
    # Common team name mappings
    name_mappings = {
        'Arizona Cardinals': 'Arizona Cardinals',
        'Atlanta Falcons': 'Atlanta Falcons', 
        'Baltimore Ravens': 'Baltimore Ravens',
        'Buffalo Bills': 'Buffalo Bills',
        'Carolina Panthers': 'Carolina Panthers',
        'Chicago Bears': 'Chicago Bears',
        'Cincinnati Bengals': 'Cincinnati Bengals',
        'Cleveland Browns': 'Cleveland Browns',
        'Dallas Cowboys': 'Dallas Cowboys',
        'Denver Broncos': 'Denver Broncos',
        'Detroit Lions': 'Detroit Lions',
        'Green Bay Packers': 'Green Bay Packers',
        'Houston Texans': 'Houston Texans',
        'Indianapolis Colts': 'Indianapolis Colts',
        'Jacksonville Jaguars': 'Jacksonville Jaguars',
        'Kansas City Chiefs': 'Kansas City Chiefs',
        'Las Vegas Raiders': 'Las Vegas Raiders',
        'Los Angeles Chargers': 'Los Angeles Chargers',
        'Los Angeles Rams': 'Los Angeles Rams',
        'Miami Dolphins': 'Miami Dolphins',
        'Minnesota Vikings': 'Minnesota Vikings',
        'New England Patriots': 'New England Patriots',
        'New Orleans Saints': 'New Orleans Saints',
        'New York Giants': 'New York Giants',
        'New York Jets': 'New York Jets',
        'Philadelphia Eagles': 'Philadelphia Eagles',
        'Pittsburgh Steelers': 'Pittsburgh Steelers',
        'San Francisco 49ers': 'San Francisco 49ers',
        'Seattle Seahawks': 'Seattle Seahawks',
        'Tampa Bay Buccaneers': 'Tampa Bay Buccaneers',
        'Tennessee Titans': 'Tennessee Titans',
        'Washington Commanders': 'Washington Commanders'
    }
    
    # Try exact match first
    if team_name in name_mappings:
        return name_mappings[team_name]
    
    # Try partial matches for common variations
    team_lower = team_name.lower()
    for full_name, clean_name in name_mappings.items():
        if full_name.lower() in team_lower or any(word in team_lower for word in full_name.lower().split()):
            return clean_name
    
    # Return original if no match found
    return team_name

# Upload callback
@app.callback(
    Output('upload-status', 'children'),
    Input('upload-picks', 'contents'),
    State('upload-picks', 'filename')
)
def upload_file(contents, filename):
    if contents is None:
        return ""
    
    try:
        message, success = process_excel_file(contents, filename)
        color = "success" if success else "danger"
        return dbc.Alert(message, color=color, dismissable=True)
        
    except Exception as e:
        return dbc.Alert(f"Upload error: {str(e)}", color="danger", dismissable=True)

# Manual entry modal callback
@app.callback(
    Output("manual-entry-modal", "is_open"),
    Output('manual-entry-form', 'children'),
    [Input("manual-entry-btn", "n_clicks"), Input("close-modal", "n_clicks")],
    [State("manual-entry-modal", "is_open")]
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        form_content = create_manual_entry_form() if not is_open else []
        return not is_open, form_content
    return is_open, []

def create_manual_entry_form():
    """Create form for manual data entry"""
    return [
        dbc.Row([
            dbc.Col([
                dbc.Label("Week"),
                dbc.Input(id="manual-week", type="number", min=1, max=18, value=1)
            ], width=6),
            dbc.Col([
                dbc.Label("Game Date"),
                dbc.Input(id="manual-date", type="date")
            ], width=6)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Label("Away Team"),
                dbc.Input(id="manual-away-team", placeholder="e.g., Chiefs")
            ], width=6),
            dbc.Col([
                dbc.Label("Home Team"),
                dbc.Input(id="manual-home-team", placeholder="e.g., Bills")
            ], width=6)
        ], className="mb-3"),
        
        html.H5("Picks", className="mb-2"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Bobby"),
                dbc.Select(id="manual-bobby", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4),
            dbc.Col([
                dbc.Label("Chet"),
                dbc.Select(id="manual-chet", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4),
            dbc.Col([
                dbc.Label("Clyde"),
                dbc.Select(id="manual-clyde", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4)
        ], className="mb-2"),
        
        dbc.Row([
            dbc.Col([
                dbc.Label("Henry"),
                dbc.Select(id="manual-henry", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4),
            dbc.Col([
                dbc.Label("Nick"),
                dbc.Select(id="manual-nick", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4),
            dbc.Col([
                dbc.Label("Riley"),
                dbc.Select(id="manual-riley", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Label("Actual Winner (if known)"),
                dbc.Select(id="manual-winner", options=[
                    {"label": "Not decided yet", "value": ""},
                    {"label": "Away Team", "value": "away"},
                    {"label": "Home Team", "value": "home"}
                ])
            ], width=6)
        ], className="mb-3"),
        
        dbc.Button("Add Game", id="add-game-btn", color="primary")
    ]

# Update callback
@app.callback(
    Output('update-status', 'children'),
    Input('update-btn', 'n_clicks')
)
def update_status(n_clicks):
    if not n_clicks:
        return ""
    
    try:
        message, success = update_results_from_api()
        color = "success" if success else "warning"
        return dbc.Alert(message, color=color, dismissable=True)
    except Exception as e:
        return dbc.Alert(f"Update failed: {str(e)}", color="danger", dismissable=True)

# Main tab callback
@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "active_tab")
)
def render_tab_content(active_tab):
    if active_tab == "leaderboard":
        return render_leaderboard_tab()
    elif active_tab == "weekly_records":
        return render_weekly_records_tab()
    elif active_tab == "weekly_picks":
        return render_weekly_picks_tab()
    elif active_tab == "stats_dashboard":
        return render_stats_dashboard_tab()

# Helper function to get standings
def get_current_standings():
    try:
        conn = get_db_connection()
        if not conn:
            return pd.DataFrame()
        
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
        standings = []
        
        for person in people:
            person_pick_col = f'{person}_pick'
            person_picks = df[df[person_pick_col].notna()]
            
            wins = 0
            total_games = len(person_picks)
            
            for _, row in person_picks.iterrows():
                # Convert picks to team names for comparison
                if row[person_pick_col] == 'away':
                    person_team_pick = row['away_team']
                elif row[person_pick_col] == 'home':
                    person_team_pick = row['home_team']
                else:
                    person_team_pick = row[person_pick_col]
                
                # Convert actual winner
                if row['actual_winner'] == 'away':
                    actual_team_winner = row['away_team']
                elif row['actual_winner'] == 'home':
                    actual_team_winner = row['home_team']
                else:
                    actual_team_winner = row['actual_winner']
                
                if person_team_pick == actual_team_winner:
                    wins += 1
            
            losses = total_games - wins
            win_pct = (wins / total_games * 100) if total_games > 0 else 0
            
            standings.append({
                'Rank': 0,
                'Player': person.title(),
                'Wins': wins,
                'Losses': losses,
                'Total': total_games,
                'Win %': f"{win_pct:.1f}%"
            })
        
        standings_df = pd.DataFrame(standings)
        standings_df = standings_df.sort_values('Wins', ascending=False)
        standings_df['Rank'] = range(1, len(standings_df) + 1)
        
        return standings_df
        
    except Exception as e:
        print(f"Error getting standings: {e}")
        return pd.DataFrame()

# Enhanced Leaderboard tab with charts
def render_leaderboard_tab():
    standings_df = get_current_standings()
    
    if standings_df.empty:
        return dbc.Alert("No game results available. Upload picks and update results first.", color="info")
    
    # Create charts
    win_pct_chart = create_win_percentage_chart(standings_df)
    wins_chart = create_wins_comparison_chart(standings_df)
    
    # Create podium visualization for top 3
    top_3 = standings_df.head(3)
    
    podium_cards = []
    medals = ["🥇", "🥈", "🥉"]
    colors = ["warning", "secondary", "dark"]
    
    for i, (_, player) in enumerate(top_3.iterrows()):
        podium_cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H2(medals[i], className="text-center mb-2"),
                        html.H4(player['Player'], className="text-center mb-2"),
                        html.H5(f"{player['Wins']}-{player['Losses']}", className="text-center mb-1"),
                        html.P(player['Win %'], className="text-center text-muted mb-0")
                    ], className="py-4")
                ], color=colors[i], outline=True, className="h-100")
            ], width=12, md=4)
        )
    
    return [
        # Championship Podium
        dbc.Row([
            dbc.Col([
                html.H3("🏆 Championship Podium", className="text-center mb-4")
            ], width=12)
        ]),
        dbc.Row(podium_cards, className="mb-5"),
        
        # Charts row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 Win Percentage Comparison"),
                    dbc.CardBody([
                        dcc.Graph(figure=win_pct_chart, style={'height': '400px'})
                    ])
                ])
            ], width=12, lg=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🏆 Total Wins Comparison"),
                    dbc.CardBody([
                        dcc.Graph(figure=wins_chart, style={'height': '400px'})
                    ])
                ])
            ], width=12, lg=6)
        ], className="mb-4"),
        
        # Original standings table
        dbc.Card([
            dbc.CardHeader("Complete Standings"),
            dbc.CardBody([
                dash_table.DataTable(
                    data=standings_df.to_dict('records'),
                    columns=[
                        {"name": "Rank", "id": "Rank"},
                        {"name": "Player", "id": "Player"},
                        {"name": "Wins", "id": "Wins"},
                        {"name": "Losses", "id": "Losses"},
                        {"name": "Total", "id": "Total"},
                        {"name": "Win %", "id": "Win %"}
                    ],
                    style_cell={'textAlign': 'center', 'padding': '12px'},
                    style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 0},
                            'backgroundColor': '#fff3cd',
                            'color': '#856404',
                            'fontWeight': 'bold'
                        }
                    ]
                )
            ])
        ])
    ]

def create_win_percentage_chart(standings_df):
    """Create a horizontal bar chart showing win percentages"""
    # Extract numeric values from percentage strings
    win_percentages = [float(pct.rstrip('%')) for pct in standings_df['Win %']]
    
    fig = px.bar(
        standings_df.sort_values('Wins', ascending=True),
        x=sorted(win_percentages),
        y=standings_df.sort_values('Wins', ascending=True)['Player'],
        orientation='h',
        title='Win Percentage by Player',
        text=standings_df.sort_values('Wins', ascending=True)['Win %'],
        color=sorted(win_percentages),
        color_continuous_scale='RdYlGn'
    )
    
    fig.update_traces(textposition='inside')
    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),
        font=dict(size=12),
        coloraxis_showscale=False
    )
    fig.update_xaxes(title='Win Percentage (%)')
    fig.update_yaxes(title='')
    
    return fig

def create_wins_comparison_chart(standings_df):
    """Create a stacked bar chart comparing total wins and losses"""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=standings_df['Player'],
        y=standings_df['Wins'],
        name='Wins',
        marker_color='lightgreen',
        text=standings_df['Wins'],
        textposition='auto'
    ))
    
    fig.add_trace(go.Bar(
        x=standings_df['Player'],
        y=standings_df['Losses'],
        name='Losses',
        marker_color='lightcoral',
        text=standings_df['Losses'],
        textposition='auto'
    ))
    
    fig.update_layout(
        title='Wins vs Losses by Player',
        barmode='stack',
        margin=dict(l=0, r=0, t=40, b=0),
        font=dict(size=12)
    )
    fig.update_xaxes(title='Player')
    fig.update_yaxes(title='Games')
    
    return fig

# Weekly Picks Tab - NEW
def render_weekly_picks_tab():
    """Show all picks by week with color coding for correct/incorrect"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")
        
        df = pd.read_sql_query("SELECT * FROM picks ORDER BY week, game_id", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No picks data available.", color="info")
        
        # Get available weeks
        weeks = sorted(df['week'].unique())
        
        # Create dropdown for week selection
        week_options = [{"label": f"Week {week}", "value": week} for week in weeks]
        
        return [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Select Week to View Picks"),
                        dbc.CardBody([
                            dcc.Dropdown(
                                id='week-selector',
                                options=week_options,
                                value=weeks[0] if weeks else None,
                                placeholder="Select a week"
                            )
                        ])
                    ])
                ], width=12, md=4)
            ], className="mb-4"),
            
            html.Div(id='weekly-picks-content')
        ]
        
    except Exception as e:
        return dbc.Alert(f"Error loading weekly picks: {str(e)}", color="danger")

# Add callback for weekly picks
@app.callback(
    Output('weekly-picks-content', 'children'),
    Input('week-selector', 'value')
)
def update_weekly_picks_content(selected_week):
    if not selected_week:
        return dbc.Alert("Please select a week to view picks.", color="info")
    
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database connection failed.", color="danger")
        
        # Get picks for selected week
        df = pd.read_sql_query(
            "SELECT * FROM picks WHERE week = ? ORDER BY game_id", 
            conn, 
            params=(selected_week,)
        )
        conn.close()
        
        if df.empty:
            return dbc.Alert(f"No games found for Week {selected_week}.", color="info")
        
        # Create picks table data
        picks_data = []
        people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
        
        for _, row in df.iterrows():
            game_info = f"{row['away_team']} @ {row['home_team']}"
            
            pick_row = {
                'Game': game_info,
                'Result': row['actual_winner'] if pd.notna(row['actual_winner']) else 'TBD'
            }
            
            # Add each person's pick
            for person in people:
                person_pick_col = f'{person}_pick'
                pick_row[person.title()] = row[person_pick_col] if pd.notna(row[person_pick_col]) else '-'
            
            picks_data.append(pick_row)
        
        # Create the data table
        columns = [{"name": "Game", "id": "Game"}, {"name": "Winner", "id": "Result"}]
        columns.extend([{"name": person.title(), "id": person.title()} for person in people])
        
        # Create conditional styling for correct/incorrect picks
        style_data_conditional = []
        
        # Add styling for each person's column
        for person in people:
            person_title = person.title()
            
            # Correct picks - green background
            style_data_conditional.append({
                'if': {
                    'filter_query': f'{{{person_title}}} = {{Result}}',
                    'column_id': person_title
                },
                'backgroundColor': '#d4edda',
                'color': '#155724',
                'fontWeight': 'bold'
            })
            
            # Check for incorrect picks (when Result is not TBD and pick doesn't match)
            for _, row in df.iterrows():
                if pd.notna(row['actual_winner']) and row['actual_winner'] != 'TBD':
                    person_pick = row[f'{person}_pick']
                    if pd.notna(person_pick) and person_pick != row['actual_winner']:
                        # We'll handle this with a broader condition below
                        pass
        
        # Add incorrect picks styling - this is a bit complex due to DataTable limitations
        # We'll use a different approach - row index based conditions
        for i, row_data in enumerate(picks_data):
            if row_data['Result'] != 'TBD':
                for person in people:
                    person_title = person.title()
                    if (row_data[person_title] != '-' and 
                        row_data[person_title] != row_data['Result'] and
                        row_data['Result'] != 'TBD'):
                        style_data_conditional.append({
                            'if': {
                                'row_index': i,
                                'column_id': person_title
                            },
                            'backgroundColor': '#f8d7da',
                            'color': '#721c24',
                            'fontWeight': 'bold'
                        })
        
        return [
            dbc.Card([
                dbc.CardHeader(f"Week {selected_week} Picks & Results"),
                dbc.CardBody([
                    dbc.Alert([
                        html.Strong("Legend: "),
                        html.Span("Green = Correct Pick", style={'color': '#155724', 'backgroundColor': '#d4edda', 'padding': '2px 8px', 'marginRight': '10px', 'borderRadius': '3px'}),
                        html.Span("Red = Incorrect Pick", style={'color': '#721c24', 'backgroundColor': '#f8d7da', 'padding': '2px 8px', 'borderRadius': '3px'})
                    ], color="light", className="mb-3"),
                    
                    dash_table.DataTable(
                        data=picks_data,
                        columns=columns,
                        style_cell={
                            'textAlign': 'center',
                            'padding': '12px',
                            'fontFamily': 'Arial, sans-serif',
                            'fontSize': '13px',
                            'whiteSpace': 'normal',
                            'height': 'auto'
                        },
                        style_header={
                            'backgroundColor': '#6f42c1',
                            'color': 'white',
                            'fontWeight': 'bold'
                        },
                        style_data_conditional=style_data_conditional,
                        style_table={'overflowX': 'auto'},
                        page_size=20
                    )
                ])
            ])
        ]
        
    except Exception as e:
        return dbc.Alert(f"Error loading picks for week {selected_week}: {str(e)}", color="danger")
def render_weekly_records_tab():
    try:
        weekly_df = get_weekly_records_data()
        
        if weekly_df.empty:
            return dbc.Alert("No completed games available for weekly records.", color="info")
        
        # Create a chart showing weekly performance trends
        weekly_chart = create_weekly_trends_chart()
        
        return [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Weekly Performance Trends"),
                        dbc.CardBody([
                            dcc.Graph(figure=weekly_chart, style={'height': '400px'})
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4("Weekly Records", className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Alert([
                                html.Strong("Format: "),
                                "Wins-Losses (Win Percentage) for each week"
                            ], color="info", className="mb-3"),
                            
                            dash_table.DataTable(
                                data=weekly_df.to_dict('records'),
                                columns=[{"name": col, "id": col} for col in weekly_df.columns],
                                style_cell={
                                    'textAlign': 'center',
                                    'padding': '12px',
                                    'fontFamily': 'Arial, sans-serif',
                                    'fontSize': '13px',
                                    'minWidth': '100px'
                                },
                                style_header={
                                    'backgroundColor': '#17a2b8',
                                    'color': 'white',
                                    'fontWeight': 'bold'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'row_index': 'odd'},
                                        'backgroundColor': '#f8f9fa'
                                    },
                                    {
                                        'if': {
                                            'filter_query': '{Week} = TOTALS',
                                            'column_id': 'Week'
                                        },
                                        'backgroundColor': '#343a40',
                                        'color': 'white',
                                        'fontWeight': 'bold'
                                    },
                                    {
                                        'if': {
                                            'filter_query': '{Week} = TOTALS'
                                        },
                                        'backgroundColor': '#343a40',
                                        'color': 'white',
                                        'fontWeight': 'bold'
                                    }
                                ],
                                style_table={'overflowX': 'auto'},
                                page_size=20
                            )
                        ])
                    ])
                ], width=12)
            ])
        ]
        
    except Exception as e:
        return dbc.Alert(f"Error loading weekly records: {str(e)}", color="danger")

def get_weekly_records_data():
    """Get weekly records data with totals row"""
    try:
        conn = get_db_connection()
        if not conn:
            return pd.DataFrame()
        
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
        weeks = sorted(df['week'].unique())
        
        weekly_records = []
        totals = {'Week': 'TOTALS'}
        
        for week in weeks:
            week_df = df[df['week'] == week]
            week_record = {'Week': f"Week {week}"}
            
            for person in people:
                person_pick_col = f'{person}_pick'
                person_week_picks = week_df[week_df[person_pick_col].notna()]
                
                if len(person_week_picks) > 0:
                    wins = 0
                    for _, row in person_week_picks.iterrows():
                        # Handle pick comparison
                        if row[person_pick_col] == 'away':
                            person_team_pick = row['away_team']
                        elif row[person_pick_col] == 'home':
                            person_team_pick = row['home_team']
                        else:
                            person_team_pick = row[person_pick_col]
                        
                        # Handle actual winner
                        if row['actual_winner'] == 'away':
                            actual_team_winner = row['away_team']
                        elif row['actual_winner'] == 'home':
                            actual_team_winner = row['home_team']
                        else:
                            actual_team_winner = row['actual_winner']
                        
                        if person_team_pick == actual_team_winner:
                            wins += 1
                    
                    total = len(person_week_picks)
                    losses = total - wins
                    win_pct = (wins / total * 100) if total > 0 else 0
                    
                    week_record[person.title()] = f"{wins}-{losses} ({win_pct:.0f}%)"
                    
                    # Add to totals
                    if person.title() not in totals:
                        totals[person.title()] = {'wins': 0, 'total': 0}
                    totals[person.title()]['wins'] += wins
                    totals[person.title()]['total'] += total
                else:
                    week_record[person.title()] = "0-0 (0%)"
            
            weekly_records.append(week_record)
        
        # Calculate totals row
        for person in people:
            person_title = person.title()
            if person_title in totals and isinstance(totals[person_title], dict):
                total_wins = totals[person_title]['wins']
                total_games = totals[person_title]['total']
                total_losses = total_games - total_wins
                total_win_pct = (total_wins / total_games * 100) if total_games > 0 else 0
                totals[person_title] = f"{total_wins}-{total_losses} ({total_win_pct:.1f}%)"
            else:
                totals[person_title] = "0-0 (0%)"
        
        # Add totals row
        weekly_records.append(totals)
        
        return pd.DataFrame(weekly_records)
        
    except Exception as e:
        print(f"Error in get_weekly_records_data: {e}")
        return pd.DataFrame()

def create_weekly_trends_chart():
    """Create a line chart showing weekly win percentage trends"""
    try:
        conn = get_db_connection()
        if not conn:
            return go.Figure()
        
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return go.Figure()
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
        weeks = sorted(df['week'].unique())
        
        fig = go.Figure()
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        
        for i, person in enumerate(people):
            person_pick_col = f'{person}_pick'
            weekly_percentages = []
            
            for week in weeks:
                week_df = df[df['week'] == week]
                person_week_picks = week_df[week_df[person_pick_col].notna()]
                
                if len(person_week_picks) > 0:
                    wins = 0
                    for _, row in person_week_picks.iterrows():
                        # Handle pick comparison
                        if row[person_pick_col] == 'away':
                            person_team_pick = row['away_team']
                        elif row[person_pick_col] == 'home':
                            person_team_pick = row['home_team']
                        else:
                            person_team_pick = row[person_pick_col]
                        
                        # Handle actual winner
                        if row['actual_winner'] == 'away':
                            actual_team_winner = row['away_team']
                        elif row['actual_winner'] == 'home':
                            actual_team_winner = row['home_team']
                        else:
                            actual_team_winner = row['actual_winner']
                        
                        if person_team_pick == actual_team_winner:
                            wins += 1
                    
                    total = len(person_week_picks)
                    win_pct = (wins / total * 100) if total > 0 else 0
                    weekly_percentages.append(win_pct)
                else:
                    weekly_percentages.append(0)
            
            fig.add_trace(go.Scatter(
                x=[f"Week {w}" for w in weeks],
                y=weekly_percentages,
                mode='lines+markers',
                name=person.title(),
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=8)
            ))
        
        fig.update_layout(
            title='Weekly Win Percentage Trends',
            xaxis_title='Week',
            yaxis_title='Win Percentage (%)',
            hovermode='x unified',
            margin=dict(l=0, r=0, t=40, b=0),
            font=dict(size=12)
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creating weekly trends chart: {e}")
        return go.Figure()

# Statistics Dashboard Tab
def render_stats_dashboard_tab():
    """Comprehensive statistics dashboard with streaks and advanced analytics"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")
        
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL ORDER BY week, game_id", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No completed games available for statistics.", color="info")
        
        # Calculate various statistics
        streak_data = calculate_streaks(df)
        best_worst_weeks = calculate_best_worst_weeks(df)
        head_to_head = calculate_head_to_head_records(df)
        
        return [
            # Current Streaks Section
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4("Current Streaks", className="mb-0")
                        ]),
                        dbc.CardBody([
                            create_streaks_display(streak_data)
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            # Best/Worst Weeks
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4("Best & Worst Week Performances", className="mb-0")
                        ]),
                        dbc.CardBody([
                            create_best_worst_weeks_display(best_worst_weeks)
                        ])
                    ])
                ], width=12, lg=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4("Head-to-Head Records", className="mb-0"),
                            html.Small("Shows who makes better picks when players disagree", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dbc.Alert([
                                html.Strong("Explanation: "),
                                "When two players pick different teams for the same game, whoever picked the winning team gets a head-to-head win. This measures individual game decision-making skill."
                            ], color="info", className="mb-3"),
                            create_head_to_head_display(head_to_head)
                        ])
                    ])
                ], width=12, lg=6)
            ])
        ]
        
    except Exception as e:
        return dbc.Alert(f"Error loading statistics: {str(e)}", color="danger")

def calculate_streaks(df):
    """Calculate current winning/losing streaks for each player"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    streak_data = []
    
    for person in people:
        person_pick_col = f'{person}_pick'
        person_df = df[df[person_pick_col].notna()].sort_values(['week', 'game_id'])
        
        if len(person_df) == 0:
            continue
        
        # Calculate current streak
        current_streak = 0
        streak_type = None
        max_win_streak = 0
        max_loss_streak = 0
        
        # Get results in chronological order
        results = []
        for _, row in person_df.iterrows():
            # Handle pick comparison
            if row[person_pick_col] == 'away':
                person_team_pick = row['away_team']
            elif row[person_pick_col] == 'home':
                person_team_pick = row['home_team']
            else:
                person_team_pick = row[person_pick_col]
            
            # Handle actual winner
            if row['actual_winner'] == 'away':
                actual_team_winner = row['away_team']
            elif row['actual_winner'] == 'home':
                actual_team_winner = row['home_team']
            else:
                actual_team_winner = row['actual_winner']
            
            correct = person_team_pick == actual_team_winner
            results.append(correct)
        
        # Find current streak (from most recent games)
        if results:
            last_result = results[-1]
            current_streak = 1
            
            # Count backwards to find streak length
            for i in range(len(results) - 2, -1, -1):
                if results[i] == last_result:
                    current_streak += 1
                else:
                    break
            
            streak_type = "Win" if last_result else "Loss"
        
        # Find max streaks
        temp_streak = 0
        temp_type = None
        
        for result in results:
            if temp_type is None:
                temp_type = result
                temp_streak = 1
            elif temp_type == result:
                temp_streak += 1
            else:
                if temp_type:
                    max_win_streak = max(max_win_streak, temp_streak)
                else:
                    max_loss_streak = max(max_loss_streak, temp_streak)
                temp_type = result
                temp_streak = 1
        
        # Check final streak
        if temp_type:
            max_win_streak = max(max_win_streak, temp_streak)
        else:
            max_loss_streak = max(max_loss_streak, temp_streak)
        
        streak_data.append({
            'Player': person.title(),
            'Current Streak': f"{current_streak} {streak_type}" if streak_type else "No games",
            'Longest Win Streak': max_win_streak,
            'Longest Loss Streak': max_loss_streak
        })
    
    return streak_data

def create_streaks_display(streak_data):
    """Create display for streak information"""
    if not streak_data:
        return html.P("No streak data available.")
    
    return dash_table.DataTable(
        data=streak_data,
        columns=[
            {"name": "Player", "id": "Player"},
            {"name": "Current Streak", "id": "Current Streak"},
            {"name": "Best Win Streak", "id": "Longest Win Streak"},
            {"name": "Worst Loss Streak", "id": "Longest Loss Streak"}
        ],
        style_cell={
            'textAlign': 'center',
            'padding': '15px',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': '#28a745',
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{Current Streak} contains "Win"',
                    'column_id': 'Current Streak'
                },
                'backgroundColor': '#d4edda',
                'color': '#155724',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'filter_query': '{Current Streak} contains "Loss"',
                    'column_id': 'Current Streak'
                },
                'backgroundColor': '#f8d7da',
                'color': '#721c24',
                'fontWeight': 'bold'
            }
        ],
        style_table={'overflowX': 'auto'}
    )

def calculate_best_worst_weeks(df):
    """Calculate best and worst week performances"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    weeks = sorted(df['week'].unique())
    
    best_worst_data = []
    
    for person in people:
        person_pick_col = f'{person}_pick'
        weekly_records = []
        
        for week in weeks:
            week_df = df[df['week'] == week]
            person_week_picks = week_df[week_df[person_pick_col].notna()]
            
            if len(person_week_picks) > 0:
                wins = 0
                for _, row in person_week_picks.iterrows():
                    # Handle pick comparison
                    if row[person_pick_col] == 'away':
                        person_team_pick = row['away_team']
                    elif row[person_pick_col] == 'home':
                        person_team_pick = row['home_team']
                    else:
                        person_team_pick = row[person_pick_col]
                    
                    # Handle actual winner
                    if row['actual_winner'] == 'away':
                        actual_team_winner = row['away_team']
                    elif row['actual_winner'] == 'home':
                        actual_team_winner = row['home_team']
                    else:
                        actual_team_winner = row['actual_winner']
                    
                    if person_team_pick == actual_team_winner:
                        wins += 1
                
                total = len(person_week_picks)
                win_pct = (wins / total * 100) if total > 0 else 0
                
                weekly_records.append({
                    'week': week,
                    'wins': wins,
                    'total': total,
                    'win_pct': win_pct
                })
        
        if weekly_records:
            best_week = max(weekly_records, key=lambda x: (x['win_pct'], x['wins']))
            worst_week = min(weekly_records, key=lambda x: (x['win_pct'], -x['wins']))
            
            best_worst_data.append({
                'Player': person.title(),
                'Best Week': f"Week {best_week['week']} ({best_week['wins']}/{best_week['total']}, {best_week['win_pct']:.0f}%)",
                'Worst Week': f"Week {worst_week['week']} ({worst_week['wins']}/{worst_week['total']}, {worst_week['win_pct']:.0f}%)"
            })
    
    return best_worst_data

def create_best_worst_weeks_display(best_worst_data):
    """Create display for best/worst weeks"""
    if not best_worst_data:
        return html.P("No weekly performance data available.")
    
    return dash_table.DataTable(
        data=best_worst_data,
        columns=[
            {"name": "Player", "id": "Player"},
            {"name": "Best Week", "id": "Best Week"},
            {"name": "Worst Week", "id": "Worst Week"}
        ],
        style_cell={
            'textAlign': 'center',
            'padding': '15px',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '13px',
            'whiteSpace': 'normal',
            'height': 'auto'
        },
        style_header={
            'backgroundColor': '#17a2b8',
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        style_table={'overflowX': 'auto'}
    )

def calculate_head_to_head_records(df):
    """Calculate head-to-head win/loss records between players"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    h2h_summary = []
    
    for person in people:
        person_pick_col = f'{person}_pick'
        person_df = df[df[person_pick_col].notna()]
        
        wins_against = 0
        total_comparisons = 0
        
        for _, row in person_df.iterrows():
            # Handle person's pick
            if row[person_pick_col] == 'away':
                person_team_pick = row['away_team']
            elif row[person_pick_col] == 'home':
                person_team_pick = row['home_team']
            else:
                person_team_pick = row[person_pick_col]
            
            # Handle actual winner
            if row['actual_winner'] == 'away':
                actual_team_winner = row['away_team']
            elif row['actual_winner'] == 'home':
                actual_team_winner = row['home_team']
            else:
                actual_team_winner = row['actual_winner']
            
            person_correct = person_team_pick == actual_team_winner
            
            # Compare against each other player for this game
            for other_person in people:
                if other_person != person:
                    other_pick_col = f'{other_person}_pick'
                    if pd.notna(row[other_pick_col]):
                        # Handle other person's pick
                        if row[other_pick_col] == 'away':
                            other_team_pick = row['away_team']
                        elif row[other_pick_col] == 'home':
                            other_team_pick = row['home_team']
                        else:
                            other_team_pick = row[other_pick_col]
                        
                        other_correct = other_team_pick == actual_team_winner
                        
                        if person_correct and not other_correct:
                            wins_against += 1
                        if person_correct != other_correct:  # Only count games where outcomes differed
                            total_comparisons += 1
        
        win_rate = (wins_against / total_comparisons * 100) if total_comparisons > 0 else 0
        
        h2h_summary.append({
            'Player': person.title(),
            'Head-to-Head Wins': wins_against,
            'Total Comparisons': total_comparisons,
            'H2H Win Rate': f"{win_rate:.1f}%"
        })
    
    return sorted(h2h_summary, key=lambda x: float(x['H2H Win Rate'].rstrip('%')), reverse=True)

def create_head_to_head_display(h2h_data):
    """Create display for head-to-head records"""
    if not h2h_data:
        return html.P("No head-to-head data available.")
    
    return dash_table.DataTable(
        data=h2h_data,
        columns=[
            {"name": "Player", "id": "Player"},
            {"name": "H2H Wins", "id": "Head-to-Head Wins"},
            {"name": "Comparisons", "id": "Total Comparisons"},
            {"name": "Win Rate", "id": "H2H Win Rate"}
        ],
        style_cell={
            'textAlign': 'center',
            'padding': '12px',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': '#6f42c1',
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 0},
                'backgroundColor': '#d4edda',
                'color': '#155724',
                'fontWeight': 'bold'
            },
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        style_table={'overflowX': 'auto'}
    )

# Initialize database on startup
init_database()

# Server setup
server = app.server

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=False, host='0.0.0.0', port=port)