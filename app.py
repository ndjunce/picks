import dash
from dash import dcc, html, Input, Output, dash_table, State
import dash_bootstrap_components as dbc
import pandas as pd
import sqlite3
import base64
import os
from datetime import datetime

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
                dbc.CardHeader("Update Results"),
                dbc.CardBody([
                    dbc.Button("Update Results", id='update-btn', color='success', size="lg", className="w-100"),
                    html.Div(id='update-status', className="mt-3")
                ])
            ], className="mb-4")
        ], width=12, md=6)
    ]),
    
    # Main Content
    dbc.Tabs([
        dbc.Tab(label="Leaderboard", tab_id="leaderboard"),
        dbc.Tab(label="Weekly Records", tab_id="weekly_records")
    ], id="main-tabs", active_tab="leaderboard", className="mb-4"),
    
    html.Div(id="tab-content")
], fluid=True)

# Database helper function
def get_db_connection():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False, timeout=30)
        return conn
    except:
        return None

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
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Save file
        persistent_filename = f"uploaded_picks_{filename}"
        with open(persistent_filename, 'wb') as f:
            f.write(decoded)
        
        # Try to process
        try:
            from nfl_picks_automator import import_from_excel
            import_from_excel(persistent_filename)
            message = f"Successfully uploaded and processed {filename}!"
        except:
            message = f"File {filename} uploaded but processing failed."
        
        return dbc.Alert(message, color="success", dismissable=True)
        
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)

# Update callback
@app.callback(
    Output('update-status', 'children'),
    Input('update-btn', 'n_clicks')
)
def update_status(n_clicks):
    if not n_clicks:
        return ""
    
    try:
        from nfl_picks_automator import update_picks
        update_picks()
        return dbc.Alert("Results updated!", color="success", dismissable=True)
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
                if row[person_pick_col] == row['actual_winner']:
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

# Leaderboard tab
def render_leaderboard_tab():
    standings_df = get_current_standings()
    
    if standings_df.empty:
        return dbc.Alert("No game results available. Upload picks and update results first.", color="info")
    
    return dbc.Card([
        dbc.CardHeader("Current Standings"),
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
                style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'}
            )
        ])
    ])

# Weekly records placeholder
def render_weekly_records_tab():
    return dbc.Alert("Weekly records coming soon!", color="info")

# Server setup
server = app.server

if __name__ == '__main__':
    app.run(debug=True)