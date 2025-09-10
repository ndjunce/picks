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
            dbc.Button("Update with Latest Results", id='update-btn', color='primary', size="lg", className="mb-4"),
            html.Div(id='status', className="mb-4")
        ], width=12)
    ]),
    
    # All content displayed at once
    html.Div(id='all-content')
])

@app.callback(
    [Output('status', 'children'), Output('all-content', 'children')],
    Input('update-btn', 'n_clicks')
)
def update_everything(n_clicks):
    # Handle status message
    status_msg = ""
    if n_clicks and n_clicks > 0:
        try:
            update_picks()
            status_msg = dbc.Alert("Updated successfully!", color="success", dismissable=True)
        except Exception as e:
            status_msg = dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)
    
    # Get all content
    content = get_all_content()
    
    return status_msg, content

def get_all_content():
    content = []
    
    # 1. Cumulative Results Section
    content.append(html.H3("Cumulative Results", className="mt-4 mb-3"))
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        cumulative_df = pd.read_sql_query("SELECT * FROM cumulative", conn)
        conn.close()
        
        if not cumulative_df.empty:
            content.append(
                dash_table.DataTable(
                    data=cumulative_df.to_dict('records'),
                    columns=[{"name": col.title(), "id": col} for col in cumulative_df.columns],
                    style_cell={'textAlign': 'center'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    page_size=20
                )
            )
        else:
            content.append(html.P("No cumulative data available. Click 'Update with Latest Results'."))
    except Exception as e:
        content.append(html.P(f"Error loading cumulative data: {str(e)}"))
    
    # 2. Weekly Picks Section - Show Week 1
    content.append(html.H3("Week 1 Picks", className="mt-5 mb-3"))
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        weekly_df = pd.read_sql_query("SELECT * FROM picks WHERE week = 1", conn)
        conn.close()
        
        if not weekly_df.empty:
            # Format weekly data
            display_data = []
            people_cols = ['bobby_pick', 'chet_pick', 'clyde_pick', 'henry_pick', 'riley_pick', 'nick_pick']
            
            for _, row in weekly_df.iterrows():
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
            
            weekly_display_df = pd.DataFrame(display_data)
            content.append(
                dash_table.DataTable(
                    data=weekly_display_df.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in weekly_display_df.columns],
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
            )
        else:
            content.append(html.P("No weekly picks data available."))
    except Exception as e:
        content.append(html.P(f"Error loading weekly data: {str(e)}"))
    
    # 3. Team Breakdown Section
    content.append(html.H3("Team Performance Breakdown", className="mt-5 mb-3"))
    content.append(html.P("Shows each person's record when picking specific teams", className="text-muted"))
    try:
        conn = sqlite3.connect('picks.db', check_same_thread=False)
        picks_df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()
        
        if not picks_df.empty:
            # Calculate team breakdown
            people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
            team_breakdown = []
            
            for person in people:
                person_pick_col = f'{person}_pick'
                if person_pick_col not in picks_df.columns:
                    continue
                    
                person_df = picks_df[picks_df[person_pick_col].notna()].copy()
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
            
            if team_breakdown:
                breakdown_df = pd.DataFrame(team_breakdown)
                breakdown_df = breakdown_df.sort_values(['Person', 'Total'], ascending=[True, False])
                
                content.append(
                    dash_table.DataTable(
                        data=breakdown_df.to_dict('records'),
                        columns=[{"name": col, "id": col} for col in breakdown_df.columns],
                        style_cell={'textAlign': 'center'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            }
                        ],
                        sort_action="native",
                        filter_action="native",
                        page_size=30
                    )
                )
            else:
                content.append(html.P("No team breakdown data available."))
        else:
            content.append(html.P("No completed games data available."))
    except Exception as e:
        content.append(html.P(f"Error loading team breakdown: {str(e)}"))
    
    return content

server = app.server  # Expose for Gunicorn

if __name__ == '__main__':
    app.run(debug=True)