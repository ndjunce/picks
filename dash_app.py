import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from nfl_picks_automator import update_picks
import sqlite3

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("🏈 NFL Picks Tracker", className="text-center mb-4 text-primary"),
            html.Hr()
        ], width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Button("🔄 Update with Latest Results", id='update-btn', color='success', size="lg", className="mb-4 w-100"),
            html.Div(id='status', className="mb-4")
        ], width=12)
    ]),
    
    dbc.Tabs([
        dbc.Tab(label="📊 Cumulative Results", tab_id="cumulative"),
        dbc.Tab(label="📅 Weekly Picks", tab_id="weekly"),
        dbc.Tab(label="🏟️ Team Performance", tab_id="teams")
    ], id="main-tabs", active_tab="cumulative", className="mb-4"),
    
    html.Div(id="tab-content")
], fluid=True)

@app.callback(
    Output('status', 'children'),
    Input('update-btn', 'n_clicks')
)
def update_status(n_clicks):
    if not n_clicks:
        return ""
    
    try:
        update_picks()
        return dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            "Data updated successfully!"
        ], color="success", dismissable=True, duration=4000)
    except Exception as e:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Update failed: {str(e)}"
        ], color="danger", dismissable=True)

@app.callback(
    Output("tab-content", "children"),
    [Input("main-tabs", "active_tab"), Input('update-btn', 'n_clicks')]
)
def render_tab_content(active_tab, n_clicks):
    if active_tab == "cumulative":
        return render_cumulative_tab()
    elif active_tab == "weekly":
        return render_weekly_tab()
    elif active_tab == "teams":
        return render_teams_tab()

def render_cumulative_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM cumulative", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                "No data available. Click 'Update with Latest Results' to load your picks data."
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
                    page_size=20
                )
            ])
        ])
    except Exception as e:
        return dbc.Alert(f"Error loading cumulative data: {str(e)}", color="danger")

def render_weekly_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks ORDER BY week, game_id", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No weekly picks data available.", color="info")
        
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
    
    # Create picks table
    display_data = []
    people_cols = ['bobby_pick', 'chet_pick', 'clyde_pick', 'henry_pick', 'riley_pick', 'nick_pick']
    
    for _, row in week_df.iterrows():
        game_row = {
            'Away Team': row['away_team'],
            'Home Team': row['home_team']
        }
        
        for col in people_cols:
            person_name = col.replace('_pick', '').title()
            pick = row[col]
            if pick == 'Away':
                game_row[person_name] = f"✓ {row['away_team']}"
            elif pick == 'Home':
                game_row[person_name] = f"✓ {row['home_team']}"
            else:
                game_row[person_name] = '-'
        
        # Add actual winner
        if pd.notna(row['actual_winner']):
            if row['actual_winner'] == 'Away':
                game_row['🏆 Winner'] = row['away_team']
            elif row['actual_winner'] == 'Home':
                game_row['🏆 Winner'] = row['home_team']
            else:
                game_row['🏆 Winner'] = row['actual_winner']
        else:
            game_row['🏆 Winner'] = 'TBD'
        
        display_data.append(game_row)
    
    picks_df = pd.DataFrame(display_data)
    
    # Add tiebreaker info note
    tiebreaker_info = dbc.Alert([
        html.I(className="fas fa-info-circle me-2"),
        html.Strong("Tiebreaker: "),
        "The number below each person's name represents their guess for the total points in the final game of the week."
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
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            },
            # Highlight correct picks in green
            {
                'if': {
                    'filter_query': '{🏆 Winner} contains "✓"',
                    'column_id': ['Bobby', 'Chet', 'Clyde', 'Henry', 'Riley', 'Nick']
                },
                'backgroundColor': '#d4edda',
                'color': '#155724'
            }
        ],
        style_data={
            'border': '1px solid #dee2e6'
        },
        page_size=20
    )
    
    return [tiebreaker_info, picks_table]

def render_teams_tab():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return dbc.Alert("No completed games data available.", color="info")
        
        # Calculate team breakdown
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        team_breakdown = []
        
        for person in people:
            person_pick_col = f'{person}_pick'
            if person_pick_col not in df.columns:
                continue
                
            person_df = df[df[person_pick_col].notna()].copy()
            all_teams = set(person_df['away_team'].tolist() + person_df['home_team'].tolist())
            
            for team in all_teams:
                team_picks = person_df[
                    ((person_df['away_team'] == team) & (person_df[person_pick_col] == 'Away')) |
                    ((person_df['home_team'] == team) & (person_df[person_pick_col] == 'Home'))
                ]
                
                if len(team_picks) > 0:
                    wins = len(team_picks[team_picks['actual_winner'] == team_picks[person_pick_col]])
                    total_games = len(team_picks)
                    losses = total_games - wins
                    win_pct = (wins / total_games * 100) if total_games > 0 else 0
                    
                    # Add performance indicator
                    if win_pct >= 70:
                        performance = "🔥 Hot"
                    elif win_pct >= 50:
                        performance = "✅ Good"
                    else:
                        performance = "❄️ Cold"
                    
                    team_breakdown.append({
                        'Person': person.title(),
                        'Team': team,
                        'W-L': f"{wins}-{losses}",
                        'Win %': f"{win_pct:.1f}%",
                        'Total Picks': total_games,
                        'Performance': performance
                    })
        
        if not team_breakdown:
            return dbc.Alert("No team performance data available.", color="info")
        
        breakdown_df = pd.DataFrame(team_breakdown)
        breakdown_df = breakdown_df.sort_values(['Person', 'Total Picks'], ascending=[True, False])
        
        return dbc.Card([
            dbc.CardHeader([
                html.H4([
                    html.I(className="fas fa-chart-bar me-2"),
                    "Team Performance Analysis"
                ], className="mb-0")
            ]),
            dbc.CardBody([
                dbc.Alert([
                    html.I(className="fas fa-lightbulb me-2"),
                    html.Strong("Performance Guide: "),
                    "🔥 Hot (≥70%), ✅ Good (50-69%), ❄️ Cold (<50%)"
                ], color="info", className="mb-3"),
                
                dash_table.DataTable(
                    data=breakdown_df.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in breakdown_df.columns],
                    style_cell={
                        'textAlign': 'center',
                        'padding': '10px',
                        'fontFamily': 'Arial, sans-serif'
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
                        # Color code performance
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
                        }
                    ],
                    style_data={
                        'border': '1px solid #dee2e6'
                    },
                    sort_action="native",
                    filter_action="native",
                    page_size=30
                )
            ])
        ])
    except Exception as e:
        return dbc.Alert(f"Error loading team performance data: {str(e)}", color="danger")

server = app.server

if __name__ == '__main__':
    app.run(debug=True)