import dash
from dash import dcc, html, Input, Output, dash_table, State, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
from nfl_picks_automator import update_picks
import sqlite3
import base64
import io
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define all 32 NFL teams with colors
NFL_TEAMS = {
    'Arizona Cardinals': '#97233F', 'Atlanta Falcons': '#A71930', 'Baltimore Ravens': '#241773', 
    'Buffalo Bills': '#00338D', 'Carolina Panthers': '#0085CA', 'Chicago Bears': '#0B162A',
    'Cincinnati Bengals': '#FB4F14', 'Cleveland Browns': '#311D00', 'Dallas Cowboys': '#003594',
    'Denver Broncos': '#FB4F14', 'Detroit Lions': '#0076B6', 'Green Bay Packers': '#203731',
    'Houston Texans': '#03202F', 'Indianapolis Colts': '#002C5F', 'Jacksonville Jaguars': '#101820',
    'Kansas City Chiefs': '#E31837', 'Las Vegas Raiders': '#000000', 'Los Angeles Chargers': '#0080C6',
    'Los Angeles Rams': '#003594', 'Miami Dolphins': '#008E97', 'Minnesota Vikings': '#4F2683',
    'New England Patriots': '#002244', 'New Orleans Saints': '#D3BC8D', 'New York Giants': '#0B2265',
    'New York Jets': '#125740', 'Philadelphia Eagles': '#004C54', 'Pittsburgh Steelers': '#FFB612',
    'San Francisco 49ers': '#AA0000', 'Seattle Seahawks': '#002244', 'Tampa Bay Buccaneers': '#D50A0A',
    'Tennessee Titans': '#0C2340', 'Washington Commanders': '#5A1414'
}

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("🏈 2025 NFL Picks Championship", className="text-center mb-4 text-primary"),
            html.Hr()
        ], width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Upload New Picks"),
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-picks',
                        children=dbc.Button([
                            html.I(className="fas fa-upload me-2"),
                            "Upload Excel File"
                        ], color="primary", size="lg"),
                        multiple=False,
                        accept='.xlsx,.xlsm'
                    ),
                    html.Div(id='upload-status', className="mt-3")
                ])
            ], className="mb-4")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Update Results"),
                dbc.CardBody([
                    dbc.Button("🔄 Update with Latest Results", id='update-btn', color='success', size="lg", className="w-100"),
                    html.Div(id='update-status', className="mt-3")
                ])
            ], className="mb-4")
        ], width=6)
    ]),
    
    # Last updated info
    dbc.Row([
        dbc.Col([
            html.Div(id='last-updated-info', className="text-muted mb-3")
        ], width=12)
    ]),
    
    dbc.Tabs([
        dbc.Tab(label="🏆 Leaderboard", tab_id="leaderboard"),
        dbc.Tab(label="📅 Weekly Records", tab_id="weekly_records"),
        dbc.Tab(label="📊 Statistics", tab_id="statistics"),
        dbc.Tab(label="🎯 Tiebreaker Accuracy", tab_id="tiebreaker"),
        dbc.Tab(label="📈 Pick Trends", tab_id="trends"),
        dbc.Tab(label="📅 Weekly Picks", tab_id="weekly"),
        dbc.Tab(label="🏟️ Team Performance", tab_id="teams"),
        dbc.Tab(label="📋 Weekly Summaries", tab_id="summaries")
    ], id="main-tabs", active_tab="leaderboard", className="mb-4"),
    
    html.Div(id="tab-content")
], fluid=True)

@app.callback(
    Output('upload-status', 'children'),
    Input('upload-picks', 'contents'),
    State('upload-picks', 'filename')
)
def upload_file(contents, filename):
    if contents is None:
        return ""
    
    try:
        # Decode the uploaded file
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Save the uploaded file temporarily with a unique name
        import time
        temp_filename = f"temp_{int(time.time())}_{filename}"
        with open(temp_filename, 'wb') as f:
            f.write(decoded)
        
        # Import the data using our existing function
        from nfl_picks_automator import import_from_excel
        import_from_excel(temp_filename)
        
        # Clean up temp file with error handling
        try:
            import os
            import time
            time.sleep(0.5)  # Brief delay to ensure file handle is released
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
        except Exception as cleanup_error:
            print(f"Warning: Could not delete temporary file: {cleanup_error}")
            # Don't fail the upload just because we can't delete the temp file
        
        # Record upload time
        with open('last_upload.txt', 'w') as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"Successfully uploaded and processed {filename}!"
        ], color="success", dismissable=True, duration=5000)
        
    except Exception as e:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Error processing file: {str(e)}"
        ], color="danger", dismissable=True)

@app.callback(
    Output('update-status', 'children'),
    Input('update-btn', 'n_clicks')
)
def update_status(n_clicks):
    if not n_clicks:
        return ""
    
    try:
        update_picks()
        
        # Record update time
        with open('last_results_update.txt', 'w') as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            "Game results updated successfully!"
        ], color="success", dismissable=True, duration=4000)
    except Exception as e:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Update failed: {str(e)}"
        ], color="danger", dismissable=True)

@app.callback(
    Output('last-updated-info', 'children'),
    [Input('upload-status', 'children'), Input('update-status', 'children'), Input('main-tabs', 'active_tab')]
)
def show_last_updated(upload_status, update_status, active_tab):
    try:
        info_cards = []
        
        # Check last upload time
        if os.path.exists('last_upload.txt'):
            with open('last_upload.txt', 'r') as f:
                last_upload = f.read().strip()
            info_cards.append(
                dbc.Badge(f"Picks last uploaded: {last_upload}", color="info", className="me-2")
            )
        
        # Check last results update time
        if os.path.exists('last_results_update.txt'):
            with open('last_results_update.txt', 'r') as f:
                last_update = f.read().strip()
            info_cards.append(
                dbc.Badge(f"Results last updated: {last_update}", color="secondary")
            )
        
        return info_cards
    except:
        return []

@app.callback(
    Output("tab-content", "children"),
    [Input("main-tabs", "active_tab"), Input('update-btn', 'n_clicks'), Input('upload-status', 'children')]
)
def render_tab_content(active_tab, n_clicks, upload_status):
    if active_tab == "leaderboard":
        return render_leaderboard_tab()
    elif active_tab == "weekly_records":
        return render_weekly_records_tab()
    elif active_tab == "statistics":
        return render_statistics_tab()
    elif active_tab == "tiebreaker":
        return render_tiebreaker_tab()
    elif active_tab == "trends":
        return render_trends_tab()
    elif active_tab == "weekly":
        return render_weekly_tab()
    elif active_tab == "teams":
        return render_teams_tab()
    elif active_tab == "summaries":
        return render_summaries_tab()

def get_current_standings():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        standings = []
        
        for person in people:
            person_pick_col = f'{person}_pick'
            person_picks = df[df[person_pick_col].notna()]
            
            wins = 0
            losses = 0
            total_games = len(person_picks)
            
            for _, row in person_picks.iterrows():
                if row[person_pick_col] == row['actual_winner']:
                    wins += 1
                else:
                    losses += 1
            
            win_pct = (wins / total_games * 100) if total_games > 0 else 0
            
            standings.append({
                'Rank': 0,  # Will be calculated after sorting
                'Player': person.title(),
                'Wins': wins,
                'Losses': losses,
                'Total': total_games,
                'Win %': win_pct,
                'Win % Display': f"{win_pct:.1f}%"
            })
        
        standings_df = pd.DataFrame(standings)
        standings_df = standings_df.sort_values(['Win %', 'Wins'], ascending=[False, False])
        standings_df['Rank'] = range(1, len(standings_df) + 1)
        
        return standings_df
        
    except Exception as e:
        print(f"Error getting standings: {e}")
        return pd.DataFrame()

def render_leaderboard_tab():
    standings_df = get_current_standings()
    
    if standings_df.empty:
        return dbc.Alert("No game results available yet. Upload picks and update results to see standings.", color="info")
    
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
                        html.P(player['Win % Display'], className="text-center text-muted mb-0")
                    ], className="py-4")
                ], color=colors[i], outline=True, className="h-100")
            ], width=4)
        )
    
    return [
        dbc.Row([
            dbc.Col([
                html.H3("🏆 Championship Podium", className="text-center mb-4")
            ], width=12)
        ]),
        dbc.Row(podium_cards, className="mb-5"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-list-ol me-2"),
                            "Complete Standings"
                        ], className="mb-0")
                    ]),
                    dbc.CardBody([
                        dash_table.DataTable(
                            data=standings_df[['Rank', 'Player', 'Wins', 'Losses', 'Total', 'Win % Display']].to_dict('records'),
                            columns=[
                                {"name": "Rank", "id": "Rank"},
                                {"name": "Player", "id": "Player"},
                                {"name": "Wins", "id": "Wins"},
                                {"name": "Losses", "id": "Losses"},
                                {"name": "Total", "id": "Total"},
                                {"name": "Win %", "id": "Win % Display"}
                            ],
                            style_cell={
                                'textAlign': 'center',
                                'padding': '15px',
                                'fontFamily': 'Arial, sans-serif',
                                'fontSize': '14px'
                            },
                            style_header={
                                'backgroundColor': '#2c3e50',
                                'color': 'white',
                                'fontWeight': 'bold',
                                'fontSize': '16px'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 0},
                                    'backgroundColor': '#fff3cd',
                                    'color': '#856404',
                                    'fontWeight': 'bold'
                                },
                                {
                                    'if': {'row_index': 1},
                                    'backgroundColor': '#e2e3e5',
                                    'color': '#6c757d',
                                    'fontWeight': 'bold'
                                },
                                {
                                    'if': {'row_index': 2},
                                    'backgroundColor': '#f8d7da',
                                    'color': '#721c24',
                                    'fontWeight': 'bold'
                                }
                            ]
                        )
                    ])
                ])
            ], width=12)
        ])
    ]

def render_weekly_records_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No completed games available for weekly records.", color="info")
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        weeks = sorted(df['week'].unique())
        
        weekly_records = []
        
        for week in weeks:
            week_df = df[df['week'] == week]
            week_record = {'Week': f"Week {week}"}
            
            for person in people:
                person_pick_col = f'{person}_pick'
                person_week_picks = week_df[week_df[person_pick_col].notna()]
                
                if len(person_week_picks) > 0:
                    wins = len(person_week_picks[person_week_picks[person_pick_col] == person_week_picks['actual_winner']])
                    total = len(person_week_picks)
                    losses = total - wins
                    win_pct = (wins / total * 100) if total > 0 else 0
                    
                    week_record[person.title()] = f"{wins}-{losses} ({win_pct:.0f}%)"
                else:
                    week_record[person.title()] = "0-0 (0%)"
            
            weekly_records.append(week_record)
        
        weekly_df = pd.DataFrame(weekly_records)
        
        return dbc.Card([
            dbc.CardHeader([
                html.H4([
                    html.I(className="fas fa-calendar-week me-2"),
                    "Weekly Records"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
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
                        'fontSize': '13px'
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
                    page_size=20
                )
            ])
        ])
        
    except Exception as e:
        return dbc.Alert(f"Error loading weekly records: {str(e)}", color="danger")

def render_statistics_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No completed games available for statistics.", color="info")
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        
        # Weekly performance chart
        weekly_stats = []
        weeks = sorted(df['week'].unique())
        
        for week in weeks:
            week_df = df[df['week'] == week]
            for person in people:
                person_pick_col = f'{person}_pick'
                person_week_picks = week_df[week_df[person_pick_col].notna()]
                
                if len(person_week_picks) > 0:
                    wins = len(person_week_picks[person_week_picks[person_pick_col] == person_week_picks['actual_winner']])
                    total = len(person_week_picks)
                    win_pct = (wins / total * 100) if total > 0 else 0
                    
                    weekly_stats.append({
                        'Week': f"Week {week}",
                        'Player': person.title(),
                        'Win %': win_pct,
                        'Wins': wins,
                        'Total': total
                    })
        
        weekly_df = pd.DataFrame(weekly_stats)
        
        if not weekly_df.empty:
            fig = px.line(weekly_df, x='Week', y='Win %', color='Player', 
                         title='Weekly Performance Trends',
                         markers=True)
            fig.update_layout(yaxis_title='Win Percentage (%)')
            
            weekly_chart = dcc.Graph(figure=fig)
        else:
            weekly_chart = html.P("No weekly data available")
        
        return [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📈 Weekly Performance Trends"),
                        dbc.CardBody([weekly_chart])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🥊 Head-to-Head Comparison"),
                        dbc.CardBody([
                            html.P("Coming soon - detailed matchup analysis", className="text-muted")
                        ])
                    ])
                ], width=12)
            ])
        ]
        
    except Exception as e:
        return dbc.Alert(f"Error loading statistics: {str(e)}", color="danger")

def render_tiebreaker_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_total_points IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No tiebreaker data available yet.", color="info")
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        tiebreaker_stats = []
        
        for person in people:
            person_guess_col = f'{person}_total_guess'
            person_tiebreakers = df[df[person_guess_col].notna()]
            
            if len(person_tiebreakers) > 0:
                total_error = 0
                closest_count = 0
                
                for _, row in person_tiebreakers.iterrows():
                    guess = row[person_guess_col]
                    actual = row['actual_total_points']
                    error = abs(guess - actual)
                    total_error += error
                    
                    # Check if this was the closest guess for this game
                    game_row = df[(df['week'] == row['week']) & (df['game_id'] == row['game_id'])].iloc[0]
                    all_guesses = []
                    for p in people:
                        p_guess_col = f'{p}_total_guess'
                        if pd.notna(game_row[p_guess_col]):
                            all_guesses.append(abs(game_row[p_guess_col] - actual))
                    
                    if all_guesses and error == min(all_guesses):
                        closest_count += 1
                
                avg_error = total_error / len(person_tiebreakers)
                
                tiebreaker_stats.append({
                    'Player': person.title(),
                    'Games': len(person_tiebreakers),
                    'Avg Error': f"{avg_error:.1f}",
                    'Closest': closest_count,
                    'Accuracy': f"{(closest_count/len(person_tiebreakers)*100):.1f}%" if len(person_tiebreakers) > 0 else "0%"
                })
        
        tiebreaker_df = pd.DataFrame(tiebreaker_stats)
        tiebreaker_df = tiebreaker_df.sort_values('Avg Error')
        
        return dbc.Card([
            dbc.CardHeader([
                html.H4([
                    html.I(className="fas fa-bullseye me-2"),
                    "Tiebreaker Accuracy Leaders"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    html.Strong("Scoring: "),
                    "Lower average error = better accuracy. 'Closest' shows how many times you had the most accurate prediction."
                ], color="info", className="mb-3"),
                
                dash_table.DataTable(
                    data=tiebreaker_df.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in tiebreaker_df.columns],
                    style_cell={
                        'textAlign': 'center',
                        'padding': '12px',
                        'fontFamily': 'Arial, sans-serif'
                    },
                    style_header={
                        'backgroundColor': '#28a745',
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 0},
                            'backgroundColor': '#d4edda',
                            'color': '#155724',
                            'fontWeight': 'bold'
                        }
                    ]
                )
            ])
        ])
        
    except Exception as e:
        return dbc.Alert(f"Error loading tiebreaker data: {str(e)}", color="danger")

def render_trends_tab():
    return dbc.Alert("Pick trends analysis coming soon!", color="info")

def render_summaries_tab():
    return dbc.Alert("Weekly summaries coming soon!", color="info")

def render_teams_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No picks data available. Upload your Excel file first.", color="info")
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        
        # Create person selector
        person_cards = []
        for person in people:
            person_cards.append(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5(person.title(), className="card-title text-center"),
                            dbc.Button("View Performance", 
                                     id=f"btn-{person}", 
                                     color="primary", 
                                     className="w-100",
                                     size="sm")
                        ])
                    ], className="h-100")
                ], width=2)
            )
        
        return [
            dbc.Row([
                dbc.Col([
                    html.H4("🏟️ Team Performance Analysis", className="mb-4"),
                    html.P("Select a player to view their performance with each NFL team:", className="text-muted mb-4")
                ], width=12)
            ]),
            
            dbc.Row(person_cards, className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    html.Div(id="team-performance-content")
                ], width=12)
            ])
        ]
        
    except Exception as e:
        return dbc.Alert(f"Error loading team performance data: {str(e)}", color="danger")

# Add callbacks for team performance
for person in ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']:
    @app.callback(
        Output("team-performance-content", "children"),
        Input(f"btn-{person}", "n_clicks"),
        prevent_initial_call=True
    )
    def show_person_team_performance(n_clicks, person=person):
        if not n_clicks:
            return html.Div()
        
        try:
            conn = sqlite3.connect('picks.db', check_same_thread=False)
            df = pd.read_sql_query("SELECT * FROM picks", conn)
            conn.close()
            
            person_pick_col = f'{person}_pick'
            person_df = df[df[person_pick_col].notna()].copy()
            
            team_breakdown = []
            
            for team in NFL_TEAMS.keys():
                team_picks = person_df[
                    ((person_df['away_team'] == team) & (person_df[person_pick_col] == 'Away')) |
                    ((person_df['home_team'] == team) & (person_df[person_pick_col] == 'Home'))
                ]
                
                completed_picks = team_picks[team_picks['actual_winner'].notna()]
                wins = 0
                if len(completed_picks) > 0:
                    for _, pick_row in completed_picks.iterrows():
                        if pick_row['actual_winner'] == 'Away' and pick_row[person_pick_col] == 'Away' and pick_row['away_team'] == team:
                            wins += 1
                        elif pick_row['actual_winner'] == 'Home' and pick_row[person_pick_col] == 'Home' and pick_row['home_team'] == team:
                            wins += 1
                        elif pick_row['actual_winner'] == team:
                            wins += 1
                
                total_picks = len(team_picks)
                completed_games = len(completed_picks)
                losses = completed_games - wins
                pending_games = total_picks - completed_games
                
                if completed_games > 0:
                    win_pct = (wins / completed_games * 100)
                else:
                    win_pct = 0
                
                if completed_games == 0:
                    performance = "⚪ No picks" if total_picks == 0 else "⏳ Pending"
                elif win_pct >= 70:
                    performance = "🔥 Hot"
                elif win_pct >= 50:
                    performance = "✅ Good"
                else:
                    performance = "❄️ Cold"
                
                if pending_games > 0:
                    record = f"{wins}-{losses}-{pending_games}"
                else:
                    record = f"{wins}-{losses}"
                
                if total_picks > 0:  # Only show teams they've picked
                    team_breakdown.append({
                        'Team': team,
                        'Record': record,
                        'Win %': f"{win_pct:.1f}%" if completed_games > 0 else "0.0%",
                        'Total Picks': total_picks,
                        'Completed': completed_games,
                        'Performance': performance
                    })
            
            breakdown_df = pd.DataFrame(team_breakdown)
            breakdown_df = breakdown_df.sort_values(['Total Picks', 'Win %'], ascending=[False, False])
            
            return dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-user me-2"),
                        f"{person.title()}'s Team Performance"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dash_table.DataTable(
                        data=breakdown_df.to_dict('records'),
                        columns=[{"name": col, "id": col} for col in breakdown_df.columns],
                        style_cell={
                            'textAlign': 'center',
                            'padding': '10px',
                            'fontFamily': 'Arial, sans-serif',
                            'fontSize': '12px'
                        },
                        style_header={
                            'backgroundColor': '#e74c3c',
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
                                    'filter_query': '{Performance} contains "🔥"',
                                    'column_id': 'Performance'
                                },
                                'backgroundColor': '#d4edda',
                                'color': '#155724'
                            },
                            {
                                'if': {
                                    'filter_query': '{Performance} contains "❄️"',
                                    'column_id': 'Performance'
                                },
                                'backgroundColor': '#f8d7da',
                                'color': '#721c24'
                            },
                            {
                                'if': {
                                    'filter_query': '{Performance} contains "⚪"',
                                    'column_id': 'Performance'
                                },
                                'backgroundColor': '#e2e3e5',
                                'color': '#6c757d'
                            },
                            {
                                'if': {
                                    'filter_query': '{Performance} contains "⏳"',
                                    'column_id': 'Performance'
                                },
                                'backgroundColor': '#fff3cd',
                                'color': '#856404'
                            }
                        ],
                        style_data={
                            'border': '1px solid #dee2e6'
                        },
                        sort_action="native",
                        filter_action="native",
                        page_size=20
                    )
                ])
            ])
            
        except Exception as e:
            return dbc.Alert(f"Error loading team performance data: {str(e)}", color="danger")

def render_weekly_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks ORDER BY week, game_id", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No weekly picks data available. Upload your Excel file first.", color="info")
        
        weeks = sorted(df['week'].unique())
        
        tabs_content = []
        for week in weeks:
            week_df = df[df['week'] == week]
            week_content = create_week_content(week_df, week)
            
            tabs_content.append(
                dbc.Tab(label=f"Week {week}", tab_id=f"week-{week}", children=[
                    html.Div(week_content, className="mt-3")
                ])
            )
        
        return html.Div([
            dbc.Card([
                dbc.CardHeader([
                    html.H4([
                        html.I(className="fas fa-calendar-alt me-2"),
                        "Weekly Picks & Results"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dbc.Tabs(tabs_content, id="week-tabs", active_tab=f"week-{weeks[0]}" if weeks else None)
                ])
            ])
        ])
    except Exception as e:
        return dbc.Alert(f"Error loading weekly data: {str(e)}", color="danger")

def create_week_content(week_df, week_num):
    if week_df.empty:
        return html.P(f"No data for Week {week_num}")
    
    # Find the tiebreaker game (last game with tiebreaker predictions)
    tiebreaker_game_id = None
    tiebreaker_predictions = {}
    people_names = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
    
    for _, row in week_df.iterrows():
        # Check if this game has tiebreaker predictions
        has_tiebreaker = any(pd.notna(row[f'{person}_total_guess']) for person in people_names)
        if has_tiebreaker:
            tiebreaker_game_id = row['game_id']
            for person in people_names:
                guess = row[f'{person}_total_guess']
                if pd.notna(guess):
                    tiebreaker_predictions[person] = int(guess)
            break
    
    # Create picks table
    display_data = []
    people_cols = ['bobby_pick', 'chet_pick', 'clyde_pick', 'henry_pick', 'riley_pick', 'nick_pick']
    
    for _, row in week_df.iterrows():
        game_row = {
            'Away Team': row['away_team'],
            'Home Team': row['home_team']
        }
        
        # Check if this is the tiebreaker game
        is_tiebreaker_game = (row['game_id'] == tiebreaker_game_id)
        
        for i, col in enumerate(people_cols):
            person_name = col.replace('_pick', '').title()
            person_key = col.replace('_pick', '')
            pick = row[col]
            
            if pick == 'Away':
                pick_display = f"✓ {row['away_team']}"
            elif pick == 'Home':
                pick_display = f"✓ {row['home_team']}"
            else:
                pick_display = '-'
            
            # Add tiebreaker prediction if this is the tiebreaker game
            if is_tiebreaker_game and person_key in tiebreaker_predictions:
                pick_display += f" ({tiebreaker_predictions[person_key]})"
            
            game_row[person_name] = pick_display
        
        # Add actual winner and total points
        if pd.notna(row['actual_winner']):
            if row['actual_winner'] == 'Away':
                winner_display = row['away_team']
            elif row['actual_winner'] == 'Home':
                winner_display = row['home_team']
            else:
                winner_display = row['actual_winner']
            
            # If this game has tiebreaker predictions AND actual total points, show just the total
            has_any_tiebreaker = any(pd.notna(row[f'{person}_total_guess']) for person in people_names)
            if has_any_tiebreaker and pd.notna(row.get('actual_total_points')):
                game_row['🏆 Winner'] = str(int(row['actual_total_points']))
            else:
                game_row['🏆 Winner'] = winner_display
        else:
            # Show tiebreaker prediction totals for pending games
            has_any_tiebreaker = any(pd.notna(row[f'{person}_total_guess']) for person in people_names)
            if has_any_tiebreaker:
                predictions = []
                for person in people_names:
                    guess = row[f'{person}_total_guess']
                    if pd.notna(guess):
                        predictions.append(f"{person.title()}: {int(guess)}")
                if predictions:
                    predictions_text = ", ".join(predictions)
                    game_row['🏆 Winner'] = f"TBD ({predictions_text})"
                else:
                    game_row['🏆 Winner'] = 'TBD'
            else:
                game_row['🏆 Winner'] = 'TBD'
        
        display_data.append(game_row)
    
    picks_df = pd.DataFrame(display_data)
    
    # Create conditional formatting rules for correct/incorrect picks
    style_data_conditional = [
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': '#f8f9fa'
        }
    ]
    
    # Add color coding for each person's picks
    for _, row in week_df.iterrows():
        if pd.notna(row['actual_winner']):
            row_index = row['game_id'] - 1  # game_id starts at 1, row_index at 0
            
            for col in people_cols:
                person_name = col.replace('_pick', '').title()
                person_pick = row[col]
                actual_winner = row['actual_winner']
                
                if person_pick == actual_winner:
                    # Correct pick - green
                    style_data_conditional.append({
                        'if': {
                            'row_index': row_index,
                            'column_id': person_name
                        },
                        'backgroundColor': '#d4edda',
                        'color': '#155724',
                        'fontWeight': 'bold'
                    })
                elif person_pick and person_pick != actual_winner:
                    # Incorrect pick - red
                    style_data_conditional.append({
                        'if': {
                            'row_index': row_index,
                            'column_id': person_name
                        },
                        'backgroundColor': '#f8d7da',
                        'color': '#721c24',
                        'fontWeight': 'bold'
                    })
    
    # Create more specific tiebreaker info
    if tiebreaker_predictions:
        tiebreaker_info = dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            html.Strong("Tiebreaker: "),
            f"Numbers in parentheses show each person's total points prediction for the tiebreaker game. "
            f"Green = correct pick, Red = incorrect pick."
        ], color="info", className="mb-3")
    else:
        tiebreaker_info = dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            "No tiebreaker predictions available for this week. Green = correct pick, Red = incorrect pick."
        ], color="info", className="mb-3")
    
    picks_table = dash_table.DataTable(
        data=picks_df.to_dict('records'),
        columns=[{"name": col, "id": col} for col in picks_df.columns],
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'fontSize': '11px',
            'fontFamily': 'Arial, sans-serif'
        },
        style_header={
            'backgroundColor': '#17a2b8',
            'color': 'white',
            'fontWeight': 'bold',
            'border': '1px solid #138496'
        },
        style_data_conditional=style_data_conditional,
        style_data={
            'border': '1px solid #dee2e6'
        },
        page_size=20
    )
    
    return [tiebreaker_info, picks_table]

server = app.server

if __name__ == '__main__':
    app.run(debug=True)