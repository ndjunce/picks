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
    dcc.Loading(dash_table.DataTable(id='cumulative-table', data=[], columns=[], page_size=20)),
])

@app.callback(
    [Output('status', 'children'), Output('cumulative-table', 'data'), Output('cumulative-table', 'columns')],
    Input('update-btn', 'n_clicks')
)
def run_update(n_clicks):
    if n_clicks is None:
        return "", [], []
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

server = app.server  # Expose for Gunicorn

if __name__ == '__main__':
    app.run(debug=True)