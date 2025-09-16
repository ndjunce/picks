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

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define all 32 NFL teams
NFL_TEAMS = [
    'Arizona Cardinals', 'Atlanta Falcons', 'Baltimore Ravens', 'Buffalo Bills',
    'Carolina Panthers', 'Chicago Bears', 'Cincinnati Bengals', 'Cleveland Browns',
    'Dallas Cowboys', 'Denver Broncos', 'Detroit Lions', 'Green Bay Packers',
    'Houston Texans', 'Indianapolis Colts', 'Jacksonville Jaguars', 'Kansas City Chiefs',
    'Las Vegas Raiders', 'Los Angeles Chargers', 'Los Angeles Rams', 'Miami Dolphins',
    'Minnesota Vikings', 'New England Patriots', 'New Orleans Saints', 'New York Giants',
    'New York Jets', 'Philadelphia Eagles', 'Pittsburgh Steelers', 'San Francisco 49ers',
    'Seattle Seahawks', 'Tampa Bay Buccaneers', 'Tennessee Titans', 'Washington Commanders'
]

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("NFL Picks Tracker", className="text-center mb-4 text-primary"),
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
                        children=dbc.Button("Upload Excel File", color="primary", size="lg"),
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
                    dbc.Button("Update with Latest Results", id='update-btn', color='success', size="lg", className="w-100"),
                    html.Div(id='update-status', className="mt-3")
                ])
            ], className="mb-4")
        ], width=6)
    ]),
    
    dbc.Tabs([
        dbc.Tab(label="Leaderboard", tab_id="leaderboard"),
        dbc.Tab(label="Weekly Records", tab_id="weekly_records"),
        dbc.Tab(label="Statistics Dashboard", tab_id="stats_dashboard"),
        dbc.Tab(label="Tiebreaker Accuracy", tab_id="tiebreaker"),
        dbc.Tab(label="Weekly Picks", tab_id="weekly"),
        dbc.Tab(label="Team Performance", tab_id="teams")
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
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        import time
        temp_filename = f"temp_{int(time.time())}_{filename}"
        with open(temp_filename, 'wb') as f:
            f.write(decoded)
        
        from nfl_picks_automator import import_from_excel
        import_from_excel(temp_filename)
        
        try:
            time.sleep(0.5)
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
        except:
            pass
        
        return dbc.Alert(f"Successfully uploaded {filename}!", color="success", dismissable=True)
        
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)

@app.callback(
    Output('update-status', 'children'),
    Input('update-btn', 'n_clicks')
)
def update_status(n_clicks):
    if not n_clicks:
        return ""
    
    try:
        update_picks()
        return dbc.Alert("Results updated successfully!", color="success", dismissable=True)
    except Exception as e:
        return dbc.Alert(f"Update failed: {str(e)}", color="danger", dismissable=True)

@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "active_tab")
)
def render_tab_content(active_tab):
    if active_tab == "leaderboard":
        return render_leaderboard_tab()
    elif active_tab == "weekly_records":
        return render_weekly_records_tab()
    elif active_tab == "stats_dashboard":
        return render_stats_dashboard_tab()
    elif active_tab == "tiebreaker":
        return render_tiebreaker_tab()
    elif active_tab == "weekly":
        return render_weekly_tab()
    elif active_tab == "teams":
        return render_teams_tab()

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
            total_games = len(person_picks)
            
            for _, row in person_picks.iterrows():
                if row[person_pick_col] == row['actual_winner']:
                    wins += 1
            
            losses = total_games - wins
            win_pct = (wins / total_games * 100) if total_games > 0 else 0
            
            standings.append({
                'Player': person.title(),
                'Wins': wins,
                'Losses': losses,
                'Total': total_games,
                'Win %': f"{win_pct:.1f}%"
            })
        
        standings_df = pd.DataFrame(standings)
        standings_df = standings_df.sort_values('Wins', ascending=False)
        standings_df.insert(0, 'Rank', range(1, len(standings_df) + 1))
        
        return standings_df
        
    except Exception as e:
        print(f"Error getting standings: {e}")
        return pd.DataFrame()

def render_leaderboard_tab():
    standings_df = get_current_standings()
    
    if standings_df.empty:
        return dbc.Alert("No game results available yet.", color="info")
    
    return dbc.Card([
        dbc.CardHeader("Current Standings"),
        dbc.CardBody([
            dash_table.DataTable(
                data=standings_df.to_dict('records'),
                columns=[{"name": col, "id": col} for col in standings_df.columns],
                style_cell={'textAlign': 'center', 'padding': '12px'},
                style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'}
            )
        ])
    ])

def render_weekly_records_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No completed games available.", color="info")
        
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
            dbc.CardHeader("Weekly Records"),
            dbc.CardBody([
                dash_table.DataTable(
                    data=weekly_df.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in weekly_df.columns],
                    style_cell={'textAlign': 'center', 'padding': '12px'},
                    style_header={'backgroundColor': '#17a2b8', 'color': 'white', 'fontWeight': 'bold'}
                )
            ])
        ])
        
    except Exception as e:
        return dbc.Alert(f"Error loading weekly records: {str(e)}", color="danger")

def render_stats_dashboard_tab():
    return dbc.Card([
        dbc.CardHeader("Statistics Dashboard"),
        dbc.CardBody([
            html.H4("Statistics Dashboard Available!", className="text-center"),
            html.P("Enhanced statistics coming soon...", className="text-center text-muted")
        ])
    ])

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
            person_predictions = df[df[person_guess_col].notna()].copy()
            
            if len(person_predictions) == 0:
                continue
            
            differences = []
            for _, row in person_predictions.iterrows():
                predicted = float(row[person_guess_col])
                actual = float(row['actual_total_points'])
                difference = abs(predicted - actual)
                differences.append(difference)
            
            if differences:
                avg_diff = sum(differences) / len(differences)
                closest = min(differences)
                worst = max(differences)
                
                tiebreaker_stats.append({
                    'Player': person.title(),
                    'Avg Error': f"{avg_diff:.1f}",
                    'Total Predictions': len(differences),
                    'Closest': f"{closest:.0f}",
                    'Worst': f"{worst:.0f}"
                })
        
        # Sort by average difference (lower is better)
        tiebreaker_stats.sort(key=lambda x: float(x['Avg Error']))
        
        # Add ranks
        for i, player in enumerate(tiebreaker_stats):
            player['Rank'] = i + 1
        
        return dbc.Card([
            dbc.CardHeader("Tiebreaker Accuracy Leaderboard"),
            dbc.CardBody([
                dbc.Alert("Lower average error = better accuracy", color="info", className="mb-3"),
                dash_table.DataTable(
                    data=tiebreaker_stats,
                    columns=[
                        {"name": "Rank", "id": "Rank"},
                        {"name": "Player", "id": "Player"},
                        {"name": "Avg Error", "id": "Avg Error"},
                        {"name": "Total Predictions", "id": "Total Predictions"},
                        {"name": "Closest", "id": "Closest"},
                        {"name": "Worst", "id": "Worst"}
                    ],
                    style_cell={'textAlign': 'center', 'padding': '12px'},
                    style_header={'backgroundColor': '#ff6b35', 'color': 'white', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 0},
                            'backgroundColor': '#fff3cd',
                            'fontWeight': 'bold'
                        }
                    ]
                )
            ])
        ])
        
    except Exception as e:
        return dbc.Alert(f"Error loading tiebreaker data: {str(e)}", color="danger")

def render_weekly_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks ORDER BY week, game_id", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No weekly picks data available. Upload your Excel file first.", color="info")
        
        # Get ALL weeks, not just first 3
        weeks = sorted(df['week'].unique())
        
        tabs_content = []
        for week in weeks:  # Remove the [:3] limit that was causing only 3 weeks to show
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
    
    # Find the tiebreaker game 
    tiebreaker_game_id = None
    tiebreaker_predictions = {}
    people_names = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
    
    for _, row in week_df.iterrows():
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
            
            # Show total points for tiebreaker game
            has_any_tiebreaker = any(pd.notna(row[f'{person}_total_guess']) for person in people_names)
            if has_any_tiebreaker and pd.notna(row.get('actual_total_points')):
                game_row['Winner'] = f"{winner_display} (Total: {int(row['actual_total_points'])})"
            else:
                game_row['Winner'] = winner_display
        else:
            game_row['Winner'] = 'TBD'
        
        display_data.append(game_row)
    
    picks_df = pd.DataFrame(display_data)
    
    # Create conditional formatting for correct/incorrect picks
    style_data_conditional = [
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': '#f8f9fa'
        }
    ]
    
    # Add color coding
    for row_idx, (_, row) in enumerate(week_df.iterrows()):
        if pd.notna(row['actual_winner']):
            for col in people_cols:
                person_name = col.replace('_pick', '').title()
                person_pick = row[col]
                actual_winner = row['actual_winner']
                
                if person_pick == actual_winner:
                    # Correct pick - green
                    style_data_conditional.append({
                        'if': {
                            'row_index': row_idx,
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
                            'row_index': row_idx,
                            'column_id': person_name
                        },
                        'backgroundColor': '#f8d7da',
                        'color': '#721c24',
                        'fontWeight': 'bold'
                    })
    
    # Info alert
    tiebreaker_info = dbc.Alert([
        html.I(className="fas fa-info-circle me-2"),
        html.Strong("Legend: "),
        "Green = correct pick, Red = incorrect pick. Numbers in parentheses = tiebreaker predictions."
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

def render_teams_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No picks data available.", color="info")
        
        # Simple team summary
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        team_summary = []
        
        for person in people:
            person_pick_col = f'{person}_pick'
            person_picks = df[df[person_pick_col].notna()]
            
            total_picks = len(person_picks)
            completed_picks = person_picks[person_picks['actual_winner'].notna()]
            wins = len(completed_picks[completed_picks[person_pick_col] == completed_picks['actual_winner']]) if len(completed_picks) > 0 else 0
            
            team_summary.append({
                'Person': person.title(),
                'Total Picks': total_picks,
                'Completed Games': len(completed_picks),
                'Wins': wins,
                'Losses': len(completed_picks) - wins
            })
        
        summary_df = pd.DataFrame(team_summary)
        
        return dbc.Card([
            dbc.CardHeader("Team Performance Summary"),
            dbc.CardBody([
                dash_table.DataTable(
                    data=summary_df.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in summary_df.columns],
                    style_cell={'textAlign': 'center', 'padding': '12px'},
                    style_header={'backgroundColor': '#e74c3c', 'color': 'white', 'fontWeight': 'bold'}
                )
            ])
        ])
        
    except Exception as e:
        return dbc.Alert(f"Error loading team data: {str(e)}", color="danger")

if __name__ == '__main__':
    app.run(debug=True)