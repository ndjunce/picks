import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration from .env file
class Config:
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///picks.db')
    ESPN_API_TIMEOUT = int(os.getenv('ESPN_API_TIMEOUT', '10'))
    UPDATE_INTERVAL_MINUTES = int(os.getenv('UPDATE_INTERVAL_MINUTES', '120'))
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', '10000'))
    HOST = os.getenv('HOST', '0.0.0.0')
    PLAYERS = os.getenv('PLAYERS', 'bobby,chet,clyde,henry,nick,riley').split(',')
    CURRENT_SEASON = int(os.getenv('CURRENT_SEASON', '2025'))
    EXCEL_FILE_PATH = os.getenv('EXCEL_FILE_PATH', os.path.join(os.getcwd(), 'nfl_picks_2025.xlsx'))
    ENABLE_AUTO_REFRESH = os.getenv('ENABLE_AUTO_REFRESH', 'True').lower() == 'true'
    ENABLE_TEAM_LOGOS = os.getenv('ENABLE_TEAM_LOGOS', 'True').lower() == 'true'
    ENABLE_SCORE_DISPLAY = os.getenv('ENABLE_SCORE_DISPLAY', 'True').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'nfl_picks.log')


def find_latest_excel_file(base_dir=None):
    """Return the most recently modified Excel file, preferring non-temp files. Searches both current and parent directories."""
    search_dirs = []
    if base_dir:
        search_dirs.append(base_dir)
    else:
        search_dirs.append(os.getcwd())
        # Also check parent directory
        parent_dir = os.path.dirname(os.getcwd())
        if parent_dir and os.path.exists(parent_dir):
            search_dirs.append(parent_dir)
    
    preferred = None  # non-temp
    fallback = None   # any excel
    
    for search_dir in search_dirs:
        try:
            for name in os.listdir(search_dir):
                if not name.lower().endswith('.xlsx'):
                    continue
                if name.startswith('~$'):
                    continue  # Skip Excel lock files
                path = os.path.join(search_dir, name)
                if not os.path.isfile(path):
                    continue
                mtime = os.path.getmtime(path)
                # Track any excel as fallback
                if fallback is None or mtime > fallback[0]:
                    fallback = (mtime, path)
                # Prefer files that are not temp_*
                if not name.lower().startswith('temp_'):
                    if preferred is None or mtime > preferred[0]:
                        preferred = (mtime, path)
        except Exception as e:
            logger.warning(f"Could not search directory {search_dir}: {e}")
            continue
    
    if preferred:
        return preferred[1]
    if fallback:
        return fallback[1]
    return None

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import dash
from dash import dcc, html, Input, Output, dash_table, State
import dash_bootstrap_components as dbc
import pandas as pd
import sqlite3
import base64
import plotly.express as px
import plotly.graph_objects as go
import io
from werkzeug.middleware.dispatcher import DispatcherMiddleware

import postseason_fantasy_app as postseason_app

app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    'https://use.fontawesome.com/releases/v6.0.0/css/all.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
])

# Custom CSS for professional design
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>NFL Picks Tracker 2025</title>
        {%favicon%}
        {%css%}
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Tahoma&family=Verdana&display=swap');
            
            :root {
                --neon-cyan: #00FFFF;
                --hot-pink: #FF00FF;
                --lime-green: #00FF00;
                --bright-yellow: #FFFF00;
                --electric-blue: #0066FF;
                --neon-orange: #FF6600;
            }
            
            body {
                font-family: 'Verdana', 'Tahoma', Arial, sans-serif !important;
                background: #000080 !important;
                background-image: repeating-linear-gradient(
                    0deg,
                    #000080 0px,
                    #000080 2px,
                    #0000A0 2px,
                    #0000A0 4px
                ) !important;
                margin: 0;
                padding: 0;
                color: #FFFFFF !important;
                font-size: 14px;
            }
            
            .main-header {
                background: linear-gradient(180deg, #FF00FF 0%, #9900FF 100%) !important;
                border-bottom: 8px solid #00FFFF !important;
                border-top: 4px solid #FFFF00 !important;
                color: #FFFFFF !important;
                padding: 25px 40px !important;
                box-shadow: 0 0 20px #FF00FF, inset 0 0 20px rgba(255,255,255,0.2) !important;
                position: relative;
                text-shadow: 3px 3px 0px #000000, 0 0 10px #FFFFFF !important;
            }
            
            .main-title {
                margin: 0;
                font-family: 'Impact', 'Arial Black', sans-serif !important;
                font-size: 2.8rem !important;
                font-weight: 900 !important;
                letter-spacing: 3px !important;
                color: #FFFFFF !important;
                text-transform: uppercase !important;
                text-shadow: 
                    3px 3px 0px #000000,
                    5px 5px 0px #FF00FF,
                    0 0 20px #00FFFF !important;
            }
            
            .nav-pill {
                background: linear-gradient(180deg, #00FFFF 0%, #0099CC 100%) !important;
                border: 4px solid #FFFF00 !important;
                border-radius: 0px !important;
                padding: 14px 20px !important;
                margin: 10px 0 !important;
                cursor: pointer;
                transition: all 0.2s ease;
                color: #000000 !important;
                font-family: 'Verdana', sans-serif !important;
                font-size: 14px !important;
                font-weight: 900 !important;
                text-transform: uppercase !important;
                display: flex;
                align-items: center;
                box-shadow: 5px 5px 0px #000000 !important;
                letter-spacing: 1px !important;
            }
            
            .nav-pill:hover {
                background: linear-gradient(180deg, #FFFF00 0%, #FFCC00 100%) !important;
                border-color: #FF00FF !important;
                transform: translate(-3px, -3px) !important;
                box-shadow: 8px 8px 0px #000000 !important;
            }
            
            .nav-pill-active {
                background: linear-gradient(180deg, #FF00FF 0%, #CC00CC 100%) !important;
                border-color: #00FF00 !important;
                color: #FFFFFF !important;
                box-shadow: 5px 5px 0px #000000, 0 0 20px #FF00FF !important;
                text-shadow: 2px 2px 0px #000000 !important;
            }
            
            .content-card {
                background: #FFFFFF !important;
                border: 5px solid #FF00FF !important;
                border-radius: 0px !important;
                padding: 25px !important;
                margin: 20px !important;
                box-shadow: 10px 10px 0px #000000 !important;
                color: #000000 !important;
            }
            
            .content-card h3, .content-card h4 {
                color: #FF00FF !important;
                font-family: 'Impact', 'Arial Black', sans-serif !important;
                font-size: 1.8rem !important;
                font-weight: 900 !important;
                margin-bottom: 20px !important;
                padding-bottom: 12px !important;
                border-bottom: 5px solid #00FFFF !important;
                text-transform: uppercase !important;
                letter-spacing: 2px !important;
                text-shadow: 2px 2px 0px #FFFF00 !important;
            }
            
            .game-card {
                background: #FFFF99 !important;
                border: 4px solid #000000 !important;
                padding: 18px !important;
                margin: 15px 0 !important;
                border-radius: 0px !important;
                transition: all 0.2s ease;
                box-shadow: 5px 5px 0px #000000 !important;
                color: #000000 !important;
            }
            
            .game-card:hover {
                transform: translate(-2px, -2px);
                box-shadow: 7px 7px 0px #000000 !important;
                background: #FFFFCC !important;
            }
            
            .pick-card {
                background: #CCFFFF !important;
                border: 3px solid #0066FF !important;
                border-radius: 0px !important;
                padding: 15px !important;
                margin: 12px 0 !important;
                transition: all 0.2s ease;
                box-shadow: 4px 4px 0px #000000 !important;
                color: #000000 !important;
            }
            
            .pick-card:hover {
                border-color: #FF00FF !important;
                box-shadow: 6px 6px 0px #000000 !important;
                transform: translate(-2px, -2px);
                background: #E0FFFF !important;
            }
            
            .team-logo {
                filter: drop-shadow(3px 3px 0px #000000);
                transition: transform 0.2s ease;
            }
            
            .team-logo:hover {
                transform: scale(1.15) rotate(5deg);
            }
            
            .stat-badge, .stat-card {
                background: linear-gradient(180deg, #FF6600 0%, #FF3300 100%) !important;
                color: #FFFFFF !important;
                padding: 15px 25px !important;
                border-radius: 0px !important;
                border: 3px solid #FFFF00 !important;
                font-family: 'Impact', sans-serif !important;
                font-size: 1.2rem !important;
                font-weight: 900 !important;
                box-shadow: 5px 5px 0px #000000 !important;
                text-align: center;
                text-shadow: 2px 2px 0px #000000 !important;
                letter-spacing: 2px !important;
            }
            
            /* Tables */
            table {
                background: #FFFFFF !important;
                border: 5px solid #000000 !important;
                border-radius: 0px !important;
                overflow: hidden;
                color: #000000 !important;
            }
            
            table th {
                background: linear-gradient(180deg, #00FFFF 0%, #00CCCC 100%) !important;
                color: #000000 !important;
                font-family: 'Impact', sans-serif !important;
                font-size: 1rem !important;
                font-weight: 900 !important;
                text-transform: uppercase !important;
                letter-spacing: 1px !important;
                border: 3px solid #000000 !important;
                padding: 12px !important;
                text-shadow: 1px 1px 0px #FFFFFF !important;
            }
            
            table td {
                color: #000000 !important;
                border: 2px solid #000000 !important;
                font-family: 'Verdana', sans-serif !important;
                font-weight: 700 !important;
                font-size: 13px !important;
                padding: 10px !important;
                background: #FFFFFF !important;
            }
            
            table tr:nth-child(even) td {
                background: #FFFF99 !important;
            }
            
            table tr:hover td {
                background: #FF99FF !important;
            }
            
            /* Cards */
            .card {
                background: #FFFFFF !important;
                border: 5px solid #FF00FF !important;
                border-radius: 0px !important;
                box-shadow: 8px 8px 0px #000000 !important;
                color: #000000 !important;
            }
            
            .card-header {
                background: linear-gradient(180deg, #FF00FF 0%, #CC00CC 100%) !important;
                border-bottom: 4px solid #000000 !important;
                color: #FFFFFF !important;
                font-weight: 900 !important;
                border-radius: 0px !important;
                text-shadow: 2px 2px 0px #000000 !important;
                font-family: 'Impact', sans-serif !important;
                text-transform: uppercase !important;
            }
            
            .card-body {
                background: #FFFFFF !important;
                color: #000000 !important;
            }
            
            /* Alerts */
            .alert {
                background: #FFFF00 !important;
                border: 4px solid #000000 !important;
                border-radius: 0px !important;
                color: #000000 !important;
                font-family: 'Verdana', sans-serif !important;
                font-weight: 700 !important;
                box-shadow: 5px 5px 0px #000000 !important;
            }
            
            /* Buttons */
            .btn {
                border-radius: 0px !important;
                border: 4px solid #000000 !important;
                background: linear-gradient(180deg, #00FF00 0%, #00CC00 100%) !important;
                color: #000000 !important;
                font-family: 'Impact', sans-serif !important;
                font-size: 1rem !important;
                font-weight: 900 !important;
                padding: 12px 28px !important;
                box-shadow: 5px 5px 0px #000000 !important;
                transition: all 0.2s ease !important;
                text-transform: uppercase !important;
                letter-spacing: 1px !important;
                text-shadow: 1px 1px 0px #FFFFFF !important;
            }
            
            .btn:hover {
                background: linear-gradient(180deg, #FFFF00 0%, #FFCC00 100%) !important;
                transform: translate(-2px, -2px) !important;
                box-shadow: 7px 7px 0px #000000 !important;
                color: #000000 !important;
            }
            
            /* Scrollbar */
            ::-webkit-scrollbar {
                width: 16px;
                background: #00FFFF;
            }
            
            ::-webkit-scrollbar-track {
                background: #000080;
                border: 3px solid #00FFFF;
            }
            
            ::-webkit-scrollbar-thumb {
                background: linear-gradient(180deg, #FF00FF 0%, #9900FF 100%);
                border: 3px solid #000000;
                border-radius: 0px;
            }
            
            ::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(180deg, #FFFF00 0%, #FFCC00 100%);
            }
            
            .nfl-logo {
                filter: drop-shadow(0 0 10px #FFFFFF) drop-shadow(5px 5px 0px #000000) !important;
            }
            
            .btn-custom {
                border-radius: 0px !important;
                padding: 12px 30px;
                font-weight: 900;
                text-transform: uppercase;
                letter-spacing: 1px;
                transition: all 0.2s ease;
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            .btn-custom:hover {
                transform: translate(-2px, -2px);
                box-shadow: 7px 7px 0px #000000;
            }
            .leaderboard-row {
                transition: all 0.2s ease;
                border-radius: 0px;
                padding: 10px;
            }
            .leaderboard-row:hover {
                background: #FFFF00 !important;
                transform: scale(1.02);
            }
            .podium-1 { 
                background: linear-gradient(180deg, #FFD700 0%, #FFA500 100%); 
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            .podium-2 { 
                background: linear-gradient(180deg, #C0C0C0 0%, #A8A8A8 100%); 
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            .podium-3 { 
                background: linear-gradient(180deg, #CD7F32 0%, #B87333 100%); 
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            
            /* Mobile Responsive Styles */
            @media (max-width: 768px) {
                body {
                    font-size: 12px !important;
                }
                
                .main-header {
                    padding: 15px 15px !important;
                    border-bottom: 6px solid #00FFFF !important;
                }
                
                .main-title {
                    font-size: 1.8rem !important;
                    letter-spacing: 1px !important;
                    text-shadow: 
                        2px 2px 0px #000000,
                        3px 3px 0px #FF00FF,
                        0 0 15px #00FFFF !important;
                }
                
                .nav-pill {
                    padding: 12px 15px !important;
                    margin: 8px 0 !important;
                    font-size: 13px !important;
                    box-shadow: 3px 3px 0px #000000 !important;
                    border: 3px solid #FFFF00 !important;
                    display: inline-block !important;
                    width: auto !important;
                }
                
                /* Horizontal scrollable navigation on mobile */
                .card-body {
                    padding: 10px !important;
                }
                
                /* Make navigation horizontal on mobile */
                #main-tabs {
                    display: flex !important;
                    flex-wrap: nowrap !important;
                    overflow-x: auto !important;
                    -webkit-overflow-scrolling: touch !important;
                    gap: 8px !important;
                    padding: 5px 0 !important;
                }
                
                #main-tabs label {
                    flex: 0 0 auto !important;
                    margin: 0 !important;
                }
                
                /* Hide navigation section titles and actions on mobile */
                .content-card h5,
                .content-card h6,
                .content-card hr,
                .content-card .btn-custom,
                #upload-status,
                #reload-status,
                #update-status {
                    display: none !important;
                }
                
                /* Make sidebar take less space */
                .row > [class*="col-lg-3"] {
                    width: 100% !important;
                    margin-bottom: 5px !important;
                    padding: 0 5px !important;
                }
                
                .sticky-top {
                    position: relative !important;
                    top: 0 !important;
                }
                
                .nav-pill:hover {
                    box-shadow: 5px 5px 0px #000000 !important;
                }
                
                .content-card {
                    padding: 15px !important;
                    margin: 10px 5px !important;
                    border: 3px solid #FF00FF !important;
                    box-shadow: 6px 6px 0px #000000 !important;
                }
                
                .content-card h3, .content-card h4 {
                    font-size: 1.3rem !important;
                    margin-bottom: 15px !important;
                    padding-bottom: 10px !important;
                    border-bottom: 3px solid #00FFFF !important;
                }
                
                .game-card {
                    padding: 12px !important;
                    margin: 10px 0 !important;
                    border: 3px solid #000000 !important;
                    box-shadow: 4px 4px 0px #000000 !important;
                }
                
                .pick-card {
                    padding: 10px !important;
                    margin: 8px 0 !important;
                    border: 2px solid #0066FF !important;
                    box-shadow: 3px 3px 0px #000000 !important;
                }
                
                .stat-badge, .stat-card {
                    padding: 10px 15px !important;
                    font-size: 1rem !important;
                    border: 2px solid #FFFF00 !important;
                    box-shadow: 4px 4px 0px #000000 !important;
                }
                
                table {
                    font-size: 11px !important;
                    border: 3px solid #000000 !important;
                    display: block;
                    overflow-x: auto;
                    -webkit-overflow-scrolling: touch;
                }
                
                table th {
                    padding: 8px 6px !important;
                    font-size: 11px !important;
                    border: 2px solid #000000 !important;
                    white-space: nowrap;
                }
                
                table td {
                    padding: 8px 6px !important;
                    font-size: 11px !important;
                    border: 1px solid #000000 !important;
                }
                
                .btn {
                    padding: 10px 20px !important;
                    font-size: 0.9rem !important;
                    border: 3px solid #000000 !important;
                    box-shadow: 4px 4px 0px #000000 !important;
                }
                
                .btn-custom {
                    padding: 10px 20px;
                    font-size: 0.85rem;
                    border: 3px solid #000000;
                    box-shadow: 4px 4px 0px #000000;
                }
                
                .nfl-logo {
                    height: 60px !important;
                    margin-bottom: 10px !important;
                }
                
                .team-logo {
                    max-width: 30px !important;
                    height: auto !important;
                }
                
                /* Make container full width on mobile */
                .container-fluid {
                    padding-left: 5px !important;
                    padding-right: 5px !important;
                }
                
                /* Stack columns on mobile */
                .row > div[class*="col-"] {
                    margin-bottom: 15px;
                }
                
                /* Make DataTables scrollable */
                .dash-table-container {
                    overflow-x: auto !important;
                    -webkit-overflow-scrolling: touch !important;
                }
                
                /* Adjust card spacing */
                .card {
                    margin-bottom: 15px !important;
                    border: 3px solid #FF00FF !important;
                    box-shadow: 5px 5px 0px #000000 !important;
                }
                
                .card-header {
                    padding: 10px 15px !important;
                    font-size: 1rem !important;
                }
                
                .card-body {
                    padding: 15px !important;
                }
                
                /* Alert adjustments */
                .alert {
                    padding: 10px !important;
                    margin-bottom: 10px !important;
                    font-size: 0.9rem !important;
                    border: 3px solid #000000 !important;
                    box-shadow: 4px 4px 0px #000000 !important;
                }
                
                /* Scrollbar for mobile */
                ::-webkit-scrollbar {
                    width: 10px;
                    height: 10px;
                }
                
                ::-webkit-scrollbar-track {
                    background: #000080;
                    border: 2px solid #00FFFF;
                }
                
                ::-webkit-scrollbar-thumb {
                    background: linear-gradient(180deg, #FF00FF 0%, #9900FF 100%);
                    border: 2px solid #000000;
                }
            }
            
            /* Extra small devices */
            @media (max-width: 480px) {
                /* Ultra compact for phones */
                .main-header {
                    padding: 10px 10px !important;
                }
                
                .nfl-logo {
                    height: 40px !important;
                    margin-bottom: 5px !important;
                }
                
                .main-title {
                    font-size: 1.3rem !important;
                }
                
                .main-header p {
                    display: none !important;
                }
                
                .content-card h3, .content-card h4 {
                    font-size: 1.1rem !important;
                }
                
                .nav-pill {
                    font-size: 10px !important;
                    padding: 8px 10px !important;
                    white-space: nowrap !important;
                }
                
                table {
                    font-size: 10px !important;
                }
                
                table th, table td {
                    padding: 6px 4px !important;
                    font-size: 10px !important;
                }
            }
            }
            .leaderboard-row:hover {
                background: #FFFF00 !important;
                transform: scale(1.02);
            }
            .podium-1 { 
                background: linear-gradient(180deg, #FFD700 0%, #FFA500 100%); 
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            .podium-2 { 
                background: linear-gradient(180deg, #C0C0C0 0%, #A8A8A8 100%); 
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            .podium-3 { 
                background: linear-gradient(180deg, #CD7F32 0%, #B87333 100%); 
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            }
            .leaderboard-row:hover {
                background: #FFFF00 !important;
                transform: scale(1.02);
            }
            .podium-1 { 
                background: linear-gradient(180deg, #FFD700 0%, #FFA500 100%); 
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            .podium-2 { 
                background: linear-gradient(180deg, #C0C0C0 0%, #A8A8A8 100%); 
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            .podium-3 { 
                background: linear-gradient(180deg, #CD7F32 0%, #B87333 100%); 
                border: 4px solid #000000;
                box-shadow: 5px 5px 0px #000000;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = dbc.Container([
    # Premium Header with Gradient
    html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Img(
                        src="https://static.www.nfl.com/image/upload/v1554321393/league/nvfr7ogywskqrfaiu38m.svg",
                        className="nfl-logo",
                        style={'height': '100px', 'marginBottom': '15px'}
                    ),
                    html.H1("NFL PICKS TRACKER", className="main-title"),
                    html.P("2025 Season Championship", 
                          style={'color': 'rgba(255,255,255,0.9)', 'fontSize': '18px', 'fontWeight': '500'}),
                    html.P(id="last-updated-display", 
                          style={'color': 'rgba(255,255,255,0.7)', 'fontSize': '14px', 'marginTop': '10px'}),
                ], className="text-center")
            ])
        ])
    ], className="main-header"),
    
    dbc.Row([
        # Sidebar Navigation
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🧭 Navigation", style={'color': 'white', 'fontWeight': '700', 'marginBottom': '20px'}),
                    dcc.RadioItems(
                        id='main-tabs',
                        options=[
                            {'label': html.Div(['🏆 Leaderboard'], className='nav-pill'), 'value': 'leaderboard'},
                            {'label': html.Div(['📊 Weekly Records'], className='nav-pill'), 'value': 'weekly_records'},
                            {'label': html.Div(['🎯 Weekly Picks'], className='nav-pill'), 'value': 'weekly_picks'},
                            {'label': html.Div(['📡 Live Games'], className='nav-pill'), 'value': 'live'},
                            {'label': html.Div(['📋 Grid View'], className='nav-pill'), 'value': 'grid'},
                            {'label': html.Div(['📈 Statistics'], className='nav-pill'), 'value': 'stats_dashboard'},
                            {'label': html.Div(['🏈 Team Breakdown'], className='nav-pill'), 'value': 'team_breakdown'},
                            {'label': html.Div(['⭐ Postseason Fantasy'], className='nav-pill'), 'value': 'postseason'},
                            {'label': html.Div(['🏆 Postseason Picks'], className='nav-pill'), 'value': 'postseason_picks'}
                        ],
                        value='leaderboard',
                        labelStyle={'display': 'block'}
                    ),
                    html.Hr(style={'margin': '25px 0'}),
                    html.H6("⚙️ Quick Actions", style={'color': 'white', 'fontWeight': '700', 'marginBottom': '15px'}),
                    dcc.Upload(
                        id='upload-picks',
                        children=dbc.Button([html.I(className="fas fa-upload me-2"), "Upload Excel"], 
                                          color="primary", className="w-100 mb-2 btn-custom", size="sm"),
                        multiple=False,
                        accept='.xlsx,.xlsm'
                    ),
                    html.Div(id='upload-status', style={'fontSize': '12px', 'marginBottom': '10px'}),
                    dbc.Button([html.I(className="fas fa-folder-open me-2"), "Reload Excel"], 
                             id='reload-file-btn', color='secondary', className="w-100 mb-2 btn-custom", size="sm"),
                    html.Div(id='reload-status', style={'fontSize': '12px', 'marginBottom': '10px'}),
                    dbc.Button([html.I(className="fas fa-sync-alt me-2"), "Update ESPN"], 
                             id='update-btn', color='success', className="w-100 mb-2 btn-custom", size="sm"),
                    html.Div(id='update-status', style={'fontSize': '12px'}),
                ])
            ], className="content-card sticky-top", style={'top': '20px'})
        ], width=12, lg=3, className="mb-4"),
        
        # Main Content Area
        dbc.Col([
            html.Div(id="tab-content")
        ], width=12, lg=9)
    ]),
    
    # Manual Entry Modal
    dbc.Modal([
        dbc.ModalHeader("Manual Pick Entry"),
        dbc.ModalBody([html.Div(id='manual-entry-form')]),
        dbc.ModalFooter([
            dbc.Button("Close", id="close-modal", className="ms-auto", n_clicks=0)
        ])
    ], id="manual-entry-modal", size="lg"),
], fluid=True, style={'padding': '0'})

# Team logo mapping for ESPN URLs
def get_team_logo_mapping():
    """Map team names to ESPN team IDs for logo URLs"""
    return {
        'Arizona Cardinals': 22,
        'Atlanta Falcons': 1,
        'Baltimore Ravens': 33,
        'Buffalo Bills': 2,
        'Carolina Panthers': 29,
        'Chicago Bears': 3,
        'Cincinnati Bengals': 4,
        'Cleveland Browns': 5,
        'Dallas Cowboys': 6,
        'Denver Broncos': 7,
        'Detroit Lions': 8,
        'Green Bay Packers': 9,
        'Houston Texans': 34,
        'Indianapolis Colts': 11,
        'Jacksonville Jaguars': 30,
        'Kansas City Chiefs': 12,
        'Las Vegas Raiders': 13,
        'Los Angeles Chargers': 24,
        'Los Angeles Rams': 14,
        'Miami Dolphins': 15,
        'Minnesota Vikings': 16,
        'New England Patriots': 17,
        'New Orleans Saints': 18,
        'New York Giants': 19,
        'New York Jets': 20,
        'Philadelphia Eagles': 21,
        'Pittsburgh Steelers': 23,
        'San Francisco 49ers': 25,
        'Seattle Seahawks': 26,
        'Tampa Bay Buccaneers': 27,
        'Tennessee Titans': 10,
        'Washington Commanders': 28
    }

# --- Playoff data helpers ---
def fetch_espn_standings(season=2025):
    try:
        url = f"https://site.api.espn.com/apis/v2/sports/football/nfl/standings?season={season}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

def parse_playoff_picture(standings_json):
    """Return conferences with seed order and team meta. Best-effort (approximate sorting by wins/points)."""
    if not standings_json:
        return {"AFC": [], "NFC": []}
    conferences = {"AFC": [], "NFC": []}
    try:
        for child in standings_json.get('children', []):  # conferences
            conf_name = child.get('name', '').upper()
            if conf_name not in conferences:
                continue
            # Pull all team entries under divisions
            teams = []
            for div in child.get('children', []):
                for t in div.get('standings', []):
                    team = t.get('team', {})
                    records = t.get('records', [])
                    overall = next((r for r in records if r.get('type') == 'overall'), {})
                    wins = int(overall.get('wins', 0))
                    losses = int(overall.get('losses', 0))
                    ties = int(overall.get('ties', 0))
                    teams.append({
                        'id': team.get('id'),
                        'name': team.get('displayName') or team.get('name'),
                        'abbrev': team.get('abbreviation'),
                        'wins': wins,
                        'losses': losses,
                        'ties': ties,
                        'clinched': bool(t.get('clincher')) if 'clincher' in t else False,
                        'eliminated': bool(t.get('eliminated')) if 'eliminated' in t else False,
                    })
            # Approximate seed order by wins, then losses, then ties
            teams.sort(key=lambda x: (-x['wins'], x['losses'], -x['ties'], x['name']))
            conferences[conf_name] = teams
    except Exception:
        return {"AFC": [], "NFC": []}
    return conferences

def get_locked_and_bubble(conferences):
    """Determine locked (clinched/top 7) vs bubble (rest not eliminated)."""
    locked_ids = set()
    bubble_ids = set()
    for conf_name, teams in conferences.items():
        top = teams[:7]
        for i, t in enumerate(teams):
            # Treat explicit clinched as locked; otherwise top 7 provisional
            if t.get('clinched') or t in top:
                locked_ids.add(str(t.get('id')))
            elif not t.get('eliminated'):
                bubble_ids.add(str(t.get('id')))
    return locked_ids, bubble_ids

def fetch_team_roster(team_id, season=2025):
    try:
        url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/teams/{team_id}/roster?season={season}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        j = r.json()
        items = j.get('entries') or j.get('items') or []
        players = []
        for p in items:
            # Follow player ref if needed
            if isinstance(p, dict) and 'player' in p:
                pref = p['player'].get('$ref')
                if pref:
                    pr = requests.get(pref, timeout=10)
                    if pr.status_code == 200:
                        pj = pr.json()
                        players.append({
                            'id': str(pj.get('id')) if pj.get('id') is not None else None,
                            'name': pj.get('fullName') or pj.get('displayName'),
                            'position': pj.get('position', {}).get('abbreviation') or pj.get('position', {}).get('name') or '',
                            'number': pj.get('jersey'),
                            'teamId': str(team_id)
                        })
            elif isinstance(p, dict):
                players.append({
                    'id': str(p.get('id')) if p.get('id') is not None else None,
                    'name': p.get('fullName') or p.get('displayName') or p.get('name'),
                    'position': p.get('position', {}).get('abbreviation') or p.get('position', {}).get('name') or '',
                    'number': p.get('jersey'),
                    'teamId': str(team_id)
                })
        return players
    except Exception:
        return []

def fetch_player_stats(player_id, season=2025):
    """Best-effort season stats fetch from ESPN core API. Returns a flat dict of key stats.
    Fields: GP, PassYds, PassTD, RushYds, RushTD, RecYds, RecTD
    """
    try:
        # Get athlete endpoint and find statistics ref
        base = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes/{player_id}"
        ar = requests.get(base, timeout=10)
        if ar.status_code != 200:
            return {}
        aj = ar.json()
        stats_ref = None
        if isinstance(aj, dict):
            stats = aj.get('statistics')
            if isinstance(stats, dict) and '$ref' in stats:
                stats_ref = stats['$ref']
        # Fall back to athletes statistics listing if available
        if not stats_ref:
            stats_ref = base + f"/statistics?season={season}"
        else:
            # Ensure season parameter
            if 'season=' not in stats_ref:
                stats_ref = stats_ref + ("&" if "?" in stats_ref else "?") + f"season={season}"

        sr = requests.get(stats_ref, timeout=10)
        if sr.status_code != 200:
            return {}
        sj = sr.json()
        items = sj.get('splits') or sj.get('items') or []
        # Flatten known categories
        out = {'GP': None, 'PassYds': None, 'PassTD': None, 'RushYds': None, 'RushTD': None, 'RecYds': None, 'RecTD': None}
        def try_get(stat_dict, *keys):
            for k in keys:
                if k in stat_dict and stat_dict[k] is not None:
                    return stat_dict[k]
            return None
        # Iterate over items looking for season totals
        for it in items:
            cat = (it.get('name') or it.get('type') or '').lower()
            stats = it.get('stats') or it.get('statistics') or {}
            if 'passing' in cat:
                out['PassYds'] = try_get(stats, 'yards', 'passingYards', 'yds') or out['PassYds']
                out['PassTD'] = try_get(stats, 'touchdowns', 'passingTouchdowns', 'td') or out['PassTD']
            elif 'rushing' in cat:
                out['RushYds'] = try_get(stats, 'yards', 'rushingYards', 'yds') or out['RushYds']
                out['RushTD'] = try_get(stats, 'touchdowns', 'rushingTouchdowns', 'td') or out['RushTD']
            elif 'receiving' in cat:
                out['RecYds'] = try_get(stats, 'yards', 'receivingYards', 'yds') or out['RecYds']
                out['RecTD'] = try_get(stats, 'touchdowns', 'receivingTouchdowns', 'td') or out['RecTD']
            elif 'games' in cat or 'participation' in cat or 'general' in cat:
                out['GP'] = try_get(stats, 'gamesPlayed', 'games', 'gp') or out['GP']
        # Clean ints
        for k, v in list(out.items()):
            if v is None:
                continue
            try:
                out[k] = int(float(v))
            except Exception:
                pass
        return out
    except Exception:
        return {}

def build_players_pool(locked_ids, bubble_ids):
    locked_players = []
    bubble_players = []
    for tid in locked_ids:
        locked_players.extend(fetch_team_roster(tid))
    for tid in bubble_ids:
        bubble_players.extend(fetch_team_roster(tid))
    return locked_players, bubble_players

def apply_playoff_overrides(conferences, locked_ids, bubble_ids):
        """Apply user-provided scenario overrides to correct clinch/bubble state.
        Scenario per user: KC eliminated; two spots left:
            - AFC: Ravens or Steelers
            - NFC: Panthers or Buccaneers
        """
        # Map known IDs
        TEAM_IDS = {
                'Kansas City Chiefs': '12',
                'Baltimore Ravens': '33',
                'Pittsburgh Steelers': '23',
                'Carolina Panthers': '29',
                'Tampa Bay Buccaneers': '27',
        }

        # Remove Chiefs from any pool
        chiefs_id = TEAM_IDS['Kansas City Chiefs']
        locked_ids.discard(chiefs_id)
        bubble_ids.discard(chiefs_id)

        # Ensure AFC bubble includes Ravens and Steelers
        bubble_ids.add(TEAM_IDS['Baltimore Ravens'])
        bubble_ids.add(TEAM_IDS['Pittsburgh Steelers'])

        # Ensure NFC bubble includes Panthers and Buccaneers
        bubble_ids.add(TEAM_IDS['Carolina Panthers'])
        bubble_ids.add(TEAM_IDS['Tampa Bay Buccaneers'])

        return locked_ids, bubble_ids

def get_team_logo_url(team_name):
    """Get ESPN logo URL for a team"""
    if not team_name or team_name == "TIE":
        return None
    
    team_mapping = get_team_logo_mapping()
    
    # Try exact match first
    if team_name in team_mapping:
        team_id = team_mapping[team_name]
        return f"https://a.espncdn.com/i/teamlogos/nfl/500/{team_id}.png"
    
    # Try partial matches
    team_lower = team_name.lower()
    for full_name, team_id in team_mapping.items():
        if (full_name.lower() in team_lower or 
            any(word in team_lower for word in full_name.lower().split())):
            return f"https://a.espncdn.com/i/teamlogos/nfl/500/{team_id}.png"
    
    return None

def get_player_favorite_team_logo(player_name):
    """Get the logo of a player's most frequently picked team"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        # Get player's picks
        df = pd.read_sql_query(f"SELECT {player_name}_pick FROM picks WHERE {player_name}_pick IS NOT NULL", conn)
        conn.close()
        
        if df.empty:
            return None
        
        # Count team picks
        pick_counts = df[f'{player_name}_pick'].value_counts()
        if len(pick_counts) > 0:
            most_picked_team = pick_counts.index[0]
            return get_team_logo_url(most_picked_team)
        
        return None
    except:
        return None

def create_team_display(team_name, show_logo=True, logo_size="30px"):
    """Create a display element with team logo and name"""
    if not team_name:
        return "-"
    
    if not show_logo:
        return team_name
    
    logo_url = get_team_logo_url(team_name)
    
    if logo_url:
        return html.Div([
            html.Img(
                src=logo_url,
                style={
                    'height': logo_size,
                    'width': logo_size,
                    'marginRight': '8px',
                    'verticalAlign': 'middle'
                }
            ),
            html.Span(team_name, style={'verticalAlign': 'middle'})
        ], style={'display': 'inline-flex', 'alignItems': 'center'})
    else:
        return team_name
def init_database():
    """Initialize the database with required tables"""
    try:
        conn = sqlite3.connect('picks.db')
        cursor = conn.cursor()
        
        # Create picks table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS picks (
                game_id INTEGER PRIMARY KEY,
                week INTEGER,
                away_team TEXT,
                home_team TEXT,
                bobby_pick TEXT,
                chet_pick TEXT,
                clyde_pick TEXT,
                henry_pick TEXT,
                nick_pick TEXT,
                riley_pick TEXT,
                actual_winner TEXT,
                game_date TEXT,
                away_score INTEGER,
                home_score INTEGER,
                bobby_tiebreaker INTEGER,
                chet_tiebreaker INTEGER,
                clyde_tiebreaker INTEGER,
                henry_tiebreaker INTEGER,
                nick_tiebreaker INTEGER,
                riley_tiebreaker INTEGER,
                is_tiebreaker_game BOOLEAN DEFAULT 0
            )
        ''')
        
        # Add new columns to existing table if they don't exist
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN away_score INTEGER")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN home_score INTEGER")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN bobby_tiebreaker INTEGER")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN chet_tiebreaker INTEGER")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN clyde_tiebreaker INTEGER")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN henry_tiebreaker INTEGER")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN nick_tiebreaker INTEGER")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN riley_tiebreaker INTEGER")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN is_tiebreaker_game BOOLEAN DEFAULT 0")
        except:
            pass
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

def auto_load_picks_on_startup():
    """Auto-load picks from Excel file if database is empty"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM picks")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM picks WHERE actual_winner IS NOT NULL")
        results_count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            logger.info("Database is empty, attempting to auto-load picks from Excel...")
            message, success = load_excel_from_disk()
            if success:
                logger.info(message)
                # If we just imported picks and have no results, fetch them immediately
                logger.info("No results present yet, requesting latest scores from ESPN...")
                res_message, res_success = update_results_from_api()
                if res_success:
                    logger.info(res_message)
                else:
                    logger.warning(res_message)
            else:
                logger.error(message)
        elif count > 0 and results_count == 0:
            # Picks exist but no results recorded; try to pull scores so the UI isn't blank
            logger.info("Picks exist but no game results yet; fetching from ESPN...")
            res_message, res_success = update_results_from_api()
            if res_success:
                logger.info(res_message)
            else:
                logger.warning(res_message)
    except Exception as e:
        logger.error(f"Auto-load failed: {e}")

def get_db_connection():
    try:
        # Initialize database if needed
        if not os.path.exists('picks.db'):
            init_database()
        
        conn = sqlite3.connect('picks.db', check_same_thread=False, timeout=30)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def process_excel_file(contents, filename):
    """Process uploaded Excel file and import to database - Custom format for NFL picks"""
    try:
        # Decode the uploaded file
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Read Excel file with openpyxl engine
        excel_file = io.BytesIO(decoded)
        
        # Get all sheet names
        xl_file = pd.ExcelFile(excel_file)
        sheet_names = xl_file.sheet_names
        
        # Connect to database
        conn = get_db_connection()
        if not conn:
            return "Database connection failed", False
        
        total_games = 0
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        
        # Process each sheet (week)
        for sheet_name in sheet_names:
            # Skip the cumulative sheet
            if sheet_name.lower() == 'cumulative':
                continue
                
            try:
                # Determine week number from sheet name
                if sheet_name.lower().startswith('sheet'):
                    week_num = int(sheet_name.replace('Sheet', '').replace('sheet', ''))
                else:
                    continue
                
                # Read the sheet without headers
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                
                # Clear existing data for this week
                conn.execute("DELETE FROM picks WHERE week = ?", (week_num,))

                # Process only rows that have actual picks (marked with 'x')
                game_entries = []  # (row_idx, game_id)
                for idx, row in df.iterrows():
                    # Skip header rows and rows without team names
                    if idx < 2 or pd.isna(row.iloc[7]) or pd.isna(row.iloc[9]):
                        continue

                    pick_cols = list(row.iloc[1:7]) + list(row.iloc[10:16])
                    has_x = any((isinstance(v, str) and v.strip().lower() == 'x') for v in pick_cols)
                    if not has_x:
                        # Ignore rows without any picks (prevents score rows from becoming games)
                        continue

                    # Extract team names (columns 7 and 9)
                    away_team = str(row.iloc[7]).strip()
                    home_team = str(row.iloc[9]).strip()

                    # Skip if team names are invalid
                    if not away_team or not home_team or away_team == 'nan' or home_team == 'nan':
                        continue

                    # Clean team names (remove extra characters)
                    away_team = away_team.replace(' ¹', '').replace(' ²', '').replace(' ³', '')
                    home_team = home_team.replace(' ¹', '').replace(' ²', '').replace(' ³', '')

                    # Determine each person's pick
                    picks = {}
                    for i, person in enumerate(people):
                        away_pick = row.iloc[i + 1] if i + 1 < len(row) else None
                        home_pick = row.iloc[i + 10] if i + 10 < len(row) else None

                        if pd.notna(away_pick) and str(away_pick).strip().lower() == 'x':
                            picks[f'{person}_pick'] = away_team
                        elif pd.notna(home_pick) and str(home_pick).strip().lower() == 'x':
                            picks[f'{person}_pick'] = home_team
                        else:
                            picks[f'{person}_pick'] = None

                    # Insert into database
                    conn.execute('''
                        INSERT INTO picks (week, away_team, home_team, bobby_pick, chet_pick, 
                                         clyde_pick, henry_pick, riley_pick, nick_pick)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        week_num, away_team, home_team,
                        picks.get('bobby_pick'), picks.get('chet_pick'), picks.get('clyde_pick'),
                        picks.get('henry_pick'), picks.get('riley_pick'), picks.get('nick_pick')
                    ))

                    game_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    game_entries.append((idx, game_id))
                    total_games += 1

                # Attach tiebreaker predictions to the last real game (row right after it)
                if game_entries:
                    last_row_idx, last_game_id = game_entries[-1]
                    tiebreakers = {}

                    # Look ahead a few rows after the last game to find the tiebreaker numbers
                    for offset in range(1, 4):  # check next up to 3 rows in case of blank separators
                        if last_row_idx + offset >= len(df):
                            break
                        next_row = df.iloc[last_row_idx + offset]
                        row_tbs = {}
                        for i, person in enumerate(people):
                            val1 = next_row.iloc[i + 1] if i + 1 < len(next_row) else None
                            val2 = next_row.iloc[i + 10] if i + 10 < len(next_row) else None
                            chosen = None
                            for candidate in (val1, val2):
                                if pd.notna(candidate) and str(candidate).replace('.', '', 1).isdigit():
                                    chosen = int(float(candidate))
                                    break
                            if chosen is not None:
                                row_tbs[f'{person}_tiebreaker'] = chosen
                        if row_tbs:
                            tiebreakers = row_tbs
                            break

                    if tiebreakers:
                        update_parts = []
                        update_values = []
                        for person in people:
                            tb_key = f'{person}_tiebreaker'
                            if tb_key in tiebreakers:
                                update_parts.append(f"{tb_key} = ?")
                                update_values.append(tiebreakers[tb_key])

                        if update_parts:
                            update_values.append(last_game_id)
                            conn.execute(f'''
                                UPDATE picks 
                                SET is_tiebreaker_game = 1, {', '.join(update_parts)}
                                WHERE game_id = ?
                            ''', update_values)
                    
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        if total_games == 0:
            return "No valid games found in the Excel file", False
        
        return f"Successfully imported {total_games} games from {len([s for s in sheet_names if s.lower() != 'cumulative'])} weeks", True
        
    except Exception as e:
        return f"Error processing file: {str(e)}", False


def load_excel_from_disk(file_path=None):
    """Load an Excel file from disk and reuse the existing import pipeline"""
    try:
        target_path = file_path

        # If no explicit file provided, pick the freshest Excel in the working directory
        if not target_path:
            latest = find_latest_excel_file()
            if latest:
                target_path = latest
                logger.info(f"Auto-selected latest Excel: {target_path}")
            else:
                target_path = Config.EXCEL_FILE_PATH

        if not os.path.isabs(target_path):
            target_path = os.path.join(os.getcwd(), target_path)

        if not os.path.exists(target_path):
            return f"Excel file not found at {target_path}", False

        with open(target_path, 'rb') as f:
            file_content = base64.b64encode(f.read()).decode()
            contents = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + file_content
            message, success = process_excel_file(contents, os.path.basename(target_path))
            if success:
                return f"Loaded picks from {target_path}", True
            return message, False
    except Exception as e:
        logger.error(f"Disk load failed: {e}")
        return f"Load failed: {e}", False

def update_results_from_api():
    """Update game results with scores from ESPN API"""
    try:
        import requests
        import json
        
        conn = get_db_connection()
        if not conn:
            return "Database connection failed", False
        
        # Add score columns if they don't exist
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN away_score INTEGER")
        except:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE picks ADD COLUMN home_score INTEGER")
        except:
            pass  # Column already exists
        
        current_year = Config.CURRENT_SEASON
        updated_games = 0
        
        # Check each week for completed games
        for week in range(1, 19):  # Weeks 1-18
            try:
                # ESPN API endpoint for NFL scoreboard
                url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}&dates={current_year}"
                
                response = requests.get(url, timeout=Config.ESPN_API_TIMEOUT)
                if response.status_code != 200:
                    continue
                
                data = response.json()
                
                # Process each game in the week
                if 'events' in data:
                    for game in data['events']:
                        try:
                            # Extract game information
                            if 'competitions' not in game or not game['competitions']:
                                continue
                            
                            competition = game['competitions'][0]
                            
                            # Check if game is completed
                            status = competition.get('status', {})
                            if status.get('type', {}).get('name') != 'STATUS_FINAL':
                                continue  # Skip if game not finished
                            
                            # Get team information
                            competitors = competition.get('competitors', [])
                            if len(competitors) != 2:
                                continue
                            
                            # Determine home and away teams with scores
                            home_team = None
                            away_team = None
                            home_score = 0
                            away_score = 0
                            
                            for team in competitors:
                                team_name = team.get('team', {}).get('displayName', '')
                                team_score = int(team.get('score', 0))
                                
                                if team.get('homeAway') == 'home':
                                    home_team = team_name
                                    home_score = team_score
                                else:
                                    away_team = team_name
                                    away_score = team_score
                            
                            if not home_team or not away_team:
                                continue
                            
                            # Determine winner
                            if home_score > away_score:
                                winner = home_team
                            elif away_score > home_score:
                                winner = away_team
                            else:
                                winner = "TIE"  # Handle ties (rare in NFL)
                            
                            # Clean team names to match your database format
                            home_team_clean = clean_team_name(home_team)
                            away_team_clean = clean_team_name(away_team)
                            winner_clean = clean_team_name(winner) if winner != "TIE" else "TIE"
                            
                            # Update database with scores and winner
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE picks 
                                SET actual_winner = ?, away_score = ?, home_score = ?
                                WHERE week = ? 
                                AND (
                                    (LOWER(away_team) LIKE ? AND LOWER(home_team) LIKE ?) OR
                                    (LOWER(away_team) LIKE ? AND LOWER(home_team) LIKE ?)
                                )
                                AND actual_winner IS NULL
                            ''', (
                                winner_clean, away_score, home_score,
                                week,
                                f'%{away_team_clean.lower()}%',
                                f'%{home_team_clean.lower()}%',
                                f'%{home_team_clean.lower()}%',
                                f'%{away_team_clean.lower()}%'
                            ))
                            
                            if cursor.rowcount > 0:
                                updated_games += cursor.rowcount
                                
                        except Exception as e:
                            print(f"Error processing game: {e}")
                            continue
                            
            except Exception as e:
                print(f"Error processing week {week}: {e}")
                continue
        mark_tiebreaker_games(conn)
        conn.commit()
        conn.close()
        
        if updated_games > 0:
            return f"Successfully updated {updated_games} games with scores and results!", True
        else:
            return "No new completed games found to update.", True
            
    except Exception as e:
        return f"Update failed: {str(e)}", False

def clean_team_name(team_name):
    """Clean team names to match database format"""
    if not team_name or team_name == "TIE":
        return team_name
    
    # Common team name mappings
    name_mappings = {
        'Arizona Cardinals': 'Arizona Cardinals',
        'Atlanta Falcons': 'Atlanta Falcons', 
        'Baltimore Ravens': 'Baltimore Ravens',
        'Buffalo Bills': 'Buffalo Bills',
        'Carolina Panthers': 'Carolina Panthers',
        'Chicago Bears': 'Chicago Bears',
        'Cincinnati Bengals': 'Cincinnati Bengals',
        'Cleveland Browns': 'Cleveland Browns',
        'Dallas Cowboys': 'Dallas Cowboys',
        'Denver Broncos': 'Denver Broncos',
        'Detroit Lions': 'Detroit Lions',
        'Green Bay Packers': 'Green Bay Packers',
        'Houston Texans': 'Houston Texans',
        'Indianapolis Colts': 'Indianapolis Colts',
        'Jacksonville Jaguars': 'Jacksonville Jaguars',
        'Kansas City Chiefs': 'Kansas City Chiefs',
        'Las Vegas Raiders': 'Las Vegas Raiders',
        'Los Angeles Chargers': 'Los Angeles Chargers',
        'Los Angeles Rams': 'Los Angeles Rams',
        'Miami Dolphins': 'Miami Dolphins',
        'Minnesota Vikings': 'Minnesota Vikings',
        'New England Patriots': 'New England Patriots',
        'New Orleans Saints': 'New Orleans Saints',
        'New York Giants': 'New York Giants',
        'New York Jets': 'New York Jets',
        'Philadelphia Eagles': 'Philadelphia Eagles',
        'Pittsburgh Steelers': 'Pittsburgh Steelers',
        'San Francisco 49ers': 'San Francisco 49ers',
        'Seattle Seahawks': 'Seattle Seahawks',
        'Tampa Bay Buccaneers': 'Tampa Bay Buccaneers',
        'Tennessee Titans': 'Tennessee Titans',
        'Washington Commanders': 'Washington Commanders'
    }
    
    # Try exact match first
    if team_name in name_mappings:
        return name_mappings[team_name]
    
    # Try partial matches for common variations
    team_lower = team_name.lower()
    for full_name, clean_name in name_mappings.items():
        if full_name.lower() in team_lower or any(word in team_lower for word in full_name.lower().split()):
            return clean_name
    
    # Return original if no match found
    return team_name

def get_last_updated():
    """Get timestamp of last data update"""
    try:
        conn = get_db_connection()
        if not conn:
            return "Unknown"
        
        cursor = conn.cursor()
        # Get the most recent game with a result
        cursor.execute("SELECT MAX(game_id) FROM picks WHERE actual_winner IS NOT NULL")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return datetime.now().strftime("%m/%d/%Y at %I:%M %p")
        return "No completed games"
    except:
        return "Unknown"

def mark_tiebreaker_games(conn: sqlite3.Connection | None = None):
    """Mark the last game of each week as the tiebreaker game.
    If a connection is provided, it is reused to avoid locking; otherwise a new
    connection is opened and closed here.
    """
    try:
        owns_conn = False
        if conn is None:
            conn = get_db_connection()
            owns_conn = True
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Get all weeks that have games
        cursor.execute("SELECT DISTINCT week FROM picks ORDER BY week")
        weeks = cursor.fetchall()
        
        for (week,) in weeks:
            # If the importer already marked a tiebreaker game, respect it
            cursor.execute("SELECT COUNT(*) FROM picks WHERE week = ? AND is_tiebreaker_game = 1", (week,))
            flagged_row = cursor.fetchone()
            flagged = flagged_row[0] if flagged_row else 0
            if flagged > 0:
                continue

            # Otherwise, fallback to the last game of the week
            cursor.execute("""
                UPDATE picks 
                SET is_tiebreaker_game = 1 
                WHERE week = ? AND game_id = (
                    SELECT MAX(game_id) FROM picks WHERE week = ?
                )
            """, (week, week))
        
        if owns_conn:
            conn.commit()
            conn.close()
        
    except Exception as e:
        print(f"Error marking tiebreaker games: {e}")

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
        message, success = process_excel_file(contents, filename)
        color = "success" if success else "danger"
        return dbc.Alert(message, color=color, dismissable=True)
        
    except Exception as e:
        return dbc.Alert(f"Upload error: {str(e)}", color="danger", dismissable=True)


@app.callback(
    Output('reload-status', 'children'),
    Input('reload-file-btn', 'n_clicks')
)
def reload_from_disk(n_clicks):
    if not n_clicks:
        return ""

    message, success = load_excel_from_disk()
    color = "success" if success else "danger"
    return dbc.Alert(message, color=color, dismissable=True)

# Manual entry modal callback
@app.callback(
    Output("manual-entry-modal", "is_open"),
    Output('manual-entry-form', 'children'),
    [Input("manual-entry-btn", "n_clicks"), Input("close-modal", "n_clicks")],
    [State("manual-entry-modal", "is_open")]
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        form_content = create_manual_entry_form() if not is_open else []
        return not is_open, form_content
    return is_open, []

def create_manual_entry_form():
    """Create form for manual data entry"""
    return [
        dbc.Row([
            dbc.Col([
                dbc.Label("Week"),
                dbc.Input(id="manual-week", type="number", min=1, max=18, value=1)
            ], width=6),
            dbc.Col([
                dbc.Label("Game Date"),
                dbc.Input(id="manual-date", type="date")
            ], width=6)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Label("Away Team"),
                dbc.Input(id="manual-away-team", placeholder="e.g., Chiefs")
            ], width=6),
            dbc.Col([
                dbc.Label("Home Team"),
                dbc.Input(id="manual-home-team", placeholder="e.g., Bills")
            ], width=6)
        ], className="mb-3"),
        
        html.H5("Picks", className="mb-2"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Bobby"),
                dbc.Select(id="manual-bobby", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4),
            dbc.Col([
                dbc.Label("Chet"),
                dbc.Select(id="manual-chet", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4),
            dbc.Col([
                dbc.Label("Clyde"),
                dbc.Select(id="manual-clyde", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4)
        ], className="mb-2"),
        
        dbc.Row([
            dbc.Col([
                dbc.Label("Henry"),
                dbc.Select(id="manual-henry", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4),
            dbc.Col([
                dbc.Label("Nick"),
                dbc.Select(id="manual-nick", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4),
            dbc.Col([
                dbc.Label("Riley"),
                dbc.Select(id="manual-riley", options=[
                    {"label": "Away", "value": "away"},
                    {"label": "Home", "value": "home"}
                ])
            ], width=4)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Label("Actual Winner (if known)"),
                dbc.Select(id="manual-winner", options=[
                    {"label": "Not decided yet", "value": ""},
                    {"label": "Away Team", "value": "away"},
                    {"label": "Home Team", "value": "home"}
                ])
            ], width=6)
        ], className="mb-3"),
        
        dbc.Button("Add Game", id="add-game-btn", color="primary")
    ]

# Update callback
@app.callback(
    Output('update-status', 'children'),
    Input('update-btn', 'n_clicks')
)
def update_status(n_clicks):
    if not n_clicks:
        return ""
    
    try:
        message, success = update_results_from_api()
        color = "success" if success else "warning"
        return dbc.Alert(message, color=color, dismissable=True)
    except Exception as e:
        return dbc.Alert(f"Update failed: {str(e)}", color="danger", dismissable=True)

# Main tab callback (now using RadioItems)
@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "value")
)
def render_tab_content(active_tab):
    if active_tab == "leaderboard":
        return render_leaderboard_tab()
    elif active_tab == "weekly_records":
        return render_weekly_records_tab()
    elif active_tab == "weekly_picks":
        return render_weekly_picks_tab()
    elif active_tab == "grid":
        return render_grid_tab()
    elif active_tab == "live":
        return render_live_tab()
    elif active_tab == "stats_dashboard":
        return render_stats_dashboard_tab()
    elif active_tab == "team_breakdown":
        return render_teams_tab()
    elif active_tab == "postseason":
        return render_postseason_tab()
    elif active_tab == "postseason_picks":
        return render_postseason_picks_tab()

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
                # Convert picks to team names for comparison
                if row[person_pick_col] == 'away':
                    person_team_pick = row['away_team']
                elif row[person_pick_col] == 'home':
                    person_team_pick = row['home_team']
                else:
                    person_team_pick = row[person_pick_col]
                
                # Convert actual winner
                if row['actual_winner'] == 'away':
                    actual_team_winner = row['away_team']
                elif row['actual_winner'] == 'home':
                    actual_team_winner = row['home_team']
                else:
                    actual_team_winner = row['actual_winner']
                
                if person_team_pick == actual_team_winner:
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

# Enhanced Leaderboard tab with logos in podium
def render_leaderboard_tab():
    standings_df = get_current_standings()
    
    if standings_df.empty:
        return dbc.Alert("No game results available. Upload picks and update results first.", color="info")
    
    # Create charts
    win_pct_chart = create_win_percentage_chart(standings_df)
    wins_chart = create_wins_comparison_chart(standings_df)
    
    # Create podium visualization for top 3 with recent favorite teams
    top_3 = standings_df.head(3)
    
    podium_cards = []
    medals = ["🥇", "🥈", "🥉"]
    colors = ["warning", "secondary", "dark"]
    
    for i, (_, player) in enumerate(top_3.iterrows()):
        # Get player's most picked team for logo display
        favorite_team_logo = get_player_favorite_team_logo(player['Player'].lower())
        
        podium_card_content = [
            html.H2(medals[i], className="text-center mb-2"),
            html.H4(player['Player'], className="text-center mb-2")
        ]
        
        # Add favorite team logo if available
        if favorite_team_logo:
            podium_card_content.insert(1, html.Div([
                html.Img(src=favorite_team_logo, style={'height': '40px', 'marginBottom': '10px'})
            ], className="text-center"))
        
        podium_card_content.extend([
            html.H5(f"{player['Wins']}-{player['Losses']}", className="text-center mb-1"),
            html.P(player['Win %'], className="text-center text-muted mb-0")
        ])
        
        podium_cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody(podium_card_content, className="py-4")
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
                    style_data={'backgroundColor': 'white', 'color': '#1a202c'},
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

# Weekly Picks Tab - PREMIUM DESIGN
def render_weekly_picks_tab():
    """Premium weekly picks display with modern design"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning", className="content-card")
        
        df = pd.read_sql_query("SELECT * FROM picks ORDER BY week, game_id", conn)
        conn.close()
        
        if df.empty:
            return html.Div([
                html.I(className="fas fa-inbox fa-3x", style={'color': '#D50A0A', 'marginBottom': '20px'}),
                html.H4("No Picks Data Available", style={'color': 'white'}),
                html.P("Upload an Excel file to get started", style={'color': 'white'})
            ], className="content-card text-center", style={'padding': '60px'})
        
        weeks = sorted(df['week'].unique())
        week_options = [{"label": f"Week {week}", "value": week} for week in weeks]
        
        return [
            html.Div([
                html.H4([html.I(className="fas fa-calendar-week me-3", style={'color': '#D50A0A'}), "Select Week"], 
                       style={'color': '#013369', 'fontWeight': '700', 'marginBottom': '20px'}),
                dcc.Dropdown(
                    id='week-selector',
                    options=week_options,
                    value=weeks[-1] if weeks else None,
                    placeholder="Choose a week...",
                    style={'fontSize': '16px'}
                )
            ], className="content-card"),
            
            html.Div(id='weekly-picks-content')
        ]
        
    except Exception as e:
        return dbc.Alert(f"Error loading weekly picks: {str(e)}", color="danger")

# Add callback for weekly picks with enhanced professional design
@app.callback(
    Output('weekly-picks-content', 'children'),
    Input('week-selector', 'value')
)
def update_weekly_picks_content(selected_week):
    if not selected_week:
        return dbc.Alert("👆 Please select a week to view picks.", color="info", className="text-center mt-4")
    
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database connection failed.", color="danger")
        
        # Get picks for selected week
        df = pd.read_sql_query(
            "SELECT * FROM picks WHERE week = ? ORDER BY game_id", 
            conn, 
            params=(selected_week,)
        )
        conn.close()
        
        if df.empty:
            return dbc.Alert(f"No games found for Week {selected_week}.", color="info", className="text-center mt-4")
        
        people = ['bobby', 'chet', 'clyde', 'henry', 'riley', 'nick']
        
        # Create individual game cards with modern design
        game_cards = []
        for i, game_row in df.iterrows():
            # Create team displays with logos
            away_logo_url = get_team_logo_url(game_row['away_team'])
            home_logo_url = get_team_logo_url(game_row['home_team'])
            winner_logo_url = get_team_logo_url(game_row['actual_winner']) if pd.notna(game_row['actual_winner']) else None
            
            # Game header with logos and better styling
            game_header = html.Div([
                html.Div([
                    html.Img(src=away_logo_url, style={'height': '50px', 'marginRight': '12px'}) if away_logo_url else "",
                    html.Div([
                        html.Strong(game_row['away_team'], style={'fontSize': '16px', 'display': 'block'}),
                        html.Span(f"{int(game_row['away_score'])}" if pd.notna(game_row['away_score']) else "", 
                                 style={'fontSize': '24px', 'fontWeight': 'bold', 'color': '#013369'})
                    ])
                ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1'}),
                
                html.Div("@", style={'margin': '0 20px', 'fontSize': '24px', 'fontWeight': 'bold', 'color': '#D50A0A'}),
                
                html.Div([
                    html.Div([
                        html.Strong(game_row['home_team'], style={'fontSize': '16px', 'display': 'block', 'textAlign': 'right'}),
                        html.Span(f"{int(game_row['home_score'])}" if pd.notna(game_row['home_score']) else "", 
                                 style={'fontSize': '24px', 'fontWeight': 'bold', 'color': '#013369', 'textAlign': 'right'})
                    ], style={'textAlign': 'right'}),
                    html.Img(src=home_logo_url, style={'height': '50px', 'marginLeft': '12px'}) if home_logo_url else "",
                ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'justifyContent': 'flex-end'})
            ], style={
                'display': 'flex', 
                'alignItems': 'center', 
                'marginBottom': '15px', 
                'padding': '15px', 
                'backgroundColor': '#f8f9fa', 
                'borderRadius': '8px',
                'border': '2px solid #e9ecef'
            })
            
            # Winner display and scoreline
            if pd.notna(game_row['actual_winner']) and game_row['actual_winner'] != 'TBD':
                score_total = None
                if pd.notna(game_row['away_score']) and pd.notna(game_row['home_score']):
                    score_total = int(game_row['away_score']) + int(game_row['home_score'])
                winner_display = html.Div([
                    html.Img(src=winner_logo_url, style={'height': '30px', 'marginRight': '10px'}) if winner_logo_url else "",
                    html.Span([
                        html.I(className="fas fa-trophy", style={'marginRight': '5px', 'color': '#FFD700'}),
                        html.Strong("Winner: ", style={'color': '#6c757d'}),
                        html.Strong(game_row['actual_winner'], style={'color': '#28a745'})
                    ]),
                    html.Span(
                        f" • Total Points: {score_total}" if score_total is not None else "",
                        style={'marginLeft': '10px', 'color': '#6c757d', 'fontWeight': '500'}
                    )
                ], style={
                    'display': 'flex', 
                    'alignItems': 'center', 
                    'marginBottom': '15px',
                    'padding': '10px',
                    'backgroundColor': '#d4edda',
                    'borderRadius': '5px',
                    'border': '1px solid #c3e6cb',
                    'flexWrap': 'wrap'
                })
            else:
                winner_display = html.Div([
                    html.I(className="fas fa-clock", style={'marginRight': '8px'}),
                    "Game Pending"
                ], style={
                    'fontStyle': 'italic', 
                    'color': '#6c757d', 
                    'marginBottom': '15px',
                    'padding': '10px',
                    'backgroundColor': '#fff3cd',
                    'borderRadius': '5px',
                    'border': '1px solid #ffc107'
                })
            
            # Tiebreaker display if this is the tiebreaker game
            tiebreaker_section = None
            if game_row.get('is_tiebreaker_game'):
                tiebreaker_predictions = []
                for person in people:
                    tb_col = f'{person}_tiebreaker'
                    if pd.notna(game_row.get(tb_col)):
                        prediction = int(game_row[tb_col])
                        actual = None
                        if pd.notna(game_row['away_score']) and pd.notna(game_row['home_score']):
                            actual = int(game_row['away_score']) + int(game_row['home_score'])
                        
                        diff_text = ""
                        diff_color = "#6c757d"
                        if actual:
                            diff = abs(prediction - actual)
                            if diff == 0:
                                diff_text = " ✓ EXACT!"
                                diff_color = "#28a745"
                            else:
                                diff_text = f" (off by {diff})"
                                diff_color = "#dc3545" if diff > 10 else "#ffc107"
                        
                        tiebreaker_predictions.append(
                            html.Div([
                                html.Strong(f"{person.title()}: ", style={'marginRight': '5px'}),
                                html.Span(f"{prediction} pts", style={'fontWeight': '600', 'color': '#013369'}),
                                html.Span(diff_text, style={'color': diff_color, 'fontSize': '12px', 'marginLeft': '5px'})
                            ], style={'display': 'inline-block', 'marginRight': '15px', 'marginBottom': '5px'})
                        )
                
                if tiebreaker_predictions:
                    tiebreaker_section = html.Div([
                        html.H6([
                            html.I(className="fas fa-balance-scale", style={'marginRight': '8px', 'color': '#D50A0A'}),
                            "Tiebreaker Predictions"
                        ], style={'color': '#013369', 'marginBottom': '10px'}),
                        html.Div(tiebreaker_predictions, style={'display': 'flex', 'flexWrap': 'wrap'})
                    ], style={
                        'marginTop': '15px',
                        'padding': '12px',
                        'backgroundColor': '#fff3cd',
                        'borderRadius': '5px',
                        'border': '2px solid #ffc107'
                    })
            
            # Picks display with logos and better cards
            picks_grid = []
            for person in people:
                person_pick_col = f'{person}_pick'
                person_pick = game_row[person_pick_col] if pd.notna(game_row[person_pick_col]) else None
                
                if person_pick:
                    pick_logo_url = get_team_logo_url(person_pick)
                    
                    # Determine pick correctness for styling
                    is_correct = (pd.notna(game_row['actual_winner']) and 
                                person_pick == game_row['actual_winner'])
                    is_incorrect = (pd.notna(game_row['actual_winner']) and 
                                  game_row['actual_winner'] != 'TBD' and 
                                  person_pick != game_row['actual_winner'])
                    
                    if is_correct:
                        bg_color = '#d4edda'
                        text_color = '#155724'
                        border_color = '#28a745'
                        icon = '✓'
                    elif is_incorrect:
                        bg_color = '#f8d7da'
                        text_color = '#721c24'
                        border_color = '#dc3545'
                        icon = '✗'
                    else:
                        bg_color = '#ffffff'
                        text_color = '#495057'
                        border_color = '#dee2e6'
                        icon = ''
                    
                    pick_card = html.Div([
                        html.Div(person.title(), style={
                            'fontSize': '11px', 
                            'fontWeight': 'bold', 
                            'marginBottom': '5px',
                            'color': '#6c757d',
                            'textTransform': 'uppercase'
                        }),
                        html.Div([
                            html.Img(src=pick_logo_url, style={'height': '30px', 'marginBottom': '5px'}) if pick_logo_url else "",
                            html.Div(person_pick, style={'fontSize': '12px', 'fontWeight': '600'}),
                            html.Div(icon, style={'fontSize': '18px', 'marginTop': '3px'}) if icon else None
                        ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'})
                    ], style={
                        'backgroundColor': bg_color,
                        'color': text_color,
                        'border': f'2px solid {border_color}',
                        'borderRadius': '8px',
                        'padding': '10px',
                        'margin': '5px',
                        'minWidth': '130px',
                        'textAlign': 'center',
                        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                    })
                else:
                    pick_card = html.Div([
                        html.Div(person.title(), style={
                            'fontSize': '11px', 
                            'fontWeight': 'bold', 
                            'marginBottom': '5px',
                            'color': '#6c757d',
                            'textTransform': 'uppercase'
                        }),
                        html.Div("No Pick", style={'fontSize': '12px', 'color': '#adb5bd', 'fontStyle': 'italic'})
                    ], style={
                        'backgroundColor': '#f8f9fa',
                        'color': '#6c757d',
                        'border': '1px dashed #dee2e6',
                        'borderRadius': '8px',
                        'padding': '10px',
                        'margin': '5px',
                        'fontSize': '12px',
                        'fontStyle': 'italic',
                        'minWidth': '130px',
                        'textAlign': 'center'
                    })
                
                picks_grid.append(pick_card)
            
            # Main picks section
            picks_section = html.Div([
                html.H6("Picks:", style={'color': '#013369', 'marginBottom': '10px', 'fontWeight': 'bold'}),
                html.Div(picks_grid, style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center'})
            ], style={'marginTop': '15px'})
            
            # Combine everything into a game card
            card_content = [game_header, winner_display, picks_section]
            if tiebreaker_section:
                card_content.append(tiebreaker_section)
            
            game_card = dbc.Card([
                dbc.CardBody(card_content)
            ], className="mb-3 shadow-sm", style={'border': '2px solid #e9ecef'})
            
            game_cards.append(game_card)
        
        return [
            dbc.Card([
                dbc.CardHeader(
                    html.H5(f"\ud83c\udfc8 Week {selected_week} - Picks & Results", className="mb-0", style={'color': '#013369'}),
                    style={'backgroundColor': '#f8f9fa', 'borderBottom': '3px solid #D50A0A'}
                ),
                dbc.CardBody([
                    dbc.Alert([
                        html.Strong("\ud83d\udcc8 Legend: "),
                        html.Span("\u2713 Correct", style={'color': '#155724', 'backgroundColor': '#d4edda', 'padding': '3px 10px', 'marginRight': '10px', 'borderRadius': '5px', 'fontWeight': '600'}),
                        html.Span("\u2717 Incorrect", style={'color': '#721c24', 'backgroundColor': '#f8d7da', 'padding': '3px 10px', 'borderRadius': '5px', 'fontWeight': '600'})
                    ], color="light", className="mb-3"),
                    
                    html.Div(game_cards)
                ])
            ], className="shadow")
        ]
        
    except Exception as e:
        return dbc.Alert(f"Error loading picks for week {selected_week}: {str(e)}", color="danger")


def render_postseason_tab():
    """Postseason Fantasy League template: 8 teams x 10 roster spots + player pools + rankings."""
    teams = [f"Team {i}" for i in range(1, 9)]
    slots = [f"Slot {i}" for i in range(1, 11)]
    data = [{"Team": t, **{s: "" for s in slots}} for t in teams]
    columns = ([{"name": "Team", "id": "Team"}] +
               [{"name": s, "id": s} for s in slots])

    roster_table = dash_table.DataTable(
        data=data,
        columns=columns,
        editable=True,
        style_table={"overflowX": "auto"},
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'minWidth': '100px', 'width': '100px', 'maxWidth': '140px'
        },
        style_header={
            'backgroundColor': '#00FFFF',
            'color': '#000000',
            'fontWeight': '900',
            'border': '4px solid #000000'
        },
        style_data={
            'backgroundColor': 'white',
            'color': '#1a202c',
            'border': '1px solid #000000'
        },
    )

    # Generic playoff rankings (template-only, no complex model)
    generic_rankings = [
        {"Rank": 1, "Player": "Patrick Mahomes", "Position": "QB", "Team": "KC"},
        {"Rank": 2, "Player": "Christian McCaffrey", "Position": "RB", "Team": "SF"},
        {"Rank": 3, "Player": "Josh Allen", "Position": "QB", "Team": "BUF"},
        {"Rank": 4, "Player": "Lamar Jackson", "Position": "QB", "Team": "BAL"},
        {"Rank": 5, "Player": "Tyreek Hill", "Position": "WR", "Team": "MIA"},
        {"Rank": 6, "Player": "Jalen Hurts", "Position": "QB", "Team": "PHI"},
        {"Rank": 7, "Player": "Travis Kelce", "Position": "TE", "Team": "KC"},
        {"Rank": 8, "Player": "Brock Purdy", "Position": "QB", "Team": "SF"},
        {"Rank": 9, "Player": "A.J. Brown", "Position": "WR", "Team": "PHI"},
        {"Rank": 10, "Player": "Stefon Diggs", "Position": "WR", "Team": "BUF"},
        {"Rank": 11, "Player": "Isiah Pacheco", "Position": "RB", "Team": "KC"},
        {"Rank": 12, "Player": "Deebo Samuel", "Position": "WR", "Team": "SF"},
        {"Rank": 13, "Player": "George Kittle", "Position": "TE", "Team": "SF"},
        {"Rank": 14, "Player": "James Cook", "Position": "RB", "Team": "BUF"},
        {"Rank": 15, "Player": "Mark Andrews", "Position": "TE", "Team": "BAL"},
        {"Rank": 16, "Player": "Joe Burrow", "Position": "QB", "Team": "CIN"},
        {"Rank": 17, "Player": "CeeDee Lamb", "Position": "WR", "Team": "DAL"},
        {"Rank": 18, "Player": "DeVonta Smith", "Position": "WR", "Team": "PHI"},
        {"Rank": 19, "Player": "Raheem Mostert", "Position": "RB", "Team": "MIA"},
        {"Rank": 20, "Player": "Zay Flowers", "Position": "WR", "Team": "BAL"},
        {"Rank": 21, "Player": "Brandon Aiyuk", "Position": "WR", "Team": "SF"},
        {"Rank": 22, "Player": "Gus Edwards", "Position": "RB", "Team": "BAL"},
        {"Rank": 23, "Player": "Tyler Bass", "Position": "K", "Team": "BUF"},
        {"Rank": 24, "Player": "Harrison Butker", "Position": "K", "Team": "KC"},
        {"Rank": 25, "Player": "Jake Elliott", "Position": "K", "Team": "PHI"},
        {"Rank": 26, "Player": "49ers DST", "Position": "DST", "Team": "SF"},
        {"Rank": 27, "Player": "Ravens DST", "Position": "DST", "Team": "BAL"},
        {"Rank": 28, "Player": "Bills DST", "Position": "DST", "Team": "BUF"},
        {"Rank": 29, "Player": "Chiefs DST", "Position": "DST", "Team": "KC"},
        {"Rank": 30, "Player": "Eagles DST", "Position": "DST", "Team": "PHI"},
    ]

    ranking_columns = [
        {"name": "Rank", "id": "Rank"},
        {"name": "Player", "id": "Player"},
        {"name": "Position", "id": "Position"},
        {"name": "Team", "id": "Team"},
    ]

    rankings_table = dash_table.DataTable(
        data=generic_rankings,
        columns=ranking_columns,
        style_table={"overflowX": "auto"},
        style_cell={'textAlign': 'center', 'padding': '10px'},
        style_header={'backgroundColor': '#0d6efd', 'color': 'white', 'fontWeight': 'bold'},
        style_data={'backgroundColor': 'white', 'color': '#1a202c'},
    )

    return dbc.Card([
        dbc.CardHeader([
            html.H4("Postseason Fantasy League (Template)", className="mb-0"),
            html.Small("8 teams • 10 roster spots each — fill in after your draft", className="text-muted")
        ]),
        dbc.CardBody([
            dbc.Alert([
                html.Strong("How to use: "),
                "Edit the table to enter drafted players for each team (10 slots). ",
                "Click 'Fetch Playoff Pools' to load current playoff players and bubble players.",
            ], color="info", className="mb-3"),
            roster_table,
            dbc.Button([html.I(className="fas fa-database me-2"), "Fetch Playoff Pools"], id="fetch-playoff", color="success", className="mt-3 btn-custom"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Locked-In Playoff Players"),
                        dbc.CardBody([
                            html.Div(id="locked-players")
                        ])
                    ])
                ], md=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Bubble Players (Not Yet Clinched)"),
                        dbc.CardBody([
                            html.Div(id="bubble-players")
                        ])
                    ])
                ], md=6)
            ], className="mt-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Positional Breakdown — Locked"),
                        dbc.CardBody([html.Div(id="locked-pos-breakdown")])
                    ])
                ], md=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Positional Breakdown — Bubble"),
                        dbc.CardBody([html.Div(id="bubble-pos-breakdown")])
                    ])
                ], md=6)
            ], className="mt-3"),
            dbc.Card([
                dbc.CardHeader("Current Playoff Bracket (Approximate)"),
                dbc.CardBody([
                    html.Div(id="bracket-view"),
                    html.Hr(),
                    html.H6("Potential Outcomes (Simplified)"),
                    html.Div(id="outcomes-list")
                ])
            ], className="mt-3"),
            dbc.Card([
                dbc.CardHeader("Generic Playoff Rankings (Template)"),
                dbc.CardBody([
                    dbc.Alert("Ordered by expected playoff volume and team strength — update after bracket locks.", color="light"),
                    rankings_table
                ])
            ], className="mt-3")
        ])
    ])

def render_postseason_picks_tab():
    """Template for postseason picks across rounds."""
    rounds = (["Wild Card"] * 6) + (["Divisional"] * 4) + (["Conference"] * 2) + (["Super Bowl"] * 1)
    data = [{
        "Round": r,
        "Away Team": "TBD",
        "Home Team": "TBD",
        "Game Date": "",
        "Your Pick": "",
        "Tiebreaker (SB)": "" if r == "Super Bowl" else ""
    } for r in rounds]
    columns = [
        {"name": "Round", "id": "Round"},
        {"name": "Away Team", "id": "Away Team"},
        {"name": "Home Team", "id": "Home Team"},
        {"name": "Game Date", "id": "Game Date"},
        {"name": "Your Pick", "id": "Your Pick"},
        {"name": "Tiebreaker (SB)", "id": "Tiebreaker (SB)"},
    ]

    picks_table = dash_table.DataTable(
        data=data,
        columns=columns,
        editable=True,
        style_table={"overflowX": "auto"},
        style_cell={'textAlign': 'center', 'padding': '10px'},
        style_header={'backgroundColor': '#0d6efd', 'color': 'white', 'fontWeight': 'bold'},
        style_data={'backgroundColor': 'white', 'color': '#1a202c'},
    )

    return dbc.Card([
        dbc.CardHeader("Postseason Picks (Template)"),
        dbc.CardBody([
            dbc.Alert([
                "Fill out your picks once matchups are set. ",
                "We'll add saving, validation, and scoring hooks later.",
            ], color="warning", className="mb-3"),
            picks_table
        ])
    ])

# Callbacks to populate playoff players, bracket, and outcomes
@app.callback(
    Output("locked-players", "children"),
    Output("bubble-players", "children"),
    Output("bracket-view", "children"),
    Output("outcomes-list", "children"),
    Output("locked-pos-breakdown", "children"),
    Output("bubble-pos-breakdown", "children"),
    Input("fetch-playoff", "n_clicks")
)
def fetch_playoff_pools(n_clicks):
    if not n_clicks:
        return dbc.Alert("Click the button to load pools.", color="info"), dbc.Alert("Click the button to load pools.", color="info"), dbc.Alert("Bracket will appear here.", color="light"), dbc.Alert("Outcomes will appear here.", color="light")

    standings = fetch_espn_standings(2025)
    conferences = parse_playoff_picture(standings)
    locked_ids, bubble_ids = get_locked_and_bubble(conferences)
    # Apply scenario overrides per user
    locked_ids, bubble_ids = apply_playoff_overrides(conferences, locked_ids, bubble_ids)
    locked_players, bubble_players = build_players_pool(locked_ids, bubble_ids)

    # Tables
    # Attach best-effort stats to players
    def with_stats(players):
        rows = []
        for p in players:
            row = dict(p)
            pid = p.get('id')
            stats = fetch_player_stats(pid) if pid else {}
            row.update({
                'GP': stats.get('GP'),
                'PassYds': stats.get('PassYds'),
                'PassTD': stats.get('PassTD'),
                'RushYds': stats.get('RushYds'),
                'RushTD': stats.get('RushTD'),
                'RecYds': stats.get('RecYds'),
                'RecTD': stats.get('RecTD'),
            })
            rows.append(row)
        return pd.DataFrame(rows)

    lp_df = with_stats(locked_players)
    bp_df = with_stats(bubble_players)
    lp_table = dash_table.DataTable(
        data=lp_df.to_dict('records'),
        columns=[{"name": c, "id": c} for c in lp_df.columns] if not lp_df.empty else [],
        style_cell={'textAlign': 'center', 'padding': '8px'},
        style_header={'backgroundColor': '#0d6efd', 'color': 'white', 'fontWeight': 'bold'},
        style_data={'backgroundColor': 'white', 'color': '#1a202c'},
        page_size=10,
        filter_action='native',
        sort_action='native',
        export_format='csv',
        export_headers='display'
    ) if not lp_df.empty else dbc.Alert("No data yet.", color="light")

    bp_table = dash_table.DataTable(
        data=bp_df.to_dict('records'),
        columns=[{"name": c, "id": c} for c in bp_df.columns] if not bp_df.empty else [],
        style_cell={'textAlign': 'center', 'padding': '8px'},
        style_header={'backgroundColor': '#ffc107', 'color': '#000', 'fontWeight': 'bold'},
        style_data={'backgroundColor': 'white', 'color': '#1a202c'},
        page_size=10,
        filter_action='native',
        sort_action='native',
        export_format='csv',
        export_headers='display'
    ) if not bp_df.empty else dbc.Alert("No data yet.", color="light")

    # Positional breakdown tables
    def pos_breakdown(df):
        if df.empty:
            return dbc.Alert("No data yet.", color="light")
        dfx = df.copy()
        dfx['TDs'] = (dfx[['PassTD','RushTD','RecTD']].fillna(0).sum(axis=1))
        agg = dfx.groupby('position').agg(
            Players=('name','count'),
            GP=('GP','sum'),
            PassYds=('PassYds','sum'),
            RushYds=('RushYds','sum'),
            RecYds=('RecYds','sum'),
            TDs=('TDs','sum')
        ).reset_index().rename(columns={'position':'Position'})
        return dash_table.DataTable(
            data=agg.to_dict('records'),
            columns=[{"name": c, "id": c} for c in agg.columns],
            style_cell={'textAlign': 'center', 'padding': '8px'},
            style_header={'backgroundColor': '#20c997', 'color': 'white', 'fontWeight': 'bold'},
            style_data={'backgroundColor': 'white', 'color': '#1a202c'},
        )

    locked_pos = pos_breakdown(lp_df)
    bubble_pos = pos_breakdown(bp_df)

    # Bracket view
    def conference_block(name, teams):
        seed_items = []
        for idx, t in enumerate(teams[:7], start=1):
            seed_items.append(html.Li(f"{idx}. {t.get('name')} ({t.get('wins')}-{t.get('losses')}-{t.get('ties')})"))
        return dbc.Col([
            html.H6(name),
            html.Ul(seed_items)
        ], md=6)

    bracket_children = dbc.Row([
        conference_block("AFC Seeds", conferences.get('AFC', [])),
        conference_block("NFC Seeds", conferences.get('NFC', []))
    ])

    # Note overrides applied
    overrides_note = dbc.Alert(
        "Scenario overrides applied: KC removed; AFC spot = Ravens/Steelers; NFC spot = Panthers/Bucs.",
        color="info",
        className="mt-2"
    )

    # Outcomes (simplified): list bubble teams with note
    outcome_items = []
    for conf_name, teams in conferences.items():
        for t in teams[7:]:
            tid = str(t.get('id'))
            if tid in bubble_ids:
                outcome_items.append(html.Li(f"{conf_name}: {t.get('name')} — Can still clinch; watch Week 17 MNF and Week 18 results."))

    outcomes_children = html.Ul(outcome_items) if outcome_items else dbc.Alert("No bubble teams detected.", color="light")

    bracket_with_note = html.Div([bracket_children, overrides_note])
    return lp_table, bp_table, bracket_with_note, outcomes_children, locked_pos, bubble_pos

def render_live_tab():
    """Live NFL scoreboard and in-progress correctness for weekly picks."""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")

        df = pd.read_sql_query("SELECT DISTINCT week FROM picks ORDER BY week", conn)
        conn.close()
        weeks = sorted(df['week'].unique()) if not df.empty else list(range(1, 19))

        return [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Select Week for Live View"),
                        dbc.CardBody([
                            dcc.Dropdown(id="live-week", options=[{"label": f"Week {w}", "value": w} for w in weeks], value=weeks[-1] if weeks else 1),
                            dbc.Button("Refresh", id="live-refresh", color="secondary", className="mt-2"),
                            dcc.Interval(id="live-interval", interval=60_000, n_intervals=0)
                        ])
                    ])
                ], width=12, md=4)
            ], className="mb-3"),

            html.Div(id="live-content")
        ]
    except Exception as e:
        return dbc.Alert(f"Error rendering live tab: {str(e)}", color="danger")


@app.callback(
    Output("live-content", "children"),
    Input("live-week", "value"),
    Input("live-refresh", "n_clicks"),
    Input("live-interval", "n_intervals")
)
def update_live_content(week, _refresh_clicks, _tick):
    if not week:
        return dbc.Alert("Select a week.", color="info")
    try:
        live = fetch_live_scores_for_week(int(week))
        if not live or not live.get('games'):
            return dbc.Alert("No live data right now for this week.", color="light")

        # Summary table per player: currently correct on in-progress games
        summary_df = pd.DataFrame(live['summary']) if live.get('summary') else pd.DataFrame()
        summary_table = dash_table.DataTable(
            data=summary_df.to_dict('records'),
            columns=[{"name": k, "id": k} for k in summary_df.columns] if not summary_df.empty else [],
            style_cell={'textAlign': 'center', 'padding': '10px'},
            style_header={'backgroundColor': '#0d6efd', 'color': 'white', 'fontWeight': 'bold'},
            style_data={'backgroundColor': 'white', 'color': '#1a202c'},
        ) if not summary_df.empty else dbc.Alert("No in-progress games to summarize.", color="light")

        # Game cards with current scores and who is right/wrong so far
        people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
        cards = []
        for g in live['games']:
            picks_rows = []
            for person in people:
                pick = g['picks'].get(person)
                if not pick:
                    display = html.Span("No pick", style={'color': '#6c757d'})
                else:
                    correct_now = (g['leader'] == pick)
                    display = html.Span(
                        pick,
                        style={'color': '#155724', 'fontWeight': 'bold'} if correct_now else {'color': '#721c24', 'fontWeight': 'bold'}
                    )
                picks_rows.append(html.Div([html.Strong(person.title()+": "), display]))

            cards.append(
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Strong(f"{g['away']} @ {g['home']}")
                        ], className="mb-2"),
                        html.Div(f"Status: {g['status']}"),
                        html.Div(f"Score: {g['away_score']} - {g['home_score']}", className="mb-2"),
                        html.Div(picks_rows, style={'display': 'grid', 'gridTemplateColumns': 'repeat(3, 1fr)', 'gap': '6px'})
                    ])
                ], className="mb-3")
            )

        return [
            dbc.Card([
                dbc.CardHeader("Live Summary"),
                dbc.CardBody([summary_table])
            ], className="mb-3"),
            dbc.Card([
                dbc.CardHeader("Game-by-Game Live View"),
                dbc.CardBody(cards)
            ])
        ]
    except Exception as e:
        return dbc.Alert(f"Error fetching live data: {str(e)}", color="danger")


def fetch_live_scores_for_week(week: int):
    """Scrape ESPN scoreboard for given week and map to picks for 'currently winning'."""
    try:
        current_year = Config.CURRENT_SEASON
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week={week}&dates={current_year}"
        import requests
        resp = requests.get(url, timeout=Config.ESPN_API_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        games = []

        # Read picks for week
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM picks WHERE week = ?", conn, params=(week,))
        conn.close()

        # Helper to find pick record matching teams
        def find_pick_record(away_name, home_name):
            if df.empty:
                return None
            for _, r in df.iterrows():
                if str(r['away_team']).strip() == away_name and str(r['home_team']).strip() == home_name:
                    return r
            # Fallback: try cleaned names
            away_clean = clean_team_name(away_name)
            home_clean = clean_team_name(home_name)
            for _, r in df.iterrows():
                if clean_team_name(str(r['away_team']).strip()) == away_clean and clean_team_name(str(r['home_team']).strip()) == home_clean:
                    return r
            return None

        if 'events' in data:
            for ev in data['events']:
                comp = ev.get('competitions', [{}])[0]
                teams = comp.get('competitors', [])
                status = comp.get('status', {}).get('type', {})
                game_state = status.get('name')  # e.g., STATUS_IN_PROGRESS, STATUS_FINAL, STATUS_SCHEDULED
                short_detail = comp.get('status', {}).get('type', {}).get('shortDetail', '')
                if len(teams) != 2:
                    continue
                team_a = teams[0]
                team_b = teams[1]
                # ESPN flags 'homeAway'
                away_obj = next(t for t in teams if t.get('homeAway') == 'away')
                home_obj = next(t for t in teams if t.get('homeAway') == 'home')
                away_name = clean_team_name(away_obj.get('team', {}).get('displayName', ''))
                home_name = clean_team_name(home_obj.get('team', {}).get('displayName', ''))
                away_score = int(float(away_obj.get('score', 0) or 0))
                home_score = int(float(home_obj.get('score', 0) or 0))

                # Only show live/in-progress or scheduled (pre-kick) games
                if game_state not in ("STATUS_IN_PROGRESS", "STATUS_SCHEDULED"):
                    continue

                # Map to picks
                rec = find_pick_record(away_name, home_name)
                picks = {}
                leader = None
                if away_score != home_score:
                    leader = away_name if away_score > home_score else home_name
                if rec is not None:
                    for person in ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']:
                        val = rec.get(f'{person}_pick') if isinstance(rec, pd.Series) else rec[f'{person}_pick']
                        # Normalize stored X picks (team names already stored by importer)
                        picks[person] = val if pd.notna(val) else None

                games.append({
                    'away': away_name,
                    'home': home_name,
                    'away_score': away_score,
                    'home_score': home_score,
                    'status': short_detail or game_state,
                    'leader': leader,
                    'picks': picks
                })

        # Build summary counts per person for in-progress games
        summary = []
        for person in ['Bobby', 'Chet', 'Clyde', 'Henry', 'Nick', 'Riley']:
            pkey = person.lower()
            correct = 0
            wrong = 0
            for g in games:
                pick = g['picks'].get(pkey)
                if not pick or not g['leader']:
                    continue
                if pick == g['leader']:
                    correct += 1
                else:
                    wrong += 1
            summary.append({'Player': person, 'Right Now': correct, 'Wrong Now': wrong})

        return {'games': games, 'summary': summary}
    except Exception:
        return None
def render_weekly_records_tab():
    try:
        weekly_df = get_weekly_records_data()
        weekly_winners = get_weekly_winners()
        # Determine latest week clinch status for header badge
        header_badge = None
        try:
            conn = get_db_connection()
            if conn:
                df_all = pd.read_sql_query("SELECT * FROM picks", conn)
                conn.close()
                if not df_all.empty:
                    latest_week = int(df_all['week'].max())
                    clinched = is_week_clinched(df_all, latest_week, ['bobby','chet','clyde','henry','nick','riley'])
                    header_badge = html.Span(
                        "🔒 Latest Week Clinched" if clinched else "⏳ Latest Week In Play",
                        style={'marginLeft': '10px', 'fontWeight': '700', 'color': '#212529'}
                    )
        except Exception:
            header_badge = None
        
        if weekly_df.empty:
            return dbc.Alert("No completed games available for weekly records.", color="info")
        
        # Create a chart showing weekly performance trends
        weekly_chart = create_weekly_trends_chart()
        
        # Live tiebreaker guesses for the latest week (if applicable)
        live_tb_card = build_live_tiebreaker_card()

        return [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4("Weekly Winners", className="mb-0"),
                            html.Small("Tie = closest total points in last game", className="text-muted"),
                            header_badge if header_badge else html.Span()
                        ]),
                        dbc.CardBody([
                            dash_table.DataTable(
                                data=weekly_winners,
                                columns=[
                                    {"name": "Week", "id": "Week"},
                                    {"name": "Winner", "id": "Winner"},
                                    {"name": "Record", "id": "Record"},
                                    {"name": "Tiebreaker", "id": "Tiebreaker"},
                                    {"name": "Status", "id": "Status"}
                                ],
                                style_cell={
                                    'textAlign': 'center',
                                    'padding': '10px',
                                    'fontFamily': 'Arial, sans-serif',
                                    'fontSize': '13px',
                                    'whiteSpace': 'normal',
                                    'height': 'auto'
                                },
                                style_header={
                                    'backgroundColor': '#ffc107',
                                    'color': '#212529',
                                    'fontWeight': 'bold'
                                },
                                style_data={'backgroundColor': 'white', 'color': '#1a202c'},
                                style_data_conditional=[
                                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#fdf6e3', 'color': '#1a202c'}
                                ],
                                style_table={'overflowX': 'auto'},
                                page_size=30
                            ) if weekly_winners else dbc.Alert("No weekly winners yet. Complete games first.", color="light")
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([live_tb_card], width=12)
            ], className="mb-4"),
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
                            html.H4("Weekly Records", className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Alert([
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
                                style_data={'backgroundColor': 'white', 'color': '#1a202c'},
                                style_data_conditional=[
                                    {
                                        'if': {'row_index': 'odd'},
                                        'backgroundColor': '#f8f9fa',
                                        'color': '#1a202c'
                                    },
                                    {
                                        'if': {
                                            'filter_query': '{Week} = TOTALS',
                                            'column_id': 'Week'
                                        },
                                        'backgroundColor': '#343a40',
                                        'color': 'white',
                                        'fontWeight': 'bold'
                                    },
                                    {
                                        'if': {
                                            'filter_query': '{Week} = TOTALS'
                                        },
                                        'backgroundColor': '#343a40',
                                        'color': 'white',
                                        'fontWeight': 'bold'
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

def build_live_tiebreaker_card():
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database unavailable for live tiebreaker.", color="warning")

        df_all = pd.read_sql_query("SELECT * FROM picks", conn)
        conn.close()
        if df_all.empty:
            return dbc.Alert("No data for live tiebreaker.", color="light")

        latest_week = int(df_all['week'].max())
        week_df = df_all[df_all['week'] == latest_week]
        completed = week_df[week_df['actual_winner'].notna()]

        people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
        record_map = {}
        for person in people:
            col = f"{person}_pick"
            picks = completed[completed[col].notna()]
            wins = 0
            for _, row in picks.iterrows():
                if row[col] == 'away':
                    pick_team = row['away_team']
                elif row[col] == 'home':
                    pick_team = row['home_team']
                else:
                    pick_team = row[col]
                if row['actual_winner'] == 'away':
                    actual = row['away_team']
                elif row['actual_winner'] == 'home':
                    actual = row['home_team']
                else:
                    actual = row['actual_winner']
                if pick_team == actual:
                    wins += 1
            record_map[person] = {'wins': wins}

        best_wins = max(v['wins'] for v in record_map.values()) if record_map else 0
        contenders = [p for p, rec in record_map.items() if rec['wins'] == best_wins]

        tb_row = week_df[week_df.get('is_tiebreaker_game', False) == 1]
        tb_row = tb_row.iloc[-1] if not tb_row.empty else None
        if tb_row is None:
            return dbc.Card([
                dbc.CardHeader("Current Week Tiebreaker Guesses (Live)"),
                dbc.CardBody([dbc.Alert("No tiebreaker game configured for latest week.", color="light")])
            ])

        game_matchup = f"{tb_row['away_team']} vs {tb_row['home_team']}"
        rows = []
        for person in contenders:
            raw = tb_row.get(f"{person}_tiebreaker")
            guess = "N/A"
            if pd.notna(raw):
                try:
                    guess = str(int(float(raw)))
                except Exception:
                    guess = str(raw)
            rows.append({'Player': person.title(), 'Guess': guess})

        table = dash_table.DataTable(
            data=rows,
            columns=[{"name": "Player", "id": "Player"}, {"name": "Guess", "id": "Guess"}],
            style_cell={'textAlign': 'center', 'padding': '10px'},
            style_header={'backgroundColor': '#6610f2', 'color': 'white', 'fontWeight': 'bold'},
            style_data={'backgroundColor': 'white', 'color': '#1a202c'},
        ) if rows else dbc.Alert("No contenders identified yet.", color="light")

        return dbc.Card([
            dbc.CardHeader([html.H5("Current Week Tiebreaker Guesses (Live)", className="mb-0"), html.Small(game_matchup, className="text-muted")]),
            dbc.CardBody([table])
        ])
    except Exception as e:
        return dbc.Alert(f"Live tiebreaker error: {e}", color="danger")

def get_weekly_records_data():
    """Get weekly records data with totals row"""
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
        totals = {'Week': 'TOTALS'}
        
        for week in weeks:
            week_df = df[df['week'] == week]
            week_record = {'Week': f"Week {week}"}
            
            for person in people:
                person_pick_col = f'{person}_pick'
                person_week_picks = week_df[week_df[person_pick_col].notna()]
                
                if len(person_week_picks) > 0:
                    wins = 0
                    for _, row in person_week_picks.iterrows():
                        # Handle pick comparison
                        if row[person_pick_col] == 'away':
                            person_team_pick = row['away_team']
                        elif row[person_pick_col] == 'home':
                            person_team_pick = row['home_team']
                        else:
                            person_team_pick = row[person_pick_col]
                        
                        # Handle actual winner
                        if row['actual_winner'] == 'away':
                            actual_team_winner = row['away_team']
                        elif row['actual_winner'] == 'home':
                            actual_team_winner = row['home_team']
                        else:
                            actual_team_winner = row['actual_winner']
                        
                        if person_team_pick == actual_team_winner:
                            wins += 1
                    
                    total = len(person_week_picks)
                    losses = total - wins
                    win_pct = (wins / total * 100) if total > 0 else 0
                    
                    week_record[person.title()] = f"{wins}-{losses} ({win_pct:.0f}%)"
                    
                    # Add to totals
                    if person.title() not in totals:
                        totals[person.title()] = {'wins': 0, 'total': 0}
                    totals[person.title()]['wins'] += wins
                    totals[person.title()]['total'] += total
                else:
                    week_record[person.title()] = "0-0 (0%)"
            
            weekly_records.append(week_record)
        
        # Calculate totals row
        for person in people:
            person_title = person.title()
            if person_title in totals and isinstance(totals[person_title], dict):
                total_wins = totals[person_title]['wins']
                total_games = totals[person_title]['total']
                total_losses = total_games - total_wins
                total_win_pct = (total_wins / total_games * 100) if total_games > 0 else 0
                totals[person_title] = f"{total_wins}-{total_losses} ({total_win_pct:.1f}%)"
            else:
                totals[person_title] = "0-0 (0%)"
        
        # Add totals row
        weekly_records.append(totals)
        
        return pd.DataFrame(weekly_records)
        

    except Exception as e:
        print(f"Error in get_weekly_records_data: {e}")
        return pd.DataFrame()


def get_weekly_winners():
    """Determine weekly winners using total points in the last game as tiebreaker."""
    try:
        conn = get_db_connection()
        if not conn:
            return []

        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()

        if df.empty:
            return []

        people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
        weeks = sorted(df['week'].unique())
        winners_rows = []

        for week in weeks:
            week_df = df[df['week'] == week]
            record_map = {}

            for person in people:
                person_col = f'{person}_pick'
                picks = week_df[week_df[person_col].notna()]
                wins = 0
                for _, row in picks.iterrows():
                    if row[person_col] == 'away':
                        pick_team = row['away_team']
                    elif row[person_col] == 'home':
                        pick_team = row['home_team']
                    else:
                        pick_team = row[person_col]

                    if row['actual_winner'] == 'away':
                        actual = row['away_team']
                    elif row['actual_winner'] == 'home':
                        actual = row['home_team']
                    else:
                        actual = row['actual_winner']

                    if pick_team == actual:
                        wins += 1

                total_games = len(picks)
                record_map[person] = {
                    'wins': wins,
                    'total': total_games,
                    'losses': total_games - wins
                }

            if not record_map:
                continue

            best_wins = max(p['wins'] for p in record_map.values())
            contenders = [p for p, rec in record_map.items() if rec['wins'] == best_wins]
            winners = contenders[:]
            tiebreaker_detail = "Tiebreaker not needed"

            if len(contenders) > 1:
                tb_game_df = week_df[week_df.get('is_tiebreaker_game', False) == 1]
                tb_row = tb_game_df.iloc[-1] if not tb_game_df.empty else None

                if tb_row is not None and pd.notna(tb_row.get('away_score')) and pd.notna(tb_row.get('home_score')):
                    actual_total = int(tb_row['away_score']) + int(tb_row['home_score'])
                    game_matchup = f"{tb_row['away_team']} vs {tb_row['home_team']}"
                    final_score = f"{int(tb_row['away_score'])}-{int(tb_row['home_score'])}"
                    
                    contender_errors = []
                    for person in contenders:
                        tb_val_raw = tb_row.get(f"{person}_tiebreaker")
                        tb_val = None
                        if pd.notna(tb_val_raw):
                            try:
                                tb_val = int(float(tb_val_raw))
                            except Exception:
                                tb_val = None

                        error = abs(tb_val - actual_total) if tb_val is not None else float('inf')
                        contender_errors.append({
                            'name': person,
                            'error': error,
                            'prediction': tb_val
                        })

                    best_error = min(c['error'] for c in contender_errors)
                    winners = [c['name'] for c in contender_errors if c['error'] == best_error]

                    detail_parts = []
                    for c in contender_errors:
                        pred_text = f"{int(c['prediction'])}" if c['prediction'] is not None else "N/A"
                        if c['error'] == float('inf'):
                            diff_text = "no pick"
                        else:
                            diff_text = f"off by {int(c['error'])}"
                        detail_parts.append(f"{c['name'].title()}: {pred_text} ({diff_text})")

                    tiebreaker_detail = f"🏈 {game_matchup} (Final: {final_score}, Total: {actual_total} pts) | " + "; ".join(detail_parts)
                else:
                    # If last-game score missing, still list contenders' guesses for transparency
                    if tb_row is not None:
                        game_matchup = f"{tb_row['away_team']} vs {tb_row['home_team']}"
                        detail_parts = []
                        for person in contenders:
                            tb_val_raw = tb_row.get(f"{person}_tiebreaker")
                            pred_text = "N/A"
                            if pd.notna(tb_val_raw):
                                try:
                                    pred_text = str(int(float(tb_val_raw)))
                                except Exception:
                                    pred_text = str(tb_val_raw)
                            detail_parts.append(f"{person.title()}: {pred_text}")
                        tiebreaker_detail = f"🏈 {game_matchup} (Final: TBD) | Contenders' guesses: " + ", ".join(detail_parts)
                    else:
                        tiebreaker_detail = "Tiebreaker unavailable (missing last-game setup)."

            # Determine lock status (clinched) for the week based on remaining games and pick differences
            clinched = is_week_clinched(df, week, people)

            winner_names = ", ".join([w.title() for w in winners]) if winners else "-"
            primary_winner = winners[0] if winners else contenders[0]
            rec = record_map.get(primary_winner, {'wins': 0, 'losses': 0})
            record_text = f"{rec['wins']}-{rec['losses']}"

            winners_rows.append({
                'Week': f"Week {week}",
                'Winner': winner_names,
                'Record': record_text,
                'Tiebreaker': tiebreaker_detail,
                'Status': '🔒 Clinched' if clinched else '⏳ In Play'
            })

        return winners_rows

    except Exception as e:
        print(f"Error computing weekly winners: {e}")
        return []

def is_week_clinched(df_all, week, people):
    """Approximate clinch detection: if no trailing player can catch the leader given remaining differing picks.
    - Compute wins so far for each player.
    - Identify current unique leader; if tie at top, not clinched.
    - Count remaining games and for each trailing player, count games where their pick differs from leader's.
    - If trailing player's wins + differing_remaining < leader_wins, they cannot catch; if true for all, clinched.
    """
    try:
        week_df = df_all[df_all['week'] == week]
        completed = week_df[week_df['actual_winner'].notna()]
        remaining = week_df[week_df['actual_winner'].isna()]

        # wins so far
        wins_map = {}
        for person in people:
            col = f"{person}_pick"
            wins = 0
            for _, row in completed.iterrows():
                pick_team = row['away_team'] if row[col] == 'away' else (row['home_team'] if row[col] == 'home' else row[col])
                actual = row['away_team'] if row['actual_winner'] == 'away' else (row['home_team'] if row['actual_winner'] == 'home' else row['actual_winner'])
                if pick_team == actual:
                    wins += 1
            wins_map[person] = wins

        if not wins_map:
            return False

        # current leader(s)
        max_wins = max(wins_map.values())
        leaders = [p for p, w in wins_map.items() if w == max_wins]
        if len(leaders) != 1:
            return False  # tie at top, not clinched
        leader = leaders[0]

        # For each trailing player, can they catch or pass?
        leader_wins = wins_map[leader]
        for person in people:
            if person == leader:
                continue
            person_wins = wins_map[person]
            deficit = leader_wins - person_wins
            if deficit <= 0:
                return False
            # Count remaining games with differing picks
            diff_count = 0
            lcol = f"{leader}_pick"
            pcol = f"{person}_pick"
            for _, row in remaining.iterrows():
                lpick = row['away_team'] if row[lcol] == 'away' else (row['home_team'] if row[lcol] == 'home' else row[lcol])
                ppick = row['away_team'] if row[pcol] == 'away' else (row['home_team'] if row[pcol] == 'home' else row[pcol])
                if lpick != ppick:
                    diff_count += 1
            # If even sweeping all differing games can't erase deficit, person cannot catch
            if person_wins + diff_count >= leader_wins:
                return False
        return True
    except Exception:
        return False


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
                    wins = 0
                    for _, row in person_week_picks.iterrows():
                        # Handle pick comparison
                        if row[person_pick_col] == 'away':
                            person_team_pick = row['away_team']
                        elif row[person_pick_col] == 'home':
                            person_team_pick = row['home_team']
                        else:
                            person_team_pick = row[person_pick_col]
                        
                        # Handle actual winner
                        if row['actual_winner'] == 'away':
                            actual_team_winner = row['away_team']
                        elif row['actual_winner'] == 'home':
                            actual_team_winner = row['home_team']
                        else:
                            actual_team_winner = row['actual_winner']
                        
                        if person_team_pick == actual_team_winner:
                            wins += 1
                    
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

# Statistics Dashboard Tab
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
        player_insights = calculate_player_insights(df)
        tiebreaker_stats = calculate_tiebreaker_accuracy(df)
        
        return html.Div([
            # Current Streaks Section
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([html.I(className="fas fa-fire me-2", style={'color': '#D50A0A'}), "Current Streaks"], className="mb-0")
                        ]),
                        dbc.CardBody([
                            create_streaks_display(streak_data)
                        ])
                    ], className="content-card")
                ], width=12)
            ], className="mb-4"),
            
            # Best/Worst Weeks
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([html.I(className="fas fa-chart-line me-2", style={'color': '#013369'}), "Best & Worst Week Performances"], className="mb-0")
                        ]),
                        dbc.CardBody([
                            create_best_worst_weeks_display(best_worst_weeks)
                        ])
                    ], className="content-card")
                ], width=12)
            ], className="mb-4"),

            # Player insights & tiebreaker accuracy & head-to-head
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([html.I(className="fas fa-user-chart me-2"), "Player Insights"], className="mb-0"),
                            html.Small("Most picked teams and strengths", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dash_table.DataTable(
                                data=player_insights,
                                columns=[
                                    {"name": "Player", "id": "Player"},
                                    {"name": "Picks", "id": "Picks"},
                                    {"name": "Win %", "id": "Win %"},
                                    {"name": "Most Picked", "id": "Most Picked"},
                                    {"name": "Best Team", "id": "Best Team"},
                                    {"name": "Worst Team", "id": "Worst Team"},
                                    {"name": "Home/Away", "id": "Home/Away"}
                                ],
                                style_cell={'textAlign': 'center', 'padding': '10px', 'fontSize': '13px'},
                                style_header={'backgroundColor': '#0d6efd', 'color': 'white', 'fontWeight': 'bold'},
                                style_data={'backgroundColor': 'white', 'color': '#1a202c'},
                                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa', 'color': '#1a202c'}],
                                style_table={'overflowX': 'auto'}
                            )
                        ])
                    ], className="content-card")
                ], width=12, lg=6),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([html.I(className="fas fa-bullseye me-2"), "Tiebreaker Accuracy"], className="mb-0"),
                            html.Small("Lower error is better", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dash_table.DataTable(
                                data=tiebreaker_stats,
                                columns=[
                                    {"name": "Rank", "id": "Rank"},
                                    {"name": "Player", "id": "Player"},
                                    {"name": "Attempts", "id": "Attempts"},
                                    {"name": "Avg Error", "id": "Avg Error"},
                                    {"name": "Best", "id": "Best"},
                                    {"name": "Worst", "id": "Worst"}
                                ],
                                style_cell={'textAlign': 'center', 'padding': '10px', 'fontSize': '13px'},
                                style_header={'backgroundColor': '#6610f2', 'color': 'white', 'fontWeight': 'bold'},
                                style_data={'backgroundColor': 'white', 'color': '#1a202c'},
                                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa', 'color': '#1a202c'}],
                                style_table={'overflowX': 'auto'}
                            )
                        ])
                    ], className="content-card")
                ], width=12, lg=6)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([html.I(className="fas fa-users me-2"), "Head-to-Head Records"], className="mb-0"),
                            html.Small("Shows who makes better picks when players disagree", className="text-muted")
                        ]),
                        dbc.CardBody([
                            dbc.Alert([
                                html.Strong("Explanation: "),
                                "When two players pick different teams for the same game, whoever picked the winning team gets a head-to-head win. This measures individual game decision-making skill."
                            ], color="info", className="mb-3"),
                            create_head_to_head_display(head_to_head)
                        ])
                    ], className="content-card")
                ], width=12)
            ])
        ])
        
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
            # Handle pick comparison
            if row[person_pick_col] == 'away':
                person_team_pick = row['away_team']
            elif row[person_pick_col] == 'home':
                person_team_pick = row['home_team']
            else:
                person_team_pick = row[person_pick_col]
            
            # Handle actual winner
            if row['actual_winner'] == 'away':
                actual_team_winner = row['away_team']
            elif row['actual_winner'] == 'home':
                actual_team_winner = row['home_team']
            else:
                actual_team_winner = row['actual_winner']
            
            correct = person_team_pick == actual_team_winner
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
            {"name": "Current Streak", "id": "Current Streak"},
            {"name": "Best Win Streak", "id": "Longest Win Streak"},
            {"name": "Worst Loss Streak", "id": "Longest Loss Streak"}
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
        style_data={'backgroundColor': 'white', 'color': '#1a202c'},
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
                wins = 0
                for _, row in person_week_picks.iterrows():
                    # Handle pick comparison
                    if row[person_pick_col] == 'away':
                        person_team_pick = row['away_team']
                    elif row[person_pick_col] == 'home':
                        person_team_pick = row['home_team']
                    else:
                        person_team_pick = row[person_pick_col]
                    
                    # Handle actual winner
                    if row['actual_winner'] == 'away':
                        actual_team_winner = row['away_team']
                    elif row['actual_winner'] == 'home':
                        actual_team_winner = row['home_team']
                    else:
                        actual_team_winner = row['actual_winner']
                    
                    if person_team_pick == actual_team_winner:
                        wins += 1
                
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
            {"name": "Best Week", "id": "Best Week"},
            {"name": "Worst Week", "id": "Worst Week"}
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
        style_data={'backgroundColor': 'white', 'color': '#1a202c'},
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa',
                'color': '#1a202c'
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
            # Handle person's pick
            if row[person_pick_col] == 'away':
                person_team_pick = row['away_team']
            elif row[person_pick_col] == 'home':
                person_team_pick = row['home_team']
            else:
                person_team_pick = row[person_pick_col]
            
            # Handle actual winner
            if row['actual_winner'] == 'away':
                actual_team_winner = row['away_team']
            elif row['actual_winner'] == 'home':
                actual_team_winner = row['home_team']
            else:
                actual_team_winner = row['actual_winner']
            
            person_correct = person_team_pick == actual_team_winner
            
            # Compare against each other player for this game
            for other_person in people:
                if other_person != person:
                    other_pick_col = f'{other_person}_pick'
                    if pd.notna(row[other_pick_col]):
                        # Handle other person's pick
                        if row[other_pick_col] == 'away':
                            other_team_pick = row['away_team']
                        elif row[other_pick_col] == 'home':
                            other_team_pick = row['home_team']
                        else:
                            other_team_pick = row[other_pick_col]
                        
                        other_correct = other_team_pick == actual_team_winner
                        
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


def calculate_player_insights(df):
    """Create per-player insight rows: volume, accuracy, best/worst team, pick bias."""
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    insights = []
    for person in people:
        col = f'{person}_pick'
        picks = df[df[col].notna()].copy()
        completed = picks[picks['actual_winner'].notna()]
        if completed.empty:
            continue
        total = len(completed)
        wins = (completed[col] == completed['actual_winner']).sum()
        win_pct = (wins / total * 100) if total else 0

        # Most picked team
        most_picked = picks[col].value_counts().idxmax() if not picks.empty else '-'

        # Team performance
        team_perf = completed.groupby(col)['actual_winner'].apply(
            lambda s: (s.index, (s == s.index.to_series().map(completed.loc[s.index, col])).sum())
        ) if False else None  # placeholder to keep structure minimal
        team_stats = completed.groupby(col).apply(
            lambda g: {
                'wins': (g[col] == g['actual_winner']).sum(),
                'total': len(g)
            }
        )
        def best_or_worst(selector):
            if team_stats.empty:
                return "-"
            key = selector(team_stats.items(), key=lambda kv: (kv[1]['wins']/kv[1]['total'], kv[1]['wins']))
            pct = (key[1]['wins'] / key[1]['total'] * 100) if key[1]['total'] else 0
            return f"{key[0]} ({key[1]['wins']}-{key[1]['total']-key[1]['wins']} | {pct:.0f}%)"
        best_team = best_or_worst(max)
        worst_team = best_or_worst(min)

        home_picks = ((picks[col] == picks['home_team']).sum()) if 'home_team' in picks else 0
        away_picks = ((picks[col] == picks['away_team']).sum()) if 'away_team' in picks else 0

        insights.append({
            'Player': person.title(),
            'Picks': total,
            'Win %': f"{win_pct:.1f}%",
            'Most Picked': most_picked,
            'Best Team': best_team,
            'Worst Team': worst_team,
            'Home/Away': f"{home_picks}/{away_picks}"
        })
    return insights


def calculate_tiebreaker_accuracy(df):
    """Compute tiebreaker accuracy using stored predictions vs total points scored."""
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    rows = []
    for person in people:
        col = f'{person}_tiebreaker'
        if col not in df.columns:
            continue
        tb_df = df[(df[col].notna()) & df['away_score'].notna() & df['home_score'].notna()].copy()
        if tb_df.empty:
            continue
        tb_df['actual_total'] = tb_df['away_score'] + tb_df['home_score']
        tb_df['error'] = (tb_df[col] - tb_df['actual_total']).abs()
        avg_err = tb_df['error'].mean()
        best = tb_df['error'].min()
        worst = tb_df['error'].max()
        rows.append({
            'Player': person.title(),
            'Attempts': len(tb_df),
            'Avg Error': f"{avg_err:.1f}",
            'Best': f"{best:.0f}",
            'Worst': f"{worst:.0f}"
        })
    rows.sort(key=lambda r: float(r['Avg Error']))
    for i, row in enumerate(rows):
        row['Rank'] = i + 1
    return rows

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
        style_data={'backgroundColor': 'white', 'color': '#1a202c'},
        style_data_conditional=[
            {
                'if': {'row_index': 0},
                'backgroundColor': '#d4edda',
                'color': '#155724',
                'fontWeight': 'bold'
            },
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa',
                'color': '#1a202c'
            }
        ],
        style_table={'overflowX': 'auto'}
    )

def render_grid_tab():
    """Show all weeks in a grid format with color-coded picks"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")

        df = pd.read_sql_query("SELECT * FROM picks ORDER BY week, game_id", conn)
        conn.close()

        if df.empty:
            return dbc.Alert("No picks data available.", color="info")

        weeks = sorted(df['week'].unique())
        
        # Create tabs for each week
        week_tabs = []
        for week in weeks:
            week_df = df[df['week'] == week]
            week_content = create_grid_week_content(week_df, week)
            
            week_tabs.append(
                dbc.Tab(label=f"Week {week}", tab_id=f"grid-week-{week}", children=[
                    html.Div(week_content, className="mt-3")
                ])
            )
        
        return dbc.Card([
            dbc.CardHeader("Weekly Picks & Results"),
            dbc.CardBody([
                dbc.Alert([
                    html.Strong("Tiebreaker: "),
                    "Numbers in parentheses show each person's total points prediction for the tiebreaker game. Green = correct pick, Red = incorrect pick."
                ], color="info", className="mb-3"),
                dbc.Tabs(week_tabs, id="grid-week-tabs", active_tab=f"grid-week-{weeks[0]}" if weeks else None)
            ])
        ])

    except Exception as e:
        return dbc.Alert(f"Error loading grid: {str(e)}", color="danger")


def create_grid_week_content(week_df, week_num):
    """Create grid content for a specific week"""
    if week_df.empty:
        return html.P(f"No data for Week {week_num}")
    
    people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
    display_data = []
    
    for _, row in week_df.iterrows():
        # Get team logos for display
        away_logo = get_team_logo_url(row['away_team'])
        home_logo = get_team_logo_url(row['home_team'])
        
        game_row = {
            'Matchup': html.Div([
                html.Div([
                    html.Img(src=away_logo, style={'height': '25px', 'marginRight': '5px'}) if away_logo else "",
                    html.Span(row['away_team'], style={'fontWeight': '600'}),
                    html.Span(" @ ", style={'margin': '0 5px', 'color': '#6c757d'}),
                    html.Img(src=home_logo, style={'height': '25px', 'marginRight': '5px'}) if home_logo else "",
                    html.Span(row['home_team'], style={'fontWeight': '600'})
                ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
            ])
        }
        
        for person in people:
            person_pick_col = f'{person}_pick'
            pick = row[person_pick_col]
            
            # Check if this is a tiebreaker game for displaying prediction
            tiebreaker_text = ""
            if row.get('is_tiebreaker_game', False):
                tiebreaker_col = f'{person}_tiebreaker'
                if pd.notna(row.get(tiebreaker_col)):
                    tiebreaker_text = f" ({int(row[tiebreaker_col])})"
            
            if pd.notna(pick):
                pick_logo = get_team_logo_url(pick)
                if pd.notna(row['actual_winner']):
                    is_correct = pick == row['actual_winner']
                    if is_correct:
                        game_row[person.title()] = html.Div([
                            html.Img(src=pick_logo, style={'height': '20px', 'marginRight': '5px'}) if pick_logo else "",
                            html.Span(f"✓ {pick}{tiebreaker_text}", style={'color': '#28a745', 'fontWeight': '600'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
                    else:
                        game_row[person.title()] = html.Div([
                            html.Img(src=pick_logo, style={'height': '20px', 'marginRight': '5px'}) if pick_logo else "",
                            html.Span(f"✗ {pick}{tiebreaker_text}", style={'color': '#dc3545', 'fontWeight': '600'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
                else:
                    game_row[person.title()] = html.Div([
                        html.Img(src=pick_logo, style={'height': '20px', 'marginRight': '5px'}) if pick_logo else "",
                        html.Span(f"{pick}{tiebreaker_text}")
                    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
            else:
                game_row[person.title()] = '-'
        
        if pd.notna(row['actual_winner']):
            game_row['🏆 Winner'] = row['actual_winner']
        else:
            game_row['🏆 Winner'] = 'TBD'
        
        display_data.append(game_row)
    
    # Return as HTML table since we have complex content with logos
    return html.Div([
        html.Table([
            html.Thead(
                html.Tr([
                    html.Th('Matchup', style={'padding': '12px', 'backgroundColor': '#17a2b8', 'color': 'white', 'border': '1px solid #138496'}),
                    *[html.Th(person.title(), style={'padding': '12px', 'backgroundColor': '#17a2b8', 'color': 'white', 'border': '1px solid #138496'}) for person in people],
                    html.Th('🏆 Winner', style={'padding': '12px', 'backgroundColor': '#17a2b8', 'color': 'white', 'border': '1px solid #138496'})
                ])
            ),
            html.Tbody([
                html.Tr([
                    html.Td(row.get('Matchup', ''), style={'padding': '10px', 'border': '1px solid #dee2e6', 'backgroundColor': '#f8f9fa' if i % 2 else 'white', 'color': '#1a202c'}),
                    *[html.Td(row.get(person.title(), '-'), style={'padding': '10px', 'border': '1px solid #dee2e6', 'backgroundColor': '#f8f9fa' if i % 2 else 'white', 'color': '#1a202c'}) for person in people],
                    html.Td(row.get('🏆 Winner', 'TBD'), style={'padding': '10px', 'border': '1px solid #dee2e6', 'fontWeight': 'bold', 'backgroundColor': '#f8f9fa' if i % 2 else 'white', 'color': '#1a202c'})
                ]) for i, row in enumerate(display_data)
            ])
        ], style={'width': '100%', 'borderCollapse': 'collapse', 'fontSize': '13px', 'fontFamily': 'Arial, sans-serif'})
    ])


def create_grid_week_content_old(week_df, week_num):
    """Old table-based grid (kept for reference)"""
    picks_df = pd.DataFrame([])
    
    return dash_table.DataTable(
        data=picks_df.to_dict('records'),
        columns=[{"name": col, "id": col} for col in picks_df.columns],
        style_cell={
            'textAlign': 'center',
            'padding': '10px',
            'fontSize': '12px',
            'fontFamily': 'Arial, sans-serif',
            'whiteSpace': 'normal',
            'height': 'auto'
        },
        style_header={
            'backgroundColor': '#17a2b8',
            'color': 'white',
            'fontWeight': 'bold',
            'border': '1px solid white'
        },
        style_data={'backgroundColor': 'white', 'color': '#1a202c'},
        style_data_conditional=style_conditions,
        style_table={'overflowX': 'auto'}
    )
    

def render_teams_tab():
    """Show team-by-team breakdown of each person's picks"""
    try:
        conn = get_db_connection()
        if not conn:
            return dbc.Alert("Database temporarily unavailable.", color="warning")

        df = pd.read_sql_query("SELECT * FROM picks WHERE actual_winner IS NOT NULL", conn)
        conn.close()

        if df.empty:
            return dbc.Alert("No completed games available for team breakdown.", color="info")

        # Get all unique teams
        all_teams = set()
        for _, row in df.iterrows():
            if pd.notna(row['away_team']):
                all_teams.add(row['away_team'])
            if pd.notna(row['home_team']):
                all_teams.add(row['home_team'])
        
        all_teams = sorted(list(all_teams))
        people = ['bobby', 'chet', 'clyde', 'henry', 'nick', 'riley']
        
        # Build enhanced team breakdown data with more stats
        team_breakdown = []
        
        for team in all_teams:
            team_logo = get_team_logo_url(team)
            
            # Calculate team's overall record
            team_games = df[(df['away_team'] == team) | (df['home_team'] == team)]
            team_wins = len(team_games[team_games['actual_winner'] == team])
            team_total = len(team_games)
            team_record = f"{team_wins}-{team_total - team_wins}"
            
            team_row = {
                'Team': html.Div([
                    html.Img(src=team_logo, style={'height': '30px', 'marginRight': '8px', 'verticalAlign': 'middle'}) if team_logo else "",
                    html.Span(team, style={'fontWeight': '600', 'verticalAlign': 'middle'})
                ], style={'display': 'inline-flex', 'alignItems': 'center'}),
                'Record': team_record,
                'Win %': f"{(team_wins/team_total*100) if team_total > 0 else 0:.1f}%"
            }
            
            for person in people:
                person_pick_col = f'{person}_pick'
                
                # Get all games where this person picked this team
                team_picks = df[df[person_pick_col] == team]
                
                if len(team_picks) == 0:
                    team_row[person.title()] = "-"
                    continue
                
                wins = 0
                total = len(team_picks)
                
                for _, row in team_picks.iterrows():
                    if row['actual_winner'] == team:
                        wins += 1
                
                losses = total - wins
                win_pct = (wins / total * 100) if total > 0 else 0
                
                # Color code based on performance
                if win_pct >= 70:
                    color_style = {'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': '600', 'padding': '5px', 'borderRadius': '4px'}
                elif win_pct >= 50:
                    color_style = {'backgroundColor': '#fff3cd', 'color': '#856404', 'fontWeight': '600', 'padding': '5px', 'borderRadius': '4px'}
                elif total > 0:
                    color_style = {'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': '600', 'padding': '5px', 'borderRadius': '4px'}
                else:
                    color_style = {}
                
                team_row[person.title()] = html.Div(f"{wins}-{losses} ({win_pct:.0f}%)", style=color_style)
            
            team_breakdown.append(team_row)
        
        picks_df = pd.DataFrame(team_breakdown)
        
        # Create HTML table with logos and color coding
        content = []
        content.append(html.Div([
            html.H3([html.I(className="fas fa-chart-bar me-3", style={'color': '#D50A0A'}), "Team Performance Breakdown"], 
                   style={'color': '#013369', 'fontWeight': '700', 'marginBottom': '20px'})
        ], className="content-card"))
        
        content.append(html.Div([
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                html.Strong("Analysis: "),
                "Each person's win-loss record when picking specific teams. ",
                html.Strong("Green"), " = 70%+ success, ",
                html.Strong("Yellow", style={'color': '#856404'}), " = 50-69%, ",
                html.Strong("Red", style={'color': '#721c24'}), " = below 50%. Team's overall record shown for reference."
            ], color="info", className="mb-3"),
            
            html.Table([
                html.Thead(
                    html.Tr([
                        html.Th('Team', style={'padding': '12px', 'backgroundColor': '#17a2b8', 'color': 'white', 'border': '1px solid #138496', 'textAlign': 'left'}),
                        html.Th('Record', style={'padding': '12px', 'backgroundColor': '#17a2b8', 'color': 'white', 'border': '1px solid #138496'}),
                        html.Th('Win %', style={'padding': '12px', 'backgroundColor': '#17a2b8', 'color': 'white', 'border': '1px solid #138496'}),
                        *[html.Th(person.title(), style={'padding': '12px', 'backgroundColor': '#17a2b8', 'color': 'white', 'border': '1px solid #138496'}) for person in people]
                    ])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(row.get('Team', ''), style={'padding': '10px', 'border': '1px solid #dee2e6', 'backgroundColor': '#f8f9fa' if i % 2 else 'white', 'textAlign': 'left', 'color': '#1a202c'}),
                        html.Td(row.get('Record', ''), style={'padding': '10px', 'border': '1px solid #dee2e6', 'backgroundColor': '#f8f9fa' if i % 2 else 'white', 'textAlign': 'center', 'fontWeight': '600', 'color': '#1a202c'}),
                        html.Td(row.get('Win %', ''), style={'padding': '10px', 'border': '1px solid #dee2e6', 'backgroundColor': '#f8f9fa' if i % 2 else 'white', 'textAlign': 'center', 'fontWeight': '600', 'color': '#1a202c'}),
                        *[html.Td(row.get(person.title(), '-'), style={'padding': '10px', 'border': '1px solid #dee2e6', 'backgroundColor': '#f8f9fa' if i % 2 else 'white', 'textAlign': 'center', 'color': '#1a202c'}) for person in people]
                    ]) for i, row in enumerate(team_breakdown)
                ])
            ], style={'width': '100%', 'borderCollapse': 'collapse', 'fontSize': '13px', 'fontFamily': 'Arial, sans-serif'})
        ], className="content-card"))
        
        return content

    except Exception as e:
        return dbc.Alert(f"Error loading team breakdown: {str(e)}", color="danger")


@app.callback(
    Output('last-updated-display', 'children'),
    Input('last-updated-display', 'id')
)
def display_last_updated(_):
    return f"Last Updated: {get_last_updated()}"


init_database()

# Server setup
server = app.server

# Mount postseason fantasy Dash app at /postseason
server.wsgi_app = DispatcherMiddleware(server.wsgi_app, {
    "/postseason": postseason_app.server
})

# Auto-load picks on startup - runs regardless of how the app starts
auto_load_picks_on_startup()

if __name__ == '__main__':
    logger.info(f"Starting NFL Picks Tracker on {Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG_MODE)
