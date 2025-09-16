# NEW: Enhanced Pick Trends Tab
def render_pick_trends_tab():
    """Comprehensive pick trends analysis"""
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No picks data available.", color="info")
        
        # Calculate various trend analyses
        favorite_teams = calculate_favorite_teams(df)
        home_away_trends = calculate_home_away_preferences(df)
        team_success_rates = calculate_team_success_rates(df)
        
        return [
            # Favorite Teams Section
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-heart me-2"),
                                "Most & Least Picked Teams"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            create_favorite_teams_chart(favorite_teams)
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            # Home vs Away Preferences
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-home me-2"),
                                "Home vs Away Preferences"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            create_home_away_chart(home_away_trends)
                        ])
                    ])
                ], width=12, lg=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-percentage me-2"),
                                "Team Success Rates"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            create_team_success_display(team_success_rates)
                        ])
                    ])
                ], width=12, lg=6)
            ], className="mb-4"),
            
            # Detailed Pick Frequency Table
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📊 Detailed Pick Frequency by Player"),
                        dbc.CardBody([
                            create_pick_frequency_table(df)
                        ])
                    ])
                ], width=12)
            ])
        ]
        
    except Exception as e:
        return dbc.Alert(f"Error loading pick trends: {str(e)}", color="danger")

def calculate_favorite_teams(df):
    """Calculate which teams each player picks most/least often"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
    team_picks = {}
    
    for person in people:
        person_pick_col = f'{person}_pick'
        team_counts = {}
        
        # Initialize all teams with 0 picks
        for team in NFL_TEAMS:
            team_counts[team] = 0
        
        person_df = df[df[person_pick_col].notna()]
        
        for _, row in person_df.iterrows():
            if row[person_pick_col] == 'Away':
                team_counts[row['away_team']] += 1
            elif row[person_pick_col] == 'Home':
                team_counts[row['home_team']] += 1
        
        team_picks[person.title()] = team_counts
    
    return team_picks

def create_favorite_teams_chart(favorite_teams):
    """Create a chart showing favorite teams for each player"""
    if not favorite_teams:
        return html.P("No team preference data available.")
    
    # Find top 3 most picked and least picked teams for each player
    summary_data = []
    
    for player, teams in favorite_teams.items():
        sorted_teams = sorted(teams.items(), key=lambda x: x[1], reverse=True)
        
        # Get teams with picks > 0 for most picked
        most_picked = [f"{team} ({picks})" for team, picks in sorted_teams[:3] if picks > 0]
        
        # Get teams with 0 picks for least picked (or lowest if all have picks)
        least_picked_candidates = [team for team, picks in sorted_teams if picks == 0]
        if least_picked_candidates:
            least_picked = least_picked_candidates[:3]
        else:
            least_picked = [team for team, picks in sorted_teams[-3:]]
        
        summary_data.append({
            'Player': player,
            'Most Picked': ', '.join(most_picked) if most_picked else 'None',
            'Never Picked': ', '.join(least_picked) if least_picked else 'All teams picked'
        })
    
    return dash_table.DataTable(
        data=summary_data,
        columns=[
            {"name": "Player", "id": "Player"},
            {"name": "🔥 Most Picked", "id": "Most Picked"},
            {"name": "❄️ Never/Rarely Picked", "id": "Never Picked"}
        ],
        style_cell={
            'textAlign': 'left',
            'padding': '12px',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '12px',
            'whiteSpace': 'normal',
            'height': 'auto'
        },
        style_header={
            'backgroundColor': '#6f42c1',
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'column_id': 'Player'},
                'backgroundColor': '#f8f9fa',
                'fontWeight': 'bold',
                'textAlign': 'center'
            }
        ],
        style_table={'overflowX': 'auto'}
    )

def calculate_home_away_preferences(df):
    """Calculate home vs away picking preferences"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
    home_away_data = []
    
    for person in people:
        person_pick_col = f'{person}_pick'
        person_df = df[df[person_pick_col].notna()]
        
        home_picks = len(person_df[person_df[person_pick_col] == 'Home'])
        away_picks = len(person_df[person_df[person_pick_col] == 'Away'])
        total_picks = home_picks + away_picks
        
        if total_picks > 0:
            home_pct = (home_picks / total_picks * 100)
            away_pct = (away_picks / total_picks * 100)
        else:
            home_pct = away_pct = 0
        
        home_away_data.append({
            'Player': person.title(),
            'Home': home_picks,
            'Away': away_picks,
            'Home %': home_pct,
            'Away %': away_pct
        })
    
    return home_away_data

def create_home_away_chart(home_away_data):
    """Create a chart showing home vs away preferences"""
    if not home_away_data:
        return html.P("No home/away preference data available.")
    
    df = pd.DataFrame(home_away_data)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Home',
        x=df['Player'],
        y=df['Home'],
        marker_color='lightblue',
        text=df['Home'],
        textposition='auto'
    ))
    
    fig.add_trace(go.Bar(
        name='Away',
        x=df['Player'],
        y=df['Away'],
        marker_color='lightcoral',
        text=df['Away'],
        textposition='auto'
    ))
    
    fig.update_layout(
        title='Home vs Away Pick Distribution',
        barmode='stack',
        margin=dict(l=0, r=0, t=40, b=0),
        font=dict(size=12)
    )
    fig.update_xaxes(title='Player')
    fig.update_yaxes(title='Number of Picks')
    
    return dcc.Graph(figure=fig, style={'height': '400px'})

def calculate_team_success_rates(df):
    """Calculate success rates when picking each team"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
    
    # Filter to only completed games
    completed_df = df[df['actual_winner'].notna()]
    
    team_success = []
    
    for person in people:
        person_pick_col = f'{person}_pick'
        person_df = completed_df[completed_df[person_pick_col].notna()]
        
        team_records = {}
        
        for team in NFL_TEAMS:
            # Find games where this person picked this team
            team_picks = person_df[
                ((person_df['away_team'] == team) & (person_df[person_pick_col] == 'Away')) |
                ((person_df['home_team'] == team) & (person_df[person_pick_col] == 'Home'))
            ]
            
            if len(team_picks) > 0:
                wins = 0
                for _, row in team_picks.iterrows():
                    if row['actual_winner'] == team or (
                        (row['actual_winner'] == 'Away' and row['away_team'] == team) or
                        (row['actual_winner'] == 'Home' and row['home_team'] == team)
                    ):
                        wins += 1
                
                win_rate = (wins / len(team_picks) * 100) if len(team_picks) > 0 else 0
                team_records[team] = {
                    'wins': wins,
                    'total': len(team_picks),
                    'rate': win_rate
                }
        
        # Find best and worst teams for this player
        if team_records:
            best_team = max(team_records.items(), key=lambda x: (x[1]['rate'], x[1]['total']))
            worst_team = min(team_records.items(), key=lambda x: (x[1]['rate'], -x[1]['total']))
            
            team_success.append({
                'Player': person.title(),
                'Best Team': f"{best_team[0]} ({best_team[1]['wins']}-{best_team[1]['total']-best_team[1]['wins']}, {best_team[1]['rate']:.0f}%)",
                'Worst Team': f"{worst_team[0]} ({worst_team[1]['wins']}-{worst_team[1]['total']-worst_team[1]['wins']}, {worst_team[1]['rate']:.0f}%)"
            })
    
    return team_success

def create_team_success_display(team_success_data):
    """Create display for team success rates"""
    if not team_success_data:
        return html.P("No team success data available.")
    
    return dash_table.DataTable(
        data=team_success_data,
        columns=[
            {"name": "Player", "id": "Player"},
            {"name": "🏆 Best Team", "id": "Best Team"},
            {"name": "💔 Worst Team", "id": "Worst Team"}
        ],
        style_cell={
            'textAlign': 'center',
            'padding': '12px',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '12px',
            'whiteSpace': 'normal',
            'height': 'auto'
        },
        style_header={
            'backgroundColor': '#20c997',
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

def create_pick_frequency_table(df):
    """Create detailed pick frequency table"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
    
    # Get top 10 mostimport dash
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
                }
                
                .btn-group .btn {
                    margin-bottom: 5px;
                    width: 100%;
                }
                
                h1 {
                    font-size: 1.5rem !important;
                }
                
                h3 {
                    font-size: 1.2rem !important;
                }
                
                h4 {
                    font-size: 1.1rem !important;
                }
                
                .dash-table-container {
                    font-size: 10px !important;
                }
                
                .dash-cell div {
                    max-width: 80px !important;
                    overflow: hidden !important;
                    text-overflow: ellipsis !important;
                    white-space: nowrap !important;
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
            html.H1("🏈 NFL Picks Tracker", className="text-center mb-4 text-primary"),
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
                    dbc.Button("🔄 Update with Latest Results", id='update-btn', color='success', size="lg", className="w-100"),
                    html.Div(id='update-status', className="mt-3")
                ])
            ], className="mb-4")
        ], width=12, md=6)
    ]),
    
    # Enhanced Export Controls
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📁 Export Options"),
                dbc.CardBody([
                    dbc.ButtonGroup([
                        dbc.Button([
                            html.I(className="fas fa-download me-2"),
                            "Export CSV"
                        ], id="export-csv-btn", color="success", size="sm"),
                        dbc.Button([
                            html.I(className="fas fa-file-excel me-2"),
                            "Export Excel"
                        ], id="export-excel-btn", color="primary", size="sm"),
                        dbc.Button([
                            html.I(className="fas fa-chart-line me-2"),
                            "Download Charts"
                        ], id="export-charts-btn", color="info", size="sm"),
                        dbc.Button([
                            html.I(className="fas fa-file-pdf me-2"),
                            "Export Report"
                        ], id="export-report-btn", color="warning", size="sm")
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
        dbc.Tab(label="🏆 Leaderboard", tab_id="leaderboard"),
        dbc.Tab(label="📅 Weekly Records", tab_id="weekly_records"),
        dbc.Tab(label="📊 Statistics Dashboard", tab_id="stats_dashboard"),
        dbc.Tab(label="🎯 Tiebreaker Accuracy", tab_id="tiebreaker"),
        dbc.Tab(label="📈 Pick Trends", tab_id="pick_trends"),
        dbc.Tab(label="📝 Weekly Summaries", tab_id="weekly_summaries"),
        dbc.Tab(label="📅 Weekly Picks", tab_id="weekly"),
        dbc.Tab(label="🏟️ Team Performance", tab_id="teams")
    ], id="main-tabs", active_tab="leaderboard", className="mb-4"),
    
    html.Div(id="tab-content"),
    
    # Hidden divs for downloads
    dcc.Download(id="download-csv"),
    dcc.Download(id="download-excel"),
    dcc.Download(id="download-charts"),
    dcc.Download(id="download-report")
], fluid=True, style={'padding': '10px', 'maxWidth': '100%'})

# Enhanced export callbacks
@app.callback(
    Output("download-report", "data"),
    Input("export-report-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_comprehensive_report(n_clicks):
    if n_clicks:
        try:
            # Create comprehensive Excel report with all data
            with pd.ExcelWriter("nfl_comprehensive_report.xlsx", engine='openpyxl') as writer:
                # Current standings
                standings_df = get_current_standings()
                if not standings_df.empty:
                    standings_df.to_excel(writer, sheet_name='Current Standings', index=False)
                
                # Weekly records
                weekly_records_df = get_weekly_records_data()
                if not weekly_records_df.empty:
                    weekly_records_df.to_excel(writer, sheet_name='Weekly Records', index=False)
                
                # All picks data
                conn = sqlite3.connect('picks.db', check_same_thread=False)
                picks_df = pd.read_sql_query("SELECT * FROM picks", conn)
                
                if not picks_df.empty:
                    picks_df.to_excel(writer, sheet_name='All Picks', index=False)
                
                # Tiebreaker data
                tiebreaker_df = pd.read_sql_query("SELECT * FROM picks WHERE actual_total_points IS NOT NULL", conn)
                if not tiebreaker_df.empty:
                    tiebreaker_stats = calculate_tiebreaker_accuracy(tiebreaker_df)
                    if tiebreaker_stats['leaderboard']:
                        pd.DataFrame(tiebreaker_stats['leaderboard']).to_excel(writer, sheet_name='Tiebreaker Accuracy', index=False)
                
                conn.close()
            
            return dcc.send_file("nfl_comprehensive_report.xlsx")
        except Exception as e:
            print(f"Report export error: {e}")
            return None

@app.callback(
    Output("download-charts", "data"),
    Input("export-charts-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_charts(n_clicks):
    if n_clicks:
        try:
            standings_df = get_current_standings()
            if not standings_df.empty:
                # Create and save chart as HTML
                fig = create_win_percentage_chart(standings_df)
                fig.write_html("nfl_charts.html")
                return dcc.send_file("nfl_charts.html")
        except Exception as e:
            print(f"Chart export error: {e}")
            return None

# Existing upload callback (unchanged)
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
            import os
            import time
            time.sleep(0.5)
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
        except Exception as cleanup_error:
            print(f"Warning: Could not delete temporary file: {cleanup_error}")
        
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

# Existing update callback (unchanged)
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
            # Create Excel file with multiple sheets
            with pd.ExcelWriter("nfl_complete_report.xlsx", engine='openpyxl') as writer:
                get_current_standings().to_excel(writer, sheet_name='Standings', index=False)
                
                conn = sqlite3.connect('picks.db', check_same_thread=False)
                picks_df = pd.read_sql_query("SELECT * FROM picks", conn)
                conn.close()
                
                picks_df.to_excel(writer, sheet_name='All Picks', index=False)
                
                # Weekly records
                weekly_records_df = get_weekly_records_data()
                if not weekly_records_df.empty:
                    weekly_records_df.to_excel(writer, sheet_name='Weekly Records', index=False)
            
            return dcc.send_file("nfl_complete_report.xlsx")
        except Exception as e:
            print(f"Excel export error: {e}")
            return None

# Last updated callback (unchanged)
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
                dbc.Badge(f"Picks last uploaded: {last_upload}", color="info", className="me-2")
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

# Enhanced main tab callback
@app.callback(
    Output("tab-content", "children"),
    [Input("main-tabs", "active_tab"), Input('update-btn', 'n_clicks'), Input('upload-status', 'children')]
)
def render_tab_content(active_tab, n_clicks, upload_status):
    if active_tab == "leaderboard":
        return render_leaderboard_tab()
    elif active_tab == "weekly_records":
        return render_weekly_records_tab()
    elif active_tab == "stats_dashboard":
        return render_stats_dashboard_tab()
    elif active_tab == "tiebreaker":
        return render_tiebreaker_tab()
    elif active_tab == "pick_trends":
        return render_pick_trends_tab()
    elif active_tab == "weekly_summaries":
        return render_weekly_summaries_tab()
    elif active_tab == "weekly":
        return render_weekly_tab()
    elif active_tab == "teams":
        return render_teams_tab()

# Helper function to get data (unchanged)
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

# Enhanced leaderboard with charts
def render_leaderboard_tab():
    standings_df = get_current_standings()
    
    if standings_df.empty:
        return dbc.Alert("No game results available yet. Upload picks and update results to see standings.", color="info")
    
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
                        html.P(player['Win % Display'], className="text-center text-muted mb-0")
                    ], className="py-4")
                ], color=colors[i], outline=True, className="h-100")
            ], width=12, md=4)
        )
    
    return [
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
                            ],
                            style_table={'overflowX': 'auto'}
                        )
                    ])
                ])
            ], width=12)
        ])
    ]

def create_win_percentage_chart(standings_df):
    """Create a bar chart showing win percentages"""
    fig = px.bar(
        standings_df.sort_values('Win %', ascending=True),
        x='Win %',
        y='Player',
        orientation='h',
        title='Win Percentage by Player',
        text='Win % Display',
        color='Win %',
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
    """Create a bar chart comparing total wins"""
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

# FIXED Weekly Records function
def get_weekly_records_data():
    """Get weekly records data - this was the issue!"""
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
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
        
        return pd.DataFrame(weekly_records)
        
    except Exception as e:
        print(f"Error in get_weekly_records_data: {e}")
        return pd.DataFrame()

def render_weekly_records_tab():
    """FIXED Weekly Records Tab"""
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
                        dbc.CardHeader("📈 Weekly Performance Trends"),
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

def create_weekly_trends_chart():
    """Create a line chart showing weekly win percentage trends"""
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return go.Figure()
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
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
                    wins = len(person_week_picks[person_week_picks[person_pick_col] == person_week_picks['actual_winner']])
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

# NEW: Statistics Dashboard Tab
def render_stats_dashboard_tab():
    """Comprehensive statistics dashboard"""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 Statistics Dashboard"),
                dbc.CardBody([
                    html.H4("🚧 Coming Soon!", className="text-center text-muted"),
                    html.P("Head-to-head comparisons, streak tracking, and best/worst weeks analysis will be available here.", 
                           className="text-center text-muted")
                ])
            ])
        ], width=12)
    ])

# NEW: Tiebreaker Accuracy Tab
def render_tiebreaker_tab():
    """Tiebreaker accuracy analysis"""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🎯 Tiebreaker Accuracy"),
                dbc.CardBody([
                    html.H4("🚧 Coming Soon!", className="text-center text-muted"),
                    html.P("Analysis of total points predictions and tiebreaker accuracy will be available here.", 
                           className="text-center text-muted")
                ])
            ])
        ], width=12)
    ])

# NEW: Pick Trends Tab
def render_pick_trends_tab():
    """Pick trends analysis"""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📈 Pick Trends"),
                dbc.CardBody([
                    html.H4("🚧 Coming Soon!", className="text-center text-muted"),
                    html.P("Analysis of which teams each person picks most/least often will be available here.", 
                           className="text-center text-muted")
                ])
            ])
        ], width=12)
    ])

# NEW: Weekly Summaries Tab
def render_weekly_summaries_tab():
    """Weekly summaries with automated recaps"""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📝 Weekly Summaries"),
                dbc.CardBody([
                    html.H4("🚧 Coming Soon!", className="text-center text-muted"),
                    html.P("Automated recaps of each week's results and highlights will be available here.", 
                           className="text-center text-muted")
                ])
            ])
        ], width=12)
    ])

# Keep existing functions (render_weekly_tab, render_teams_tab, etc.)
def render_weekly_tab():
    """Your existing weekly tab function - keeping it unchanged"""
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
    """Your existing create_week_content function - keeping it unchanged"""
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

def render_teams_tab():
    """Your existing teams tab function - keeping it unchanged"""
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No picks data available. Upload your Excel file first.", color="info")
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        team_breakdown = []
        
        for person in people:
            person_pick_col = f'{person}_pick'
            if person_pick_col not in df.columns:
                continue
            
            person_df = df[df[person_pick_col].notna()].copy()
            
            for team in NFL_TEAMS:
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
                
                team_breakdown.append({
                    'Person': person.title(),
                    'Team': team,
                    'Record': record,
                    'Win %': f"{win_pct:.1f}%" if completed_games > 0 else "0.0%",
                    'Total Picks': total_picks,
                    'Completed': completed_games,
                    'Performance': performance
                })
        
        breakdown_df = pd.DataFrame(team_breakdown)
        breakdown_df = breakdown_df.sort_values(['Person', 'Total Picks', 'Win %'], ascending=[True, False, False])
        
        return dbc.Card([
            dbc.CardHeader([
                html.H4([
                    html.I(className="fas fa-chart-bar me-2"),
                    "Complete Team Performance Analysis"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Alert([
                    html.I(className="fas fa-lightbulb me-2"),
                    html.Strong("Performance Guide: "),
                    "🔥 Hot (≥70%), ✅ Good (50-69%), ❄️ Cold (<50%), ⏳ Pending (has picks but no results), ⚪ No picks"
                ], color="info", className="mb-3"),
                
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    html.Strong("Record Format: "),
                    "Wins-Losses-Pending (if any games are still pending)"
                ], color="secondary", className="mb-3"),
                
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
                        'fontWeight': 'bold',
                        'border': '1px solid #c0392b'
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
                    page_size=50
                )
            ])
        ])
    except Exception as e:
        return dbc.Alert(f"Error loading team performance data: {str(e)}", color="danger")

def render_cumulative_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM cumulative", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                "No data available. Upload your picks Excel file to get started."
            ], color="info")
        
        return dbc.Card([
            dbc.CardHeader([
                html.H4([
                    html.I(className="fas fa-trophy me-2"),
                    "Season Standings"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dash_table.DataTable(
                    data=df.to_dict('records'),
                    columns=[{"name": col.title(), "id": col} for col in df.columns],
                    style_cell={
                        'textAlign': 'center',
                        'padding': '12px',
                        'fontFamily': 'Arial, sans-serif'
                    },
                    style_header={
                        'backgroundColor': '#2c3e50',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'border': '1px solid #34495e'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f8f9fa'
                        },
                        {
                            'if': {'row_index': 'even'},
                            'backgroundColor': 'white'
                        }
                    ],
                    style_data={
                        'border': '1px solid #dee2e6'
                    },
                    style_table={'overflowX': 'auto'},
                    page_size=20
                )
            ])
        ])
    except Exception as e:
        return dbc.Alert(f"Error loading cumulative data: {str(e)}", color="danger")

server = app.server

if __name__ == '__main__':
    app.run(debug=True)