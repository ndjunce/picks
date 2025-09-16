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

# Weekly Records Tab - COMPLETED
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
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
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

# Server setup
server = app.server

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=False, host='0.0.0.0', port=port)