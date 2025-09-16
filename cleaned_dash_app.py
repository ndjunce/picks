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

# Define all 32 NFL teams (single definition)
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
                
                # Better mobile optimization
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
                
                /* Improve button layout on mobile */
                .btn-group {
                    gap: 5px;
                }
                
                .btn-sm {
                    font-size: 0.75rem !important;
                    padding: 4px 8px !important;
                }
                
                /* Better card spacing */
                .card-body {
                    padding: 0.75rem !important;
                }
                
                /* Responsive tabs */
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
                dbc.CardHeader("📊 Export Options"),
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
        dbc.Tab(label="📄 Weekly Summaries", tab_id="weekly_summaries"),
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

# Enhanced Pick Trends Tab - COMPLETED
def render_pick_trends_tab():
    """Comprehensive pick trends analysis"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")
        
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
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
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
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
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
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    
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
    """Create detailed pick frequency table - COMPLETED"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
    
    # Calculate team pick frequencies
    frequency_data = []
    for person in people:
        person_pick_col = f'{person}_pick'
        person_df = df[df[person_pick_col].notna()]
        
        team_counts = {}
        for team in NFL_TEAMS:
            count = len(person_df[
                ((person_df['away_team'] == team) & (person_df[person_pick_col] == 'Away')) |
                ((person_df['home_team'] == team) & (person_df[person_pick_col] == 'Home'))
            ])
            if count > 0:
                team_counts[team] = count
        
        # Get top 5 most picked teams
        top_teams = sorted(team_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        frequency_data.append({
            'Player': person.title(),
            'Top Teams': ', '.join([f"{team} ({count})" for team, count in top_teams]) if top_teams else 'No picks yet'
        })
    
    return dash_table.DataTable(
        data=frequency_data,
        columns=[
            {"name": "Player", "id": "Player"},
            {"name": "Most Picked Teams", "id": "Top Teams"}
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

# Tiebreaker accuracy function - COMPLETED
def calculate_tiebreaker_accuracy(df):
    """Calculate tiebreaker prediction accuracy"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
    tiebreaker_stats = {'leaderboard': [], 'detailed': []}
    
    for person in people:
        person_guess_col = f'{person}_total_guess'
        person_picks = df[df[person_guess_col].notna() & df['actual_total_points'].notna()]
        
        if len(person_picks) == 0:
            continue
        
        total_accuracy = 0
        predictions = []
        
        for _, row in person_picks.iterrows():
            guess = int(row[person_guess_col])
            actual = int(row['actual_total_points'])
            difference = abs(guess - actual)
            
            total_accuracy += difference
            predictions.append({
                'Week': row['week'],
                'Game': f"{row['away_team']} @ {row['home_team']}",
                'Prediction': guess,
                'Actual': actual,
                'Difference': difference
            })
        
        avg_accuracy = total_accuracy / len(person_picks) if len(person_picks) > 0 else 0
        
        tiebreaker_stats['leaderboard'].append({
            'Player': person.title(),
            'Predictions': len(person_picks),
            'Avg Difference': f"{avg_accuracy:.1f}",
            'Total Off By': total_accuracy
        })
        
        tiebreaker_stats['detailed'].extend([{
            'Player': person.title(),
            **pred
        } for pred in predictions])
    
    # Sort by average accuracy (lower is better)
    tiebreaker_stats['leaderboard'] = sorted(
        tiebreaker_stats['leaderboard'], 
        key=lambda x: float(x['Avg Difference'])
    )
    
    return tiebreaker_stats

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
                conn = get_db_connection()
                if conn:
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
        
        # Save to persistent filename instead of temporary
        persistent_filename = f"uploaded_picks_{filename}"
        with open(persistent_filename, 'wb') as f:
            f.write(decoded)
        
        from nfl_picks_automator import import_from_excel
        import_from_excel(persistent_filename)
        
        # Keep the file for persistence (don't delete it)
        # Store metadata about the upload
        with open('last_upload.txt', 'w') as f:
            upload_info = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{filename},{persistent_filename}"
            f.write(upload_info)
        
        return dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"Successfully uploaded and processed {filename}! File saved for persistence."
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
            # Create Excel file with multiple sheets
            with pd.ExcelWriter("nfl_complete_report.xlsx", engine='openpyxl') as writer:
                get_current_standings().to_excel(writer, sheet_name='Standings', index=False)
                
                conn = get_db_connection()
                if conn:
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

# Helper function to get data with error handling
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

# Weekly Records function - FIXED
def get_weekly_records_data():
    """Get weekly records data"""
    try:
        conn = get_db_connection()
        if not conn:
            return pd.DataFrame()
        
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
    """Weekly Records Tab - FIXED"""
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
        conn = get_db_connection()
        if not conn:
            return go.Figure()
        
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

# Enhanced Tiebreaker Tab with automatic calculation
def render_tiebreaker_tab():
    """Tiebreaker accuracy analysis with live tiebreaker calculation"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")
        
        # Get tiebreaker accuracy data
        tiebreaker_df = pd.read_sql_query("SELECT * FROM picks WHERE actual_total_points IS NOT NULL", conn)
        
        # Get current live tiebreaker situation
        live_tiebreaker_df = pd.read_sql_query("SELECT * FROM picks WHERE actual_total_points IS NULL AND (bobby_total_guess IS NOT NULL OR chet_total_guess IS NOT NULL OR clyde_total_guess IS NOT NULL OR henry_total_guess IS NOT NULL OR nick_total_guess IS NOT NULL OR riley_total_guess IS NOT NULL)", conn)
        
        conn.close()
        
        components = []
        
        # Live Tiebreaker Calculation
        if not live_tiebreaker_df.empty:
            live_tiebreaker_info = calculate_live_tiebreaker(live_tiebreaker_df)
            if live_tiebreaker_info:
                components.append(
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.H4([
                                        html.I(className="fas fa-clock me-2"),
                                        "Live Tiebreaker Situation"
                                    ], className="mb-0")
                                ]),
                                dbc.CardBody(live_tiebreaker_info)
                            ], color="warning", outline=True)
                        ], width=12)
                    ], className="mb-4")
                )
        
        # Historical Tiebreaker Accuracy
        if not tiebreaker_df.empty:
            tiebreaker_stats = calculate_tiebreaker_accuracy(tiebreaker_df)
            
            components.append(
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H4([
                                    html.I(className="fas fa-target me-2"),
                                    "Tiebreaker Accuracy Leaderboard"
                                ], className="mb-0")
                            ]),
                            dbc.CardBody([
                                dbc.Alert([
                                    html.I(className="fas fa-info-circle me-2"),
                                    html.Strong("Lower is better! "),
                                    "Average difference from actual total points."
                                ], color="info", className="mb-3"),
                                
                                dash_table.DataTable(
                                    data=tiebreaker_stats['leaderboard'],
                                    columns=[
                                        {"name": "Player", "id": "Player"},
                                        {"name": "Predictions Made", "id": "Predictions"},
                                        {"name": "Avg Points Off", "id": "Avg Difference"},
                                        {"name": "Total Points Off", "id": "Total Off By"}
                                    ],
                                    style_cell={
                                        'textAlign': 'center',
                                        'padding': '15px',
                                        'fontFamily': 'Arial, sans-serif',
                                        'fontSize': '14px'
                                    },
                                    style_header={
                                        'backgroundColor': '#dc3545',
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
                            ])
                        ])
                    ], width=12)
                ])
            )
        
        if not components:
            return dbc.Alert("No tiebreaker data available yet.", color="info")
        
        return components
        
    except Exception as e:
        return dbc.Alert(f"Error loading tiebreaker data: {str(e)}", color="danger")

def calculate_live_tiebreaker(live_df):
    """Calculate live tiebreaker situation and what each person needs"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    
    # Get current standings to determine who's in the running
    standings_df = get_current_standings()
    if standings_df.empty:
        return None
    
    # Find potential winners (top win percentage with small margin)
    top_win_pct = standings_df.iloc[0]['Win %']
    contenders = standings_df[standings_df['Win %'] >= top_win_pct - 5]  # Within 5% of leader
    
    tiebreaker_info = []
    
    for _, row in live_df.iterrows():
        game_info = f"{row['away_team']} @ {row['home_team']}"
        
        predictions = []
        for person in people:
            guess_col = f'{person}_total_guess'
            if pd.notna(row[guess_col]):
                predictions.append({
                    'Player': person.title(),
                    'Prediction': int(row[guess_col])
                })
        
        if predictions:
            tiebreaker_info.append(
                html.Div([
                    html.H5(f"Tiebreaker Game: {game_info}", className="text-primary mb-3"),
                    html.P("Total points predictions:", className="mb-2"),
                    html.Ul([
                        html.Li(f"{pred['Player']}: {pred['Prediction']} points") 
                        for pred in predictions
                    ]),
                    html.Hr(),
                    html.P([
                        html.Strong("Current contenders: "),
                        ", ".join([f"{row['Player']} ({row['Win % Display']})" for _, row in contenders.iterrows()])
                    ], className="text-muted")
                ])
            )
    
    return tiebreaker_info

# Statistics Dashboard Tab - COMPLETED with streaks
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
                            html.H4([
                                html.I(className="fas fa-fire me-2"),
                                "Current Streaks"
                            ], className="mb-0")
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
                            html.H4([
                                html.I(className="fas fa-chart-line me-2"),
                                "Best & Worst Week Performances"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            create_best_worst_weeks_display(best_worst_weeks)
                        ])
                    ])
                ], width=12, lg=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-users me-2"),
                                "Head-to-Head Records"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
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
            correct = row[person_pick_col] == row['actual_winner']
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
            {"name": "🔥 Current Streak", "id": "Current Streak"},
            {"name": "📈 Best Win Streak", "id": "Longest Win Streak"},
            {"name": "📉 Worst Loss Streak", "id": "Longest Loss Streak"}
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
                wins = len(person_week_picks[person_week_picks[person_pick_col] == person_week_picks['actual_winner']])
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
            {"name": "🏆 Best Week", "id": "Best Week"},
            {"name": "💔 Worst Week", "id": "Worst Week"}
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
            person_correct = row[person_pick_col] == row['actual_winner']
            
            # Compare against each other player for this game
            for other_person in people:
                if other_person != person:
                    other_pick_col = f'{other_person}_pick'
                    if pd.notna(row[other_pick_col]):
                        other_correct = row[other_pick_col] == row['actual_winner']
                        
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
    )"),
                        html.Li("Best and worst performing weeks"),
                        html.Li("Consensus vs. contrarian pick analysis"),
                        html.Li("Monthly performance breakdowns")
                    ])
                ])
            ])
        ], width=12)
    ])

# Weekly Summaries Tab - COMPLETED with automated recaps
def render_weekly_summaries_tab():
    """Weekly summaries with automated recaps"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")
        
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL ORDER BY week, game_id", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No completed games available for weekly summaries.", color="info")
        
        weeks = sorted(df['week'].unique())
        
        tabs_content = []
        for week in weeks:
            week_df = df[df['week'] == week]
            summary_content = create_weekly_summary(week_df, week)
            
            tabs_content.append(
                dbc.Tab(label=f"Week {week}", tab_id=f"summary-week-{week}", children=[
                    html.Div(summary_content, className="mt-3")
                ])
            )
        
        return html.Div([
            dbc.Card([
                dbc.CardHeader([
                    html.H4([
                        html.I(className="fas fa-newspaper me-2"),
                        "Automated Weekly Summaries"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dbc.Tabs(tabs_content, id="summary-tabs", active_tab=f"summary-week-{weeks[-1]}" if weeks else None)
                ])
            ])
        ])
        
    except Exception as e:
        return dbc.Alert(f"Error loading weekly summaries: {str(e)}", color="danger")

def create_weekly_summary(week_df, week_num):
    """Create automated summary for a specific week"""
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    
    # Calculate week statistics
    week_stats = []
    for person in people:
        person_pick_col = f'{person}_pick'
        person_picks = week_df[week_df[person_pick_col].notna()]
        
        if len(person_picks) > 0:
            wins = len(person_picks[person_picks[person_pick_col] == person_picks['actual_winner']])
            total = len(person_picks)
            win_pct = (wins / total * 100) if total > 0 else 0
            
            week_stats.append({
                'Player': person.title(),
                'Wins': wins,
                'Total': total,
                'Win %': win_pct,
                'Record': f"{wins}-{total-wins}"
            })
    
    week_stats_df = pd.DataFrame(week_stats)
    week_stats_df = week_stats_df.sort_values('Win %', ascending=False)
    
    # Find week highlights
    best_performer = week_stats_df.iloc[0] if not week_stats_df.empty else None
    worst_performer = week_stats_df.iloc[-1] if not week_stats_df.empty else None
    
    # Calculate consensus picks (where most people agreed)
    consensus_picks = []
    upset_picks = []
    
    for _, row in week_df.iterrows():
        pick_counts = {'Home': 0, 'Away': 0}
        for person in people:
            person_pick = row[f'{person}_pick']
            if pd.notna(person_pick):
                pick_counts[person_pick] += 1
        
        total_picks = pick_counts['Home'] + pick_counts['Away']
        if total_picks > 0:
            consensus_pct = max(pick_counts.values()) / total_picks
            majority_pick = 'Home' if pick_counts['Home'] > pick_counts['Away'] else 'Away'
            
            game_info = f"{row['away_team']} @ {row['home_team']}"
            
            if consensus_pct >= 0.8:  # 80%+ agreement
                consensus_correct = majority_pick == row['actual_winner']
                consensus_picks.append({
                    'game': game_info,
                    'consensus': majority_pick,
                    'agreement': f"{consensus_pct:.0%}",
                    'correct': consensus_correct
                })
            
            # Check for upsets (consensus wrong)
            if consensus_pct >= 0.7 and majority_pick != row['actual_winner']:
                upset_picks.append({
                    'game': game_info,
                    'expected': majority_pick,
                    'actual': row['actual_winner']
                })
    
    return [
        # Week Performance Summary
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(f"Week {week_num} Performance Summary"),
                    dbc.CardBody([
                        dash_table.DataTable(
                            data=week_stats_df.to_dict('records'),
                            columns=[
                                {"name": "Player", "id": "Player"},
                                {"name": "Record", "id": "Record"},
                                {"name": "Win %", "id": "Win %", "format": {"specifier": ".1f"}}
                            ],
                            style_cell={'textAlign': 'center', 'padding': '10px'},
                            style_header={'backgroundColor': '#007bff', 'color': 'white'},
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 0},
                                    'backgroundColor': '#d4edda',
                                    'fontWeight': 'bold'
                                },
                                {
                                    'if': {'row_index': len(week_stats_df) - 1},
                                    'backgroundColor': '#f8d7da'
                                }
                            ]
                        )
                    ])
                ])
            ], width=12, lg=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Week Highlights"),
                    dbc.CardBody([
                        html.H6("Player of the Week:", className="text-success"),
                        html.P(f"{best_performer['Player']} ({best_performer['Record']}, {best_performer['Win %']:.1f}%)" if best_performer is not None else "No data"),
                        
                        html.H6("Needs Improvement:", className="text-danger"),
                        html.P(f"{worst_performer['Player']} ({worst_performer['Record']}, {worst_performer['Win %']:.1f}%)" if worst_performer is not None else "No data"),
                        
                        html.H6("Total Games:", className="text-info"),
                        html.P(f"{len(week_df)} games completed")
                    ])
                ])
            ], width=12, lg=6)
        ], className="mb-4"),
        
        # Consensus and Upsets
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Consensus Picks"),
                    dbc.CardBody([
                        html.P("Games where 80%+ of players agreed:") if consensus_picks else html.P("No strong consensus picks this week."),
                        html.Ul([
                            html.Li([
                                f"{pick['game']}: ",
                                html.Span(f"{pick['consensus']} ({pick['agreement']})", className="fw-bold"),
                                html.Span(" ✅" if pick['correct'] else " ❌", className="ms-2")
                            ]) for pick in consensus_picks
                        ]) if consensus_picks else html.Div()
                    ])
                ])
            ], width=12, lg=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Biggest Upsets"),
                    dbc.CardBody([
                        html.P("Games where the consensus was wrong:") if upset_picks else html.P("No major upsets this week!"),
                        html.Ul([
                            html.Li(f"{upset['game']}: Expected {upset['expected']}, got {upset['actual']}")
                            for upset in upset_picks
                        ]) if upset_picks else html.Div()
                    ])
                ])
            ], width=12, lg=6)
        ])
    ]

# Keep existing functions (render_weekly_tab, render_teams_tab, etc.) - unchanged from your original code
def render_weekly_tab():
    """Weekly picks tab"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")
        
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
    """Create content for individual week"""
    if week_df.empty:
        return html.P(f"No data for Week {week_num}")
    
    # Find the tiebreaker game (last game with tiebreaker predictions)
    tiebreaker_game_id = None
    tiebreaker_predictions = {}
    people_names = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    
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
    people_cols = ['bobby_pick', 'chet_pick', 'clyde_pick', 'henry_pick', 'nick_pick', 'riley_pick']
    
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
        
        # Add actual winner and total points with scores
        if pd.notna(row['actual_winner']):
            # Check if we have individual scores
            away_score = row.get('away_score', None)
            home_score = row.get('home_score', None)
            
            if pd.notna(away_score) and pd.notna(home_score):
                # Display with scores
                if row['actual_winner'] == 'Away':
                    winner_display = f"{row['away_team']} {int(away_score)}-{int(home_score)}"
                elif row['actual_winner'] == 'Home':
                    winner_display = f"{row['home_team']} {int(home_score)}-{int(away_score)}"
                else:
                    winner_display = f"{row['actual_winner']} ({int(away_score)}-{int(home_score)})"
            else:
                # Fallback to team names only
                if row['actual_winner'] == 'Away':
                    winner_display = row['away_team']
                elif row['actual_winner'] == 'Home':
                    winner_display = row['home_team']
                else:
                    winner_display = row['actual_winner']
            
            # If this game has tiebreaker predictions AND actual total points, show just the total
            has_any_tiebreaker = any(pd.notna(row[f'{person}_total_guess']) for person in people_names)
            if has_any_tiebreaker and pd.notna(row.get('actual_total_points')):
                total_points = int(row['actual_total_points'])
                game_row['🏆 Winner'] = f"{winner_display} (Total: {total_points})"
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
    for i, (_, row) in enumerate(week_df.iterrows()):
        if pd.notna(row['actual_winner']):
            for col in people_cols:
                person_name = col.replace('_pick', '').title()
                person_pick = row[col]
                actual_winner = row['actual_winner']
                
                if person_pick == actual_winner:
                    # Correct pick - green
                    style_data_conditional.append({
                        'if': {
                            'row_index': i,
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
                            'row_index': i,
                            'column_id': person_name
                        },
                        'backgroundColor': '#f8d7da',
                        'color': '#721c24',
                        'fontWeight': 'bold'
                    })
    
    # Create tiebreaker info
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
    """Team performance analysis"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")
        
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

# Server setup
server = app.server

if __name__ == '__main__':
    app.run(debug=True)