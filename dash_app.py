import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from nfl_picks_automator import update_picks
import sqlite3

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1("NFL Picks Tracker - Live"),
    dbc.Button("Update with Latest Results", id='update-btn', color='primary'),
    html.Div(id='status'),
    
    # Simple buttons instead of tabs to avoid callback conflicts
    html.Div([
        html.H3("View Options:"),
        dbc.ButtonGroup([
            dbc.Button("Cumulative Results", id='show-cumulative', color='secondary', className='me-2'),
            dbc.Button("Weekly Picks", id='show-weekly', color='secondary', className='me-2'),
            dbc.Button("Team Breakdown", id='show-teams', color='secondary')
        ], className='mb-3')
    ]),
    
    # Main content area
    dcc.Loading(html.Div(id='main-content'))
])

@app.callback(
    [Output('status', 'children'), Output('main-content', 'data'), Output('main-content', 'columns')],
    [Input('update-btn', 'n_clicks')]
)
def run_update(n_clicks):
    if n_clicks is None:
        # Show initial cumulative data
        try:
            conn = sqlite3.connect('picks.db', check_same_thread=False)
            df = pd.read_sql_query("SELECT * FROM cumulative", conn)
            conn.close()
            
            if df.empty:
                return "No data available. Click update to load data.", [], []
            
            columns = [{"name": i, "id": i} for i in df.columns]
            data = df.to_dict('records')
            return "", data, columns
        except:
            return "Click 'Update with Latest Results' to load data", [], []
    
    try:
        update_picks()
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM cumulative", conn)
        conn.close()
        columns = [{"name": i, "id": i} for i in df.columns]
        data = df.to_dict('records')
        return "Updated!", data, columns
    except Exception as e:
        return f"Error: {str(e)} (Check picks.db or update_picks() for issues)", [], []

# Separate callback for showing cumulative
@app.callback(
    Output('main-content', 'children'),
    [Input('show-cumulative', 'n_clicks'), 
     Input('show-weekly', 'n_clicks'), 
     Input('show-teams', 'n_clicks')]
)
def show_content(cumulative_clicks, weekly_clicks, teams_clicks):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        # Default: show cumulative
        return get_cumulative_table()
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'show-cumulative':
        return get_cumulative_table()
    elif button_id == 'show-weekly':
        return get_weekly_content()
    elif button_id == 'show-teams':
        return get_team_breakdown()
    else:
        return get_cumulative_table()

def get_cumulative_table():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM cumulative", conn)
        conn.close()
        
        if df.empty:
            return html.Div("No cumulative data available. Click 'Update with Latest Results' first.")
        
        return html.Div([
            html.H4("Cumulative Results"),
            dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in df.columns],
                page_size=20
            )
        ])
    except Exception as e:
        return html.Div(f"Error loading cumulative data: {str(e)}")

def get_weekly_content():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE week = 1", conn)  # Just show week 1 for now
        conn.close()
        
        if df.empty:
            return html.Div("No weekly data available. Click 'Update with Latest Results' first.")
        
        # Format the data for display
        display_data = []
        people_cols = ['bobby_pick', 'chet_pick', 'clyde_pick', 'henry_pick', 'riley_pick', 'nick_pick']
        
        for _, row in df.iterrows():
            game_display = f"{row['away_team']} @ {row['home_team']}"
            game_row = {'Game': game_display}
            
            for col in people_cols:
                person_name = col.replace('_pick', '').title()
                pick = row[col]
                if pick == 'Away':
                    game_row[person_name] = row['away_team']
                elif pick == 'Home':
                    game_row[person_name] = row['home_team']
                else:
                    game_row[person_name] = '-'
            
            # Add winner
            if pd.notna(row['actual_winner']):
                if row['actual_winner'] == 'Away':
                    game_row['Winner'] = row['away_team']
                elif row['actual_winner'] == 'Home':
                    game_row['Winner'] = row['home_team']
                else:
                    game_row['Winner'] = row['actual_winner']
            else:
                game_row['Winner'] = 'TBD'
            
            display_data.append(game_row)
        
        display_df = pd.DataFrame(display_data)
        
        return html.Div([
            html.H4("Week 1 Picks"),
            dash_table.DataTable(
                data=display_df.to_dict('records'),
                columns=[{"name": col, "id": col} for col in display_df.columns],
                page_size=20,
                style_cell={'textAlign': 'center', 'fontSize': '12px'}
            )
        ])
    except Exception as e:
        return html.Div(f"Error loading weekly data: {str(e)}")

def get_team_breakdown():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return html.Div("No completed games data available. Click 'Update with Latest Results' first.")
        
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
                    
                    team_breakdown.append({
                        'Person': person.title(),
                        'Team': team,
                        'Record': f"{wins}-{losses}",
                        'Win %': f"{win_pct:.1f}%",
                        'Total': total_games
                    })
        
        if not team_breakdown:
            return html.Div("No team breakdown data available.")
        
        breakdown_df = pd.DataFrame(team_breakdown)
        breakdown_df = breakdown_df.sort_values(['Person', 'Total'], ascending=[True, False])
        
        return html.Div([
            html.H4("Team Performance Breakdown"),
            html.P("Shows each person's record when picking specific teams"),
            dash_table.DataTable(
                data=breakdown_df.to_dict('records'),
                columns=[{"name": col, "id": col} for col in breakdown_df.columns],
                page_size=25,
                style_cell={'textAlign': 'center'},
                sort_action="native",
                filter_action="native"
            )
        ])
    except Exception as e:
        return html.Div(f"Error loading team breakdown: {str(e)}")

server = app.server  # Expose for Gunicorn

if __name__ == '__main__':
    app.run(debug=True)