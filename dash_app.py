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
    [Output('status', 'children'), Output("tab-content", "children")],
    [Input('update-btn', 'n_clicks'), Input("tabs", "active_tab")]
)
def update_content(n_clicks, active_tab):
    # Handle update button
    status_msg = ""
    if n_clicks and n_clicks > 0:
        try:
            update_picks()
            status_msg = dbc.Alert("Updated successfully!", color="success", dismissable=True)
        except Exception as e:
            status_msg = dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)
    
    # Handle tab content
    try:
        if active_tab == "cumulative-tab":
            content = get_cumulative_content()
        elif active_tab == "weekly-tab":
            content = get_weekly_content()
        elif active_tab == "team-tab":
            content = get_team_breakdown_content()
        else:
            content = html.Div("Loading...")
    except Exception as e:
        content = html.Div(f"Error loading content: {str(e)}")
    
    return status_msg, content

def get_cumulative_content():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM cumulative", conn)
        conn.close()
        
        if df.empty:
            return html.Div("No data available. Click 'Update with Latest Results' to load data.")
        
        columns = [{"name": col.title(), "id": col} for col in df.columns]
        data = df.to_dict('records')
        
        return dash_table.DataTable(
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
    except Exception as e:
        return html.Div(f"Error loading cumulative data: {str(e)}")

def get_weekly_content():
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM picks", conn)
        conn.close()
        
        if df.empty:
            return html.Div("No picks data available. Click 'Update with Latest Results' to load data.")
        
        weeks = sorted(df['week'].unique()) if 'week' in df.columns else []
        
        if not weeks:
            return html.Div("No weekly data available.")
        
        # Show Week 1 by default
        selected_week = weeks[0]
        week_df = df[df['week'] == selected_week]
        
        display_data = []
        people_cols = ['bobby_pick', 'chet_pick', 'clyde_pick', 'henry_pick', 'riley_pick', 'nick_pick']
        
        for _, row in week_df.iterrows():
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
        
        if display_df.empty:
            return html.Div(f"No data for Week {selected_week}")
        
        columns = [{"name": col, "id": col} for col in display_df.columns]
        
        return html.Div([
            html.H4(f"Week {selected_week} Picks"),
            html.P(f"Available weeks: {', '.join([str(w) for w in weeks])}"),
            dash_table.DataTable(
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
        
        columns = [{"name": col, "id": col} for col in breakdown_df.columns]
        
        return html.Div([
            html.H4("Team Performance Breakdown"),
            html.P("Shows each person's record when picking specific teams"),
            dash_table.DataTable(
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
                sort_action="native",
                filter_action="native"
            )
        ])
    except Exception as e:
        return html.Div(f"Error loading team breakdown: {str(e)}")

server = app.server

if __name__ == '__main__':
    app.run(debug=True)