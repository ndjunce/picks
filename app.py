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
    # Add custom CSS for mobile optimization
    html.Head([
        html.Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        html.Style("""
            /* Mobile-first responsive design */
            @media (max-width: 768px) {
                .container-fluid {
                    padding: 5px !important;
                }
                
                .card {
                    margin-bottom: 10px !important;
                }
                
                .btn-group {
                    width: 100%;
                    flex-direction: column;
                    gap: 5px;
                }
                
                .btn-group .btn {
                    margin-bottom: 5px;
                    width: 100%;
                }
                
                h1 {
                    font-size: 1.2rem !important;
                }
                
                h2 {
                    font-size: 1.1rem !important;
                }
                
                h3 {
                    font-size: 1.0rem !important;
                }
                
                h4 {
                    font-size: 0.9rem !important;
                }
                
                .dash-table-container {
                    font-size: 9px !important;
                }
                
                .dash-cell div {
                    max-width: 60px !important;
                    overflow: hidden !important;
                    text-overflow: ellipsis !important;
                    white-space: nowrap !important;
                }
                
                .btn-sm {
                    font-size: 0.75rem !important;
                    padding: 4px 8px !important;
                }
                
                .card-body {
                    padding: 0.75rem !important;
                }
                
                .nav-tabs .nav-link {
                    padding: 0.25rem 0.5rem !important;
                    font-size: 0.8rem !important;
                }
            }
            
            /* Better table scrolling on mobile */
            .dash-table-container .dash-spreadsheet-container {
                max-height: 400px;
                overflow-y: auto;
            }
            
            /* Responsive charts */
            .js-plotly-plot {
                width: 100% !important;
            }
            
            /* Custom team colors for enhanced visual appeal */
            .team-card {
                transition: transform 0.2s;
            }
            
            .team-card:hover {
                transform: translateY(-2px);
            }
        """)
    ]),
    
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("NFL Picks Tracker", className="text-center mb-4 text-primary"),
            html.Hr()
        ], width=12)
    ]),
    
    # Upload and Update Controls
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
        ], width=12, md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Update Results"),
                dbc.CardBody([
                    dbc.Button("Update with Latest Results", id='update-btn', color='success', size="lg", className="w-100"),
                    html.Div(id='update-status', className="mt-3")
                ])
            ], className="mb-4")
        ], width=12, md=6)
    ]),
    
    # Enhanced Export Controls
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Export Options"),
                dbc.CardBody([
                    dbc.ButtonGroup([
                        dbc.Button([
                            html.I(className="fas fa-download me-2"),
                            "Export CSV"
                        ], id="export-csv-btn", color="success", size="sm"),
                        dbc.Button([
                            html.I(className="fas fa-file-excel me-2"),
                            "Export Excel"
                        ], id="export-excel-btn", color="primary", size="sm")
                    ], className="mb-2", style={'flexWrap': 'wrap'})
                ])
            ], className="mb-3")
        ], width=12)
    ]),
    
    # Last updated info
    dbc.Row([
        dbc.Col([
            html.Div(id='last-updated-info', className="text-muted mb-3")
        ], width=12)
    ]),
    
    # Enhanced tab structure
    dbc.Tabs([
        dbc.Tab(label="Leaderboard", tab_id="leaderboard"),
        dbc.Tab(label="Weekly Records", tab_id="weekly_records"),
        dbc.Tab(label="Weekly Picks", tab_id="weekly"),
        dbc.Tab(label="Team Performance", tab_id="teams")
    ], id="main-tabs", active_tab="leaderboard", className="mb-4"),
    
    html.Div(id="tab-content"),
    
    # Hidden divs for downloads
    dcc.Download(id="download-csv"),
    dcc.Download(id="download-excel")
], fluid=True, style={'padding': '10px', 'maxWidth': '100%'})

# Database helper function with error handling
def get_db_connection():
    """Get database connection with error handling"""
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False, timeout=30)
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn
    except sqlite3.OperationalError as e:
        print(f"Database connection error: {e}")
        return None

# Upload callback with persistent storage
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
        
        # Save to persistent filename
        persistent_filename = f"uploaded_picks_{filename}"
        with open(persistent_filename, 'wb') as f:
            f.write(decoded)
        
        from nfl_picks_automator import import_from_excel
        import_from_excel(persistent_filename)
        
        # Store metadata about the upload
        with open('last_upload.txt', 'w') as f:
            upload_info = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{filename},{persistent_filename}"
            f.write(upload_info)
        
        return dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"Successfully uploaded and processed {filename}!"
        ], color="success", dismissable=True, duration=5000)
        
    except Exception as e:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Error processing file: {str(e)}"
        ], color="danger", dismissable=True)

# Update callback
@app.callback(
    Output('update-status', 'children'),
    Input('update-btn', 'n_clicks')
)
def update_status(n_clicks):
    if not n_clicks:
        return ""
    
    try:
        update_picks()
        
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

# Export callbacks
@app.callback(
    Output("download-csv", "data"),
    Input("export-csv-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_csv(n_clicks):
    if n_clicks:
        standings_df = get_current_standings()
        return dcc.send_data_frame(standings_df.to_csv, "nfl_standings.csv", index=False)

@app.callback(
    Output("download-excel", "data"),
    Input("export-excel-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_excel(n_clicks):
    if n_clicks:
        try:
            with pd.ExcelWriter("nfl_complete_report.xlsx", engine='openpyxl') as writer:
                get_current_standings().to_excel(writer, sheet_name='Standings', index=False)
                
                conn = get_db_connection()
                if conn:
                    picks_df = pd.read_sql_query("SELECT * FROM picks", conn)
                    conn.close()
                    picks_df.to_excel(writer, sheet_name='All Picks', index=False)
            
            return dcc.send_file("nfl_complete_report.xlsx")
        except Exception as e:
            print(f"Excel export error: {e}")
            return None

# Last updated callback
@app.callback(
    Output('last-updated-info', 'children'),
    [Input('upload-status', 'children'), Input('update-status', 'children'), Input('main-tabs', 'active_tab')]
)
def show_last_updated(upload_status, update_status, active_tab):
    try:
        info_cards = []
        
        if os.path.exists('last_upload.txt'):
            with open('last_upload.txt', 'r') as f:
                last_upload = f.read().strip()
            info_cards.append(
                dbc.Badge(f"Picks last uploaded: {last_upload.split(',')[0]}", color="info", className="me-2")
            )
        
        if os.path.exists('last_results_update.txt'):
            with open('last_results_update.txt', 'r') as f:
                last_update = f.read().strip()
            info_cards.append(
                dbc.Badge(f"Results last updated: {last_update}", color="secondary")
            )
        
        return info_cards
    except:
        return []

# Main tab callback
@app.callback(
    Output("tab-content", "children"),
    [Input("main-tabs", "active_tab"), Input('update-btn', 'n_clicks'), Input('upload-status', 'children')]
)
def render_tab_content(active_tab, n_clicks, upload_status):
    if active_tab == "leaderboard":
        return render_leaderboard_tab()
    elif active_tab == "weekly_records":
        return render_weekly_records_tab()
    elif active_tab == "weekly":
        return render_weekly_tab()
    elif active_tab == "teams":
        return render_teams_tab()

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
            losses = 0
            total_games = len(person_picks)
            
            for _, row in person_picks.iterrows():
                if row[person_pick_col] == row['actual_winner']:
                    wins += 1
                else:
                    losses += 1
            
            win_pct = (wins / total_games * 100) if total_games > 0 else 0
            
            standings.append({
                'Rank': 0,
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

# Leaderboard tab
def render_leaderboard_tab():
    standings_df = get_current_standings()
    
    if standings_df.empty:
        return dbc.Alert("No game results available yet. Upload picks and update results to see standings.", color="info")
    
    return dbc.Card([
        dbc.CardHeader([
            html.H4([
                html.I(className="fas fa-list-ol me-2"),
                "Current Standings"
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
                    }
                ],
                style_table={'overflowX': 'auto'}
            )
        ])
    ])

# Placeholder functions for other tabs
def render_weekly_records_tab():
    return dbc.Alert("Weekly records functionality will be added soon!", color="info")

def render_weekly_tab():
    return dbc.Alert("Weekly picks view will be added soon!", color="info")

def render_teams_tab():
    return dbc.Alert("Team performance analysis will be added soon!", color="info")

# Server setup
server = app.server

if __name__ == '__main__':
    app.run(debug=True)