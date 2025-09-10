import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from nfl_picks_automator import update_picks
import sqlite3

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1("NFL Picks Tracker - Live", className="text-center mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Button("Update with Latest Results", id='update-btn', color='primary', size="lg", className="mb-3"),
            html.Div(id='status', className="mb-3")
        ], width=12)
    ]),
    
    dbc.Tabs([
        dbc.Tab(label="Cumulative Results", tab_id="cumulative-tab"),
        dbc.Tab(label="Weekly Picks", tab_id="weekly-tab"),
        dbc.Tab(label="Team Breakdown", tab_id="team-tab")
    ], id="tabs", active_tab="cumulative-tab"),
    
    html.Div(id="tab-content", className="mt-4")
])

@app.callback(
    Output("tab-content", "children"),
    [Input("tabs", "active_tab"), Input('update-btn', 'n_clicks')]
)
def update_tab_content(active_tab, n_clicks):
    if active_tab == "cumulative-tab":
        return get_cumulative_content()
    elif active_tab == "weekly-tab":
        return get_weekly_content()
    elif active_tab == "team-tab":
        return get_team_breakdown_content()

@app.callback(
    Output('status', 'children'),
    Input('update-btn', 'n_clicks')
)
def run_update(n_clicks):
    if n_clicks is None:
        return ""
    try:
        update_picks()
        return dbc.Alert("Updated successfully!", color="success", dismissable=True)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)

def get_cumulative_content():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM cumulative", conn)
        conn.close()
        
        if df.empty:
            return html.Div("No data available. Click 'Update with Latest Results' to load data.")
        
        columns = [{"name": col.title(), "id": col} for col in df.columns]
        data = df.to_dict('records')
        
        return dcc.Loading(
            dash_table.DataTable(
                id='cumulative-table',
                data=data,
                columns=columns,
                page_size=20,
                style_cell={'textAlign': 'center'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ]
            )
        )
    except Exception as e:
        return html.Div(f"Error loading cumulative data: {str(e)}")

def get_weekly_content():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks", conn)
        conn.close()
        
        if df.empty:
            return html.Div("No picks data available. Click 'Update with Latest Results' to load data.")
        
        # Get available weeks
        weeks = sorted(df['week'].unique()) if 'week' in df.columns else []
        
        if not weeks:
            return html.Div("No weekly data available.")
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Select Week:", className="fw-bold"),
                    dcc.Dropdown(
                        id='week-dropdown',
                        options=[{'label': f'Week {week}', 'value': week} for week in weeks],
                        value=weeks[0] if weeks else None,
                        clearable=False
                    )
                ], width=6)
            ], className="mb-3"),
            html.Div(id='weekly-picks-table')
        ])
    except Exception as e:
        return html.Div(f"Error loading weekly data: {str(e)}")

def get_team_breakdown_content():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return html.Div("No completed games data available. Click 'Update with Latest Results' to load data.")
        
        # Calculate team breakdown for each person
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        team_breakdown = []
        
        for person in people:
            person_pick_col = f'{person}_pick'
            if person_pick_col not in df.columns:
                continue
                
            person_df = df[df[person_pick_col].notna()].copy()
            
            # Get all unique teams
            all_teams = set(person_df['away_team'].tolist() + person_df['home_team'].tolist())
            
            for team in all_teams:
                # Find games where this person picked this team
                team_picks = person_df[
                    ((person_df['away_team'] == team) & (person_df[person_pick_col] == 'Away')) |
                    ((person_df['home_team'] == team) & (person_df[person_pick_col] == 'Home'))
                ]
                
                if len(team_picks) > 0:
                    wins = len(team_picks[team_picks['actual_winner'] == team_picks[person_pick_col]])
                    losses = len(team_picks[team_picks['actual_winner'] != team_picks[person_pick_col]]) - \
                            len(team_picks[team_picks['actual_winner'] == 'Tie'])
                    ties = len(team_picks[team_picks['actual_winner'] == 'Tie'])
                    total = wins + losses + ties
                    win_pct = (wins / total * 100) if total > 0 else 0
                    
                    team_breakdown.append({
                        'Person': person.title(),
                        'Team': team,
                        'Wins': wins,
                        'Losses': losses,
                        'Ties': ties,
                        'Total': total,
                        'Win %': f"{win_pct:.1f}%"
                    })
        
        if not team_breakdown:
            return html.Div("No team breakdown data available.")
        
        breakdown_df = pd.DataFrame(team_breakdown)
        breakdown_df = breakdown_df.sort_values(['Person', 'Total'], ascending=[True, False])
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Filter by Person:", className="fw-bold"),
                    dcc.Dropdown(
                        id='person-filter',
                        options=[{'label': 'All', 'value': 'All'}] + 
                               [{'label': person, 'value': person} for person in breakdown_df['Person'].unique()],
                        value='All',
                        clearable=False
                    )
                ], width=6)
            ], className="mb-3"),
            html.Div(id='team-breakdown-table')
        ])
    except Exception as e:
        return html.Div(f"Error loading team breakdown: {str(e)}")

@app.callback(
    Output('weekly-picks-table', 'children'),
    Input('week-dropdown', 'value')
)
def update_weekly_picks(selected_week):
    if selected_week is None:
        return html.Div()
    
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query(f"SELECT * FROM picks WHERE week = {selected_week}", conn)
        conn.close()
        
        if df.empty:
            return html.Div(f"No data for Week {selected_week}")
        
        # Prepare display data
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
            
            # Add actual winner
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
        columns = [{"name": col, "id": col} for col in display_df.columns]
        
        return dash_table.DataTable(
            data=display_df.to_dict('records'),
            columns=columns,
            style_cell={'textAlign': 'center', 'fontSize': '12px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ],
            page_size=20
        )
    except Exception as e:
        return html.Div(f"Error: {str(e)}")

@app.callback(
    Output('team-breakdown-table', 'children'),
    Input('person-filter', 'value')
)
def update_team_breakdown(selected_person):
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return html.Div("No completed games data available.")
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        team_breakdown = []
        
        for person in people:
            if selected_person != 'All' and person.title() != selected_person:
                continue
                
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
                    losses = len(team_picks[team_picks['actual_winner'] != team_picks[person_pick_col]]) - \
                            len(team_picks[team_picks['actual_winner'] == 'Tie'])
                    ties = len(team_picks[team_picks['actual_winner'] == 'Tie'])
                    total = wins + losses + ties
                    win_pct = (wins / total * 100) if total > 0 else 0
                    
                    team_breakdown.append({
                        'Person': person.title(),
                        'Team': team,
                        'Record': f"{wins}-{losses}-{ties}",
                        'Win %': f"{win_pct:.1f}%",
                        'Total Picks': total
                    })
        
        if not team_breakdown:
            return html.Div("No team breakdown data available.")
        
        breakdown_df = pd.DataFrame(team_breakdown)
        breakdown_df = breakdown_df.sort_values(['Person', 'Total Picks'], ascending=[True, False])
        
        columns = [{"name": col, "id": col} for col in breakdown_df.columns]
        
        return dash_table.DataTable(
            data=breakdown_df.to_dict('records'),
            columns=columns,
            style_cell={'textAlign': 'center'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ],
            page_size=25,
            sort_action="native"
        )
    except Exception as e:
        return html.Div(f"Error: {str(e)}")

server = app.server  # Expose for Gunicorn

if __name__ == '__main__':
    app.run(debug=True)