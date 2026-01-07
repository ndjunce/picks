import os
import sqlite3
import requests
from datetime import datetime

import dash
from dash import Dash, Input, Output, State, dcc, html, dash_table
import dash_bootstrap_components as dbc
from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.path.join(os.getcwd(), "picks.db")
MAX_TEAMS = 10
ROSTER_SLOTS = [
    "Superflex 1",
    "Superflex 2",
    "Superflex 3",
    "Superflex 4",
    "Superflex 5",
    "Superflex 6",
    "K",
    "DST",
]
DEFAULT_SEASON = 2025
POSTSEASON_PREFIX = os.getenv("POSTSEASON_PREFIX", "/postseason/")
POSTSEASON_STATS_API_URL = os.getenv("POSTSEASON_STATS_API_URL", "")
AUTO_REFRESH_SECS = int(os.getenv("POSTSEASON_AUTO_REFRESH_SECS", "60"))


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_postseason_tables():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS postseason_users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS postseason_teams (
            id INTEGER PRIMARY KEY,
            team_name TEXT UNIQUE,
            owner_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS postseason_players (
            id INTEGER PRIMARY KEY,
            name TEXT,
            position TEXT,
            nfl_team TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS postseason_rosters (
            team_id INTEGER,
            slot TEXT,
            player_id INTEGER,
            PRIMARY KEY (team_id, slot)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS postseason_weekly_stats (
            player_id INTEGER,
            week INTEGER,
            season INTEGER,
            pass_yds REAL,
            pass_td REAL,
            interceptions REAL,
            rush_yds REAL,
            rush_td REAL,
            receptions REAL,
            rec_yds REAL,
            rec_td REAL,
            fumbles REAL,
            two_pt REAL,
            fg_made REAL,
            fg_miss REAL,
            xp_made REAL,
            xp_miss REAL,
            sacks REAL,
            turnovers REAL,
            dst_td REAL,
            points_allowed REAL,
            fantasy_points REAL,
            PRIMARY KEY (player_id, week, season)
        )
        """
    )
    conn.commit()
    conn.close()


def register_user(username: str, password: str):
    conn = get_conn()
    cur = conn.cursor()
    user_count = cur.execute("SELECT COUNT(*) FROM postseason_users").fetchone()[0]
    if user_count >= MAX_TEAMS:
        conn.close()
        return None, "League is full (10 managers)."
    try:
        cur.execute(
            "INSERT INTO postseason_users (username, password_hash) VALUES (?, ?)",
            (username.strip().lower(), generate_password_hash(password)),
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return user_id, "Account created."
    except sqlite3.IntegrityError:
        conn.close()
        return None, "Username already exists."


def verify_user(username: str, password: str):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, password_hash FROM postseason_users WHERE username = ?",
        (username.strip().lower(),),
    ).fetchone()
    conn.close()
    if row and check_password_hash(row[1], password):
        return row[0]
    return None


def ensure_team_for_user(user_id: int, team_name: str | None = None):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, team_name FROM postseason_teams WHERE owner_id = ?",
        (user_id,),
    ).fetchone()
    if row:
        conn.close()
        return row[0], row[1]
    if team_name:
        cur.execute(
            "INSERT INTO postseason_teams (team_name, owner_id) VALUES (?, ?)",
            (team_name, user_id),
        )
        conn.commit()
        team_id = cur.lastrowid
        conn.close()
        return team_id, team_name
    conn.close()
    return None, None


def upsert_player(name: str, position: str, nfl_team: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO postseason_players (name, position, nfl_team) VALUES (?, ?, ?)",
        (name.strip(), position.strip().upper(), nfl_team.strip()),
    )
    conn.commit()
    conn.close()


def get_players():
    conn = get_conn()
    df = conn.execute(
        "SELECT id, name, position, nfl_team FROM postseason_players ORDER BY name"
    ).fetchall()
    conn.close()
    return df


def save_roster(team_id: int, selections: dict):
    conn = get_conn()
    cur = conn.cursor()
    for slot, player_id in selections.items():
        if player_id:
            cur.execute(
                "REPLACE INTO postseason_rosters (team_id, slot, player_id) VALUES (?, ?, ?)",
                (team_id, slot, int(player_id)),
            )
    conn.commit()
    conn.close()


def record_weekly_stats(player_id: int, week: int, season: int, stats: dict):
    pts = calculate_points(stats, stats.get("position", "FLEX"))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        REPLACE INTO postseason_weekly_stats (
            player_id, week, season, pass_yds, pass_td, interceptions,
            rush_yds, rush_td, receptions, rec_yds, rec_td, fumbles, two_pt,
            fg_made, fg_miss, xp_made, xp_miss, sacks, turnovers, dst_td,
            points_allowed, fantasy_points
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            player_id,
            week,
            season,
            stats.get("pass_yds", 0),
            stats.get("pass_td", 0),
            stats.get("interceptions", 0),
            stats.get("rush_yds", 0),
            stats.get("rush_td", 0),
            stats.get("receptions", 0),
            stats.get("rec_yds", 0),
            stats.get("rec_td", 0),
            stats.get("fumbles", 0),
            stats.get("two_pt", 0),
            stats.get("fg_made", 0),
            stats.get("fg_miss", 0),
            stats.get("xp_made", 0),
            stats.get("xp_miss", 0),
            stats.get("sacks", 0),
            stats.get("turnovers", 0),
            stats.get("dst_td", 0),
            stats.get("points_allowed", 0),
            pts,
        ),
    )
    conn.commit()
    conn.close()
    return pts


def calculate_points(stats: dict, position: str):
    pos = position.upper()
    if pos == "K":
        return (
            stats.get("fg_made", 0) * 3
            - stats.get("fg_miss", 0)
            + stats.get("xp_made", 0) * 1
            - stats.get("xp_miss", 0)
        )
    if pos == "DST":
        pa = stats.get("points_allowed", 0)
        pa_bonus = 10 if pa == 0 else 7 if pa <= 6 else 4 if pa <= 13 else 1 if pa <= 20 else 0 if pa <= 27 else -1 if pa <= 34 else -4
        return (
            stats.get("sacks", 0)
            + stats.get("turnovers", 0) * 2
            + stats.get("dst_td", 0) * 6
            + pa_bonus
        )
    return (
        stats.get("pass_yds", 0) * 0.04
        + stats.get("pass_td", 0) * 4
        - stats.get("interceptions", 0) * 2
        + stats.get("rush_yds", 0) * 0.1
        + stats.get("rush_td", 0) * 6
        + stats.get("receptions", 0) * 1
        + stats.get("rec_yds", 0) * 0.1
        + stats.get("rec_td", 0) * 6
        - stats.get("fumbles", 0) * 2
        + stats.get("two_pt", 0) * 2
    )


def fetch_roster(team_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT slot, player_id FROM postseason_rosters WHERE team_id = ?",
        (team_id,),
    ).fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def fetch_weekly_totals(week: int, season: int):
    conn = get_conn()
    cur = conn.cursor()
    teams = cur.execute(
        "SELECT id, team_name FROM postseason_teams ORDER BY team_name"
    ).fetchall()
    results = []
    for team_id, name in teams:
        total = 0
        roster = cur.execute(
            "SELECT slot, player_id FROM postseason_rosters WHERE team_id = ?",
            (team_id,),
        ).fetchall()
        for _, player_id in roster:
            if not player_id:
                continue
            row = cur.execute(
                """
                SELECT p.position, s.fantasy_points
                FROM postseason_players p
                JOIN postseason_weekly_stats s ON p.id = s.player_id
                WHERE p.id = ? AND s.week = ? AND s.season = ?
                """,
                (player_id, week, season),
            ).fetchone()
            if row and row[1] is not None:
                total += row[1]
        results.append({"Team": name, "Points": round(total, 2)})
    conn.close()
    return results


init_postseason_tables()

# Auto-load default playoff players from JSON if table is empty
def _bootstrap_playoff_players():
    try:
        conn = get_conn()
        cur = conn.cursor()
        count = cur.execute("SELECT COUNT(*) FROM postseason_players").fetchone()[0]
        if count > 0:
            conn.close()
            return
        # Read generated players JSON
        base_dir = os.getcwd()
        json_path = os.path.join(base_dir, "docs", "postseason", "playoff_players_2026.json")
        if not os.path.exists(json_path):
            conn.close()
            return
        import json
        with open(json_path) as f:
            data = json.load(f)
        players = data.get("players", [])
        for p in players:
            name = p.get("player_name", "").strip()
            pos = p.get("position", "").strip().upper()
            team = p.get("team", "").strip().upper()
            if not name or not pos:
                continue
            if pos == "DEF":
                pos = "DST"
            cur.execute(
                "INSERT INTO postseason_players (name, position, nfl_team) VALUES (?, ?, ?)",
                (name, pos, team),
            )
        conn.commit()
        conn.close()
    except Exception:
        # Non-fatal: skip bootstrap on errors
        pass

_bootstrap_playoff_players()

app: Dash = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
    requests_pathname_prefix=POSTSEASON_PREFIX,
    routes_pathname_prefix=POSTSEASON_PREFIX,
)
server = app.server

app.layout = dbc.Container(
    [
        dcc.Store(id="auth-store", storage_type="session"),
        html.H2("Postseason Superflex Fantasy", className="mt-3 mb-2"),
        html.P("Standard PPR, 6 Superflex + K + DST. Up to 10 managers."),
        dbc.Card(
            [
                dbc.CardHeader("Login or Create Account"),
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Input(id="username", placeholder="Username"), width=12, md=4
                                ),
                                dbc.Col(
                                    dbc.Input(id="password", type="password", placeholder="Password"),
                                    width=12,
                                    md=4,
                                ),
                                dbc.Col(
                                    dbc.Input(
                                        id="team-name",
                                        placeholder="Team name (new accounts)",
                                    ),
                                    width=12,
                                    md=4,
                                ),
                            ],
                            className="mb-2",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Switch(
                                        id="register-toggle",
                                        label="Create new account",
                                        value=False,
                                    ),
                                    width=12,
                                    md=4,
                                ),
                                dbc.Col(
                                    dbc.Button("Submit", id="login-btn", color="primary", className="w-100"),
                                    width=12,
                                    md=4,
                                ),
                            ]
                        ),
                        html.Div(id="login-alert", className="mt-2"),
                    ]
                ),
            ],
            className="mb-3",
        ),
        html.Div(id="protected-content"),
    ],
    fluid=True,
)


def tabs_layout():
    return dbc.Tabs(
        [
            dbc.Tab(label="Teams", tab_id="teams"),
            dbc.Tab(label="Players", tab_id="players"),
            dbc.Tab(label="Playoff Players", tab_id="playoff_players"),
            dbc.Tab(label="Rosters", tab_id="rosters"),
            dbc.Tab(label="Weekly Stats", tab_id="stats"),
            dbc.Tab(label="Scoreboard", tab_id="score"),
        ],
        id="main-tabs",
        active_tab="score",
        className="mb-3",
    )


def teams_panel(user_id):
    team_id, team_name = ensure_team_for_user(user_id)
    return dbc.Card(
        [
            dbc.CardHeader("Your Team"),
            dbc.CardBody(
                [
                    html.P(f"Current team: {team_name}" if team_name else "No team yet."),
                    dbc.Input(id="new-team-name", placeholder="Team name"),
                    dbc.Button(
                        "Save Team",
                        id="team-save-btn",
                        color="secondary",
                        className="mt-2",
                    ),
                    html.Div(id="team-save-status", className="mt-2"),
                ]
            ),
        ]
    )


def players_panel():
    return dbc.Card(
        [
            dbc.CardHeader("Add Player"),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(dbc.Input(id="player-name", placeholder="Name"), md=4),
                            dbc.Col(
                                dbc.Select(
                                    id="player-position",
                                    options=[
                                        {"label": p, "value": p}
                                        for p in ["QB", "RB", "WR", "TE", "K", "DST"]
                                    ],
                                    value="QB",
                                ),
                                md=3,
                            ),
                            dbc.Col(
                                dbc.Input(id="player-team", placeholder="NFL Team (e.g., KC)"),
                                md=3,
                            ),
                            dbc.Col(
                                dbc.Button(
                                    "Add Player",
                                    id="add-player-btn",
                                    color="primary",
                                    className="w-100",
                                ),
                                md=2,
                            ),
                        ],
                        className="mb-2",
                    ),
                    html.Div(id="player-status"),
                ]
            ),
        ]
    )


def roster_panel(user_id):
    team_id, team_name = ensure_team_for_user(user_id)
    if not team_id:
        return dbc.Alert("Create your team first.", color="warning")
    players = get_players()
    roster = fetch_roster(team_id)
    option_map = {pos: [] for pos in ["SUPERFLEX", "K", "DST"]}
    for row in players:
        pid, name, pos, nfl = row
        label = f"{name} ({pos}-{nfl})"
        if pos in ["QB", "RB", "WR", "TE"]:
            option_map["SUPERFLEX"].append({"label": label, "value": pid})
        if pos == "K":
            option_map["K"].append({"label": label, "value": pid})
        if pos == "DST":
            option_map["DST"].append({"label": label, "value": pid})
    rows = []
    for slot in ROSTER_SLOTS:
        key = "SUPERFLEX" if "Superflex" in slot else slot
        rows.append(
            dbc.Row(
                [
                    dbc.Col(html.Label(slot), width=4),
                    dbc.Col(
                        dcc.Dropdown(
                            id=f"slot-{slot}",
                            options=option_map[key],
                            value=roster.get(slot),
                            placeholder="Select player",
                            clearable=True,
                        ),
                        width=8,
                    ),
                ],
                className="mb-2",
            )
        )
    return dbc.Card(
        [
            dbc.CardHeader(f"Roster for {team_name}"),
            dbc.CardBody(
                rows
                + [
                    dbc.Button(
                        "Save Roster",
                        id="save-roster-btn",
                        color="success",
                        className="mt-2",
                    ),
                    html.Div(id="roster-status", className="mt-2"),
                ]
            ),
        ]
    )


def stats_panel():
    players = get_players()
    return dbc.Card(
        [
            dbc.CardHeader("Enter Weekly Stats"),
            dbc.CardBody(
                [
                    dcc.Dropdown(
                        id="stat-player",
                        options=[
                            {"label": f"{p[1]} ({p[2]}-{p[3]})", "value": p[0], "position": p[2]}
                            for p in players
                        ],
                        placeholder="Choose player",
                        clearable=False,
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Input(id="stat-week", type="number", value=1, min=1), width=12, md=3),
                            dbc.Col(
                                dbc.Input(
                                    id="stat-season",
                                    type="number",
                                    value=DEFAULT_SEASON,
                                    min=2020,
                                ),
                                width=12,
                                md=3,
                            ),
                        ],
                        className="mt-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Input(id="pass-yds", type="number", placeholder="Pass yds"), md=3),
                            dbc.Col(dbc.Input(id="pass-td", type="number", placeholder="Pass TD"), md=3),
                            dbc.Col(dbc.Input(id="interceptions", type="number", placeholder="INT"), md=3),
                            dbc.Col(dbc.Input(id="rush-yds", type="number", placeholder="Rush yds"), md=3),
                        ],
                        className="mt-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Input(id="rush-td", type="number", placeholder="Rush TD"), md=3),
                            dbc.Col(dbc.Input(id="receptions", type="number", placeholder="Receptions"), md=3),
                            dbc.Col(dbc.Input(id="rec-yds", type="number", placeholder="Rec yds"), md=3),
                            dbc.Col(dbc.Input(id="rec-td", type="number", placeholder="Rec TD"), md=3),
                        ],
                        className="mt-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Input(id="fumbles", type="number", placeholder="Fumbles"), md=3),
                            dbc.Col(dbc.Input(id="two-pt", type="number", placeholder="2PT"), md=3),
                            dbc.Col(dbc.Input(id="fg-made", type="number", placeholder="FG made"), md=3),
                            dbc.Col(dbc.Input(id="fg-miss", type="number", placeholder="FG miss"), md=3),
                        ],
                        className="mt-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Input(id="xp-made", type="number", placeholder="XP made"), md=3),
                            dbc.Col(dbc.Input(id="xp-miss", type="number", placeholder="XP miss"), md=3),
                            dbc.Col(dbc.Input(id="sacks", type="number", placeholder="DST sacks"), md=3),
                            dbc.Col(dbc.Input(id="turnovers", type="number", placeholder="DST TO"), md=3),
                        ],
                        className="mt-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Input(id="dst-td", type="number", placeholder="DST TD"), md=3),
                            dbc.Col(dbc.Input(id="points-allowed", type="number", placeholder="PTS allowed"), md=3),
                        ],
                        className="mt-2",
                    ),
                    dbc.Button("Save Stats", id="save-stats-btn", color="primary", className="mt-3 w-100"),
                    html.Div(id="stats-status", className="mt-2"),
                ]
            ),
        ]
    )


def scoreboard_panel():
    return dbc.Card(
        [
            dbc.CardHeader("Weekly Scoreboard"),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(dbc.Input(id="score-week", type="number", value=1, min=1), width=12, md=3),
                            dbc.Col(
                                dcc.Dropdown(
                                    id="score-week-dd",
                                    options=[
                                        {"label": "Wild Card (1)", "value": 1},
                                        {"label": "Divisional (2)", "value": 2},
                                        {"label": "Conference (3)", "value": 3},
                                        {"label": "Super Bowl (4)", "value": 4},
                                    ],
                                    value=1,
                                    clearable=False,
                                ),
                                width=12,
                                md=3,
                            ),
                            dbc.Col(
                                dbc.Input(id="score-season", type="number", value=DEFAULT_SEASON, min=2020),
                                width=12,
                                md=3,
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id="score-season-dd",
                                    options=[
                                        {"label": str(y), "value": y} for y in range(2020, DEFAULT_SEASON + 1)
                                    ],
                                    value=DEFAULT_SEASON,
                                    clearable=False,
                                ),
                                width=12,
                                md=3,
                            ),
                            dbc.Col(
                                dbc.Button("Refresh", id="refresh-score", color="secondary", className="w-100 mb-2"),
                                width=12,
                                md=3,
                            ),
                            dbc.Col(
                                dbc.Button("Update Live Stats", id="update-live-stats", color="primary", className="w-100 mb-2"),
                                width=12,
                                md=3,
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.Div(id="update-live-status", className="mb-3"),
                    html.Div(id="score-table"),
                    # Auto-update on page load (fires once)
                    dcc.Interval(id="auto-update-on-load", interval=1000, n_intervals=0, max_intervals=1),
                    # Periodic refresh while page is open
                    dcc.Interval(id="live-auto-refresh", interval=AUTO_REFRESH_SECS * 1000, n_intervals=0),
                ]
            ),
        ]
    )


def playoff_players_panel():
    # Load generated playoff players JSON
    base_dir = os.getcwd()
    json_path = os.path.join(base_dir, "docs", "postseason", "playoff_players_2026.json")
    rows = []
    try:
        import json
        if os.path.exists(json_path):
            with open(json_path) as f:
                data = json.load(f)
            for p in data.get("players", []):
                ws = p.get("weekly_scores", {})
                rows.append({
                    "Rank": p.get("rank"),
                    "Player": p.get("player_name"),
                    "Pos": p.get("position"),
                    "Team": p.get("team"),
                    "WC": ws.get("wild_card", 0.0),
                    "DIV": ws.get("divisional", 0.0),
                    "CONF": ws.get("conference", 0.0),
                    "SB": ws.get("super_bowl", 0.0),
                    "Total": p.get("total_points", 0.0),
                    "Games": p.get("games_played", 0),
                    "Status": "Eliminated" if p.get("eliminated") else "Active",
                })
    except Exception:
        rows = []

    return dbc.Card([
        dbc.CardHeader("Available Playoff Players"),
        dbc.CardBody([
            dash_table.DataTable(
                data=rows,
                columns=[
                    {"name": "Rank", "id": "Rank"},
                    {"name": "Player", "id": "Player"},
                    {"name": "Pos", "id": "Pos"},
                    {"name": "Team", "id": "Team"},
                    {"name": "WC", "id": "WC"},
                    {"name": "DIV", "id": "DIV"},
                    {"name": "CONF", "id": "CONF"},
                    {"name": "SB", "id": "SB"},
                    {"name": "Total", "id": "Total"},
                    {"name": "Games", "id": "Games"},
                    {"name": "Status", "id": "Status"},
                ],
                filter_action='native',
                sort_action='native',
                page_action='native',
                page_size=20,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'center', 'padding': '8px', 'minWidth': '70px'},
                style_header={'backgroundColor': '#0d6efd', 'color': 'white', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Status', 'filter_query': '{Status} = "Eliminated"'},
                        'backgroundColor': '#f8d7da', 'color': '#721c24'
                    }
                ]
            )
        ])
    ])


@app.callback(
    Output("auth-store", "data"),
    Output("login-alert", "children"),
    Input("login-btn", "n_clicks"),
    State("username", "value"),
    State("password", "value"),
    State("team-name", "value"),
    State("register-toggle", "value"),
    prevent_initial_call=True,
)
def handle_login(n_clicks, username, password, team_name, register):
    if not username or not password:
        return dash.no_update, dbc.Alert("Enter username and password.", color="danger")
    if register:
        user_id, msg = register_user(username, password)
        if not user_id:
            return dash.no_update, dbc.Alert(msg, color="danger")
        ensure_team_for_user(user_id, team_name or f"Team {username}")
        return {"user_id": user_id, "username": username}, dbc.Alert(msg, color="success")
    user_id = verify_user(username, password)
    if not user_id:
        return dash.no_update, dbc.Alert("Invalid credentials.", color="danger")
    ensure_team_for_user(user_id, team_name)
    return {"user_id": user_id, "username": username}, dbc.Alert("Logged in.", color="success")


@app.callback(
    Output("protected-content", "children"),
    Input("auth-store", "data"),
)
def render_protected(auth):
    if not auth:
        return dbc.Alert("Log in to manage the postseason league.", color="info")
    user_id = auth.get("user_id")
    return html.Div(
        [tabs_layout(), html.Div(id="tab-body"), dcc.Interval(id="heartbeat", interval=30_000)]
    )


@app.callback(
    Output("tab-body", "children"),
    Input("main-tabs", "active_tab"),
    Input("auth-store", "data"),
    Input("heartbeat", "n_intervals"),
)
def render_tab(active_tab, auth, _):
    if not auth:
        return dash.no_update
    user_id = auth.get("user_id")
    if active_tab == "teams":
        return teams_panel(user_id)
    if active_tab == "players":
        return players_panel()
    if active_tab == "playoff_players":
        return playoff_players_panel()
    if active_tab == "rosters":
        return roster_panel(user_id)
    if active_tab == "stats":
        return stats_panel()
    if active_tab == "score":
        return scoreboard_panel()
    return dash.no_update


@app.callback(
    Output("team-save-status", "children"),
    Input("team-save-btn", "n_clicks"),
    State("new-team-name", "value"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def save_team(n_clicks, new_name, auth):
    if not auth:
        return dbc.Alert("Login required.", color="warning")
    if not new_name:
        return dbc.Alert("Enter a team name.", color="danger")
    team_id, _ = ensure_team_for_user(auth.get("user_id"), new_name)
    if team_id:
        return dbc.Alert("Team saved.", color="success")
    return dbc.Alert("Unable to save team.", color="danger")


@app.callback(
    Output("player-status", "children"),
    Input("add-player-btn", "n_clicks"),
    State("player-name", "value"),
    State("player-position", "value"),
    State("player-team", "value"),
    prevent_initial_call=True,
)
def add_player(n_clicks, name, position, team):
    if not name or not position:
        return dbc.Alert("Name and position required.", color="danger")
    upsert_player(name, position, team or "")
    return dbc.Alert("Player added.", color="success")


@app.callback(
    Output("roster-status", "children"),
    Input("save-roster-btn", "n_clicks"),
    State("auth-store", "data"),
    [State(f"slot-{slot}", "value") for slot in ROSTER_SLOTS],
    prevent_initial_call=True,
)
def save_roster_callback(n_clicks, auth, *slot_values):
    if not auth:
        return dbc.Alert("Login required.", color="warning")
    team_id, _ = ensure_team_for_user(auth.get("user_id"))
    if not team_id:
        return dbc.Alert("Create a team first.", color="danger")
    selections = {slot: val for slot, val in zip(ROSTER_SLOTS, slot_values)}
    save_roster(team_id, selections)
    return dbc.Alert("Roster saved.", color="success")


@app.callback(
    Output("stats-status", "children"),
    Input("save-stats-btn", "n_clicks"),
    State("stat-player", "value"),
    State("stat-player", "options"),
    State("stat-week", "value"),
    State("stat-season", "value"),
    State("pass-yds", "value"),
    State("pass-td", "value"),
    State("interceptions", "value"),
    State("rush-yds", "value"),
    State("rush-td", "value"),
    State("receptions", "value"),
    State("rec-yds", "value"),
    State("rec-td", "value"),
    State("fumbles", "value"),
    State("two-pt", "value"),
    State("fg-made", "value"),
    State("fg-miss", "value"),
    State("xp-made", "value"),
    State("xp-miss", "value"),
    State("sacks", "value"),
    State("turnovers", "value"),
    State("dst-td", "value"),
    State("points-allowed", "value"),
    prevent_initial_call=True,
)
def save_stats(
    n_clicks,
    player_id,
    player_options,
    week,
    season,
    pass_yds,
    pass_td,
    interceptions,
    rush_yds,
    rush_td,
    receptions,
    rec_yds,
    rec_td,
    fumbles,
    two_pt,
    fg_made,
    fg_miss,
    xp_made,
    xp_miss,
    sacks,
    turnovers,
    dst_td,
    points_allowed,
):
    if not player_id:
        return dbc.Alert("Select a player.", color="danger")
    pos = "FLEX"
    for opt in player_options:
        if opt["value"] == player_id:
            pos = opt.get("position", "FLEX")
            break
    stats = {
        "position": pos,
        "pass_yds": pass_yds or 0,
        "pass_td": pass_td or 0,
        "interceptions": interceptions or 0,
        "rush_yds": rush_yds or 0,
        "rush_td": rush_td or 0,
        "receptions": receptions or 0,
        "rec_yds": rec_yds or 0,
        "rec_td": rec_td or 0,
        "fumbles": fumbles or 0,
        "two_pt": two_pt or 0,
        "fg_made": fg_made or 0,
        "fg_miss": fg_miss or 0,
        "xp_made": xp_made or 0,
        "xp_miss": xp_miss or 0,
        "sacks": sacks or 0,
        "turnovers": turnovers or 0,
        "dst_td": dst_td or 0,
        "points_allowed": points_allowed or 0,
    }
    pts = record_weekly_stats(int(player_id), int(week), int(season), stats)
    return dbc.Alert(f"Saved {pts:.2f} pts", color="success")


@app.callback(
    Output("score-table", "children"),
    Input("refresh-score", "n_clicks"),
    State("score-week", "value"),
    State("score-season", "value"),
)
def refresh_scoreboard(_, week, season):
    if not week or not season:
        return dbc.Alert("Enter week and season.", color="danger")
    data = fetch_weekly_totals(int(week), int(season))
    if not data:
        return dbc.Alert("No scores yet.", color="info")
    return dash_table.DataTable(
        data=data,
        columns=[{"name": "Team", "id": "Team"}, {"name": "Points", "id": "Points"}],
        style_cell={"textAlign": "center", "padding": "10px"},
    )


def _find_player_id_by_name_or_team(name: str, position: str, team: str | None = None) -> int | None:
    try:
        conn = get_conn()
        cur = conn.cursor()
        # Try exact name match first (case-insensitive)
        row = cur.execute(
            "SELECT id FROM postseason_players WHERE LOWER(name) = LOWER(?)",
            (name.strip(),),
        ).fetchone()
        if row:
            conn.close()
            return int(row[0])
        # Fallback for DST and K placeholders by team
        if position.upper() in {"DST", "DEF"} and team:
            row = cur.execute(
                "SELECT id FROM postseason_players WHERE position = 'DST' AND UPPER(nfl_team) = UPPER(?)",
                (team.strip(),),
            ).fetchone()
            if row:
                conn.close()
                return int(row[0])
        if position.upper() == "K" and team:
            row = cur.execute(
                "SELECT id FROM postseason_players WHERE position = 'K' AND UPPER(nfl_team) = UPPER(?)",
                (team.strip(),),
            ).fetchone()
            if row:
                conn.close()
                return int(row[0])
        conn.close()
        return None
    except Exception:
        return None


def _fetch_live_stats(season: int, week: int) -> list[dict]:
    """Fetch live stats from API or local JSON fallback. Returns list of stat dicts."""
    # Expected schema per entry: {name, position, team, pass_yds, pass_td, interceptions, rush_yds, rush_td,
    # receptions, rec_yds, rec_td, fumbles, two_pt, fg_made, fg_miss, xp_made, xp_miss, sacks, turnovers, dst_td, points_allowed}
    # API mode
    if POSTSEASON_STATS_API_URL:
        try:
            resp = requests.get(POSTSEASON_STATS_API_URL, params={"season": season, "week": week}, timeout=10)
            if resp.ok:
                payload = resp.json()
                items = payload if isinstance(payload, list) else payload.get("stats", [])
                return items if isinstance(items, list) else []
        except Exception:
            pass
    # Local fallback
    try:
        local_path = os.path.join(os.getcwd(), "docs", "postseason", "live_weekly_stats.json")
        if os.path.exists(local_path):
            import json
            with open(local_path) as f:
                payload = json.load(f)
            if isinstance(payload, list):
                return payload
            return payload.get("stats", []) if isinstance(payload, dict) else []
    except Exception:
        pass
    return []


def _perform_update_live_stats(week, season):
    if not week or not season:
        return dbc.Alert("Enter week and season.", color="danger")
    stats_items = _fetch_live_stats(int(season), int(week))
    if not stats_items:
        return dbc.Alert("No live stats available.", color="warning")
    saved = 0
    unmatched = 0
    for s in stats_items:
        name = (s.get("name") or "").strip()
        pos = (s.get("position") or "").strip().upper()
        team = (s.get("team") or "").strip().upper()
        pid = _find_player_id_by_name_or_team(name, pos, team)
        if not pid:
            unmatched += 1
            continue
        record_weekly_stats(
            player_id=int(pid),
            week=int(week),
            season=int(season),
            stats={
                "position": pos,
                "pass_yds": s.get("pass_yds", 0),
                "pass_td": s.get("pass_td", 0),
                "interceptions": s.get("interceptions", 0),
                "rush_yds": s.get("rush_yds", 0),
                "rush_td": s.get("rush_td", 0),
                "receptions": s.get("receptions", 0),
                "rec_yds": s.get("rec_yds", 0),
                "rec_td": s.get("rec_td", 0),
                "fumbles": s.get("fumbles", 0),
                "two_pt": s.get("two_pt", 0),
                "fg_made": s.get("fg_made", 0),
                "fg_miss": s.get("fg_miss", 0),
                "xp_made": s.get("xp_made", 0),
                "xp_miss": s.get("xp_miss", 0),
                "sacks": s.get("sacks", 0),
                "turnovers": s.get("turnovers", 0),
                "dst_td": s.get("dst_td", 0),
                "points_allowed": s.get("points_allowed", 0),
            },
        )
        saved += 1
    msg = f"Updated {saved} players. Unmatched: {unmatched}."
    return dbc.Alert(msg, color="success" if saved else "warning")


@app.callback(
    Output("update-live-status", "children"),
    Input("update-live-stats", "n_clicks"),
    State("score-week", "value"),
    State("score-season", "value"),
    State("score-week-dd", "value"),
    State("score-season-dd", "value"),
    prevent_initial_call=True,
)
def update_live_stats(n_clicks, week, season, week_dd, season_dd):
    week_final = week_dd if week_dd is not None else week
    season_final = season_dd if season_dd is not None else season
    return _perform_update_live_stats(week_final, season_final)


@app.callback(
    Output("update-live-status", "children"),
    Output("score-table", "children"),
    Input("auto-update-on-load", "n_intervals"),
    State("score-week", "value"),
    State("score-season", "value"),
    State("score-week-dd", "value"),
    State("score-season-dd", "value"),
    prevent_initial_call=True,
)
def auto_update_on_load(n_intervals, week, season, week_dd, season_dd):
    week_final = week_dd if week_dd is not None else week
    season_final = season_dd if season_dd is not None else season
    alert = _perform_update_live_stats(week_final, season_final)
    table = refresh_scoreboard(None, week_final, season_final)
    return alert, table


@app.callback(
    Output("update-live-status", "children"),
    Output("score-table", "children"),
    Input("live-auto-refresh", "n_intervals"),
    State("score-week", "value"),
    State("score-season", "value"),
    State("score-week-dd", "value"),
    State("score-season-dd", "value"),
    prevent_initial_call=True,
)
def periodic_update(n_intervals, week, season, week_dd, season_dd):
    week_final = week_dd if week_dd is not None else week
    season_final = season_dd if season_dd is not None else season
    alert = _perform_update_live_stats(week_final, season_final)
    table = refresh_scoreboard(None, week_final, season_final)
    return alert, table


if __name__ == "__main__":
    app.run(debug=True)
