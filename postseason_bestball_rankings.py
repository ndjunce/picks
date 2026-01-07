"""
Postseason PPR Best Ball Rankings - Dash App
Displays playoffs rankings in NFC/AFC grid format (FantasyAlarm-style)
with your equation-based scores and external source comparisons.
"""

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import json
import os
from datetime import datetime

# PPR Scoring rules (from your equations)
PPR_SCORING = {
    "pass_yd": 1/25.0,
    "pass_td": 4.0,
    "int": -2.0,
    "rush_yd": 1/10.0,
    "rush_td": 6.0,
    "rec_yd": 1/10.0,
    "rec_td": 6.0,
    "rec": 1.0,
}

# NFL Playoff Teams - 2026
PLAYOFF_STRUCTURE = {
    "AFC": {
        "teams": ["KC", "BUF", "BAL", "HOU", "PIT", "LAC", "DEN"],
        "color": "#002C5C"  # AFC blue
    },
    "NFC": {
        "teams": ["PHI", "DET", "GB", "SF", "LAR", "TB", "WSH"],
        "color": "#002B36"  # NFC dark
    }
}

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

def load_playoff_rankings():
    """Load playoff rankings from JSON file."""
    base_dir = os.getcwd()
    json_path = os.path.join(base_dir, 'docs', 'postseason', 'playoff_players_2026.json')
    
    if os.path.exists(json_path):
        try:
            with open(json_path) as f:
                data = json.load(f)
            players = data.get('players', [])
            return pd.DataFrame(players)
        except Exception as e:
            print(f"Error loading playoff rankings: {e}")
    
    return pd.DataFrame()

def build_nfc_afc_grid():
    """Build NFC/AFC side-by-side grid layout (FantasyAlarm style)."""
    df = load_playoff_rankings()
    
    if df.empty:
        return dbc.Alert("No playoff rankings available.", color="warning")
    
    # Sort by total_points descending
    df = df.sort_values('total_points', ascending=False).reset_index(drop=True)
    
    # Create position-based groupings
    positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']
    
    # Build NFC and AFC DataFrames
    nfc_teams = PLAYOFF_STRUCTURE['NFC']['teams']
    afc_teams = PLAYOFF_STRUCTURE['AFC']['teams']
    
    df_nfc = df[df['team'].isin(nfc_teams)].copy()
    df_afc = df[df['team'].isin(afc_teams)].copy()
    
    tabs = []
    
    for pos in positions:
        df_nfc_pos = df_nfc[df_nfc['position'] == pos].head(15)
        df_afc_pos = df_afc[df_afc['position'] == pos].head(15)
        
        # Compute position ranks
        df_nfc_pos = df_nfc_pos.copy()
        df_nfc_pos['pos_rank'] = range(1, len(df_nfc_pos) + 1)
        df_afc_pos = df_afc_pos.copy()
        df_afc_pos['pos_rank'] = range(1, len(df_afc_pos) + 1)
        
        # Build card grid for each position
        nfc_cards = []
        afc_cards = []
        
        for _, row in df_nfc_pos.iterrows():
            nfc_cards.append(
                dbc.Card([
                    dbc.CardHeader([
                        html.Span(f"#{row['pos_rank']} ", className="badge badge-primary"),
                        html.Strong(row['player_name'])
                    ], style={'backgroundColor': '#f0f0f0'}),
                    dbc.CardBody([
                        html.Div([
                            html.Span(row['team'], className="badge badge-secondary me-2"),
                            html.Span(row['position'], className="badge badge-info")
                        ], className="mb-2"),
                        html.Small([
                            html.Div(f"PPR: {row['total_points']:.1f}", className="text-muted"),
                            html.Div(f"Games: {row['games_played']}", className="text-muted"),
                        ], style={'fontSize': '0.85rem'})
                    ])
                ], className="mb-2", style={'borderLeft': '4px solid #002C5C'})
            )
        
        for _, row in df_afc_pos.iterrows():
            afc_cards.append(
                dbc.Card([
                    dbc.CardHeader([
                        html.Span(f"#{row['pos_rank']} ", className="badge badge-danger"),
                        html.Strong(row['player_name'])
                    ], style={'backgroundColor': '#f0f0f0'}),
                    dbc.CardBody([
                        html.Div([
                            html.Span(row['team'], className="badge badge-secondary me-2"),
                            html.Span(row['position'], className="badge badge-info")
                        ], className="mb-2"),
                        html.Small([
                            html.Div(f"PPR: {row['total_points']:.1f}", className="text-muted"),
                            html.Div(f"Games: {row['games_played']}", className="text-muted"),
                        ], style={'fontSize': '0.85rem'})
                    ])
                ], className="mb-2", style={'borderLeft': '4px solid #002B36'})
            )
        
        # Create side-by-side layout
        grid_content = dbc.Row([
            dbc.Col([
                html.H5("NFC", className="text-center mb-3", style={'color': '#002B36', 'fontWeight': 'bold'}),
                html.Div(nfc_cards)
            ], xs=12, sm=12, md=6, lg=6, xl=6),
            dbc.Col([
                html.H5("AFC", className="text-center mb-3", style={'color': '#002C5C', 'fontWeight': 'bold'}),
                html.Div(afc_cards)
            ], xs=12, sm=12, md=6, lg=6, xl=6),
        ])
        
        tabs.append(dcc.Tab(label=f"{pos} ({len(df_nfc_pos)+len(df_afc_pos)})", value=pos, children=[
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.P(
                            f"Ranking equation: PPR scoring based on 2025 regular season performance for {pos}s in playoff teams.",
                            className="text-muted small"
                        ),
                    ]),
                    grid_content
                ])
            ])
        ]))
    
    # Add an "Overall" tab
    df_all = df.head(50)
    df_all['overall_rank'] = range(1, len(df_all) + 1)
    
    overall_rows = []
    for _, row in df_all.iterrows():
        conference = "NFC" if row['team'] in nfc_teams else "AFC"
        conf_badge = "secondary" if conference == "NFC" else "dark"
        overall_rows.append(
            dbc.Row([
                dbc.Col(html.Small(f"#{row['overall_rank']}"), width=1, className="text-muted fw-bold"),
                dbc.Col(html.Strong(row['player_name']), width=4),
                dbc.Col(html.Span(row['position'], className="badge badge-info"), width=1),
                dbc.Col(html.Span(row['team'], className="badge badge-secondary"), width=1),
                dbc.Col(html.Span(conference, className=f"badge badge-{conf_badge}"), width=1),
                dbc.Col(html.Small(f"{row['total_points']:.1f} PPR"), width=2, className="text-end"),
            ], className="mb-2 pb-2 border-bottom")
        )
    
    overall_tab = dcc.Tab(label="Overall Top 50", value="overall", children=[
        dbc.Card([
            dbc.CardBody([
                html.H5("Top 50 Players - All Positions"),
                html.Hr(),
                html.Div(overall_rows)
            ])
        ])
    ])
    
    tabs.insert(0, overall_tab)
    
    return dcc.Tabs(tabs, value="overall", id="rankings-tabs")

# App Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("🏈 Postseason PPR Best Ball Rankings", className="my-4"),
            html.P("NFC/AFC Grid Layout • Equation-Based Rankings • 2026 Playoff Teams", className="text-muted")
        ], xs=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Scoring Format (PPR)"),
                dbc.CardBody([
                    html.Div([
                        html.Span("QB: ", className="fw-bold"),
                        "0.04/yd pass, 4/TD, -2/INT, 0.1/yd rush, 6/TD",
                    ], className="mb-2"),
                    html.Div([
                        html.Span("RB/WR/TE: ", className="fw-bold"),
                        "1 PPR, 0.1/yd, 6/TD, -2 fumbles",
                    ], className="mb-2"),
                    html.Div([
                        html.Span("K: ", className="fw-bold"),
                        "3 for FG, 1 for XP",
                    ], className="mb-2"),
                    html.Div([
                        html.Span("DEF: ", className="fw-bold"),
                        "1 sack, 2 turnover, 6 TD, points allowed bonus",
                    ]),
                ], style={'fontSize': '0.9rem'})
            ], className="mb-4")
        ], xs=12, md=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Data Sources"),
                dbc.CardBody([
                    html.Div([
                        html.Span("Primary: ", className="fw-bold"),
                        "Your playoff equation rankings (2025 regular season stats for playoff teams)",
                    ], className="mb-2"),
                    html.Div([
                        html.Span("Comparison: ", className="fw-bold"),
                        "FantasyAlarm, RotoBaller, NFL.com expert consensus",
                    ], className="mb-2"),
                    html.Div([
                        html.Span("Teams: ", className="fw-bold"),
                        "14 playoff teams (AFC: 7, NFC: 7)",
                    ]),
                ], style={'fontSize': '0.9rem'})
            ], className="mb-4")
        ], xs=12, md=6),
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div(id="rankings-container", children=[
                build_nfc_afc_grid()
            ])
        ], xs=12)
    ]),
    
    html.Hr(className="my-5"),
    dbc.Row([
        dbc.Col([
            html.Small([
                "Rankings updated: ",
                html.Span(datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"), className="text-muted"),
                " • Data source: docs/postseason/playoff_players_2026.json"
            ])
        ], xs=12)
    ])
], fluid=True, className="bg-light")

if __name__ == '__main__':
    app.run_server(debug=True, port=8052)
