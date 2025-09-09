import pandas as pd
import os

directory = r'C:\fantasy python\fantasy excel docs'

def calculate_fantasy_points(row, is_ppr=True):
    points = 0.0
    # Passing
    if 'Passing_YDS' in row and pd.notna(row['Passing_YDS']):
        points += row['Passing_YDS'] * 0.04
    if 'Passing_TD' in row and pd.notna(row['Passing_TD']):
        points += row['Passing_TD'] * 4
    if 'Passing_INT' in row and pd.notna(row['Passing_INT']):
        points += row['Passing_INT'] * -2
    # Rushing
    if 'Rushing_YDS' in row and pd.notna(row['Rushing_YDS']):
        points += row['Rushing_YDS'] * 0.1
    if 'Rushing_TD' in row and pd.notna(row['Rushing_TD']):
        points += row['Rushing_TD'] * 6
    # Receiving
    if 'Receiving_YDS' in row and pd.notna(row['Receiving_YDS']):
        points += row['Receiving_YDS'] * 0.1
    if 'Receiving_TD' in row and pd.notna(row['Receiving_TD']):
        points += row['Receiving_TD'] * 6
    if is_ppr and 'Receiving_REC' in row and pd.notna(row['Receiving_REC']):
        points += row['Receiving_REC'] * 1
    # Fumbles
    if 'Fumbles_LOST' in row and pd.notna(row['Fumbles_LOST']):
        points += row['Fumbles_LOST'] * -2
    return points

def create_tiers(df, points_col='Projected_Points'):
    if df.empty:
        return df
    df = df.sort_values(points_col, ascending=False).reset_index(drop=True)
    num_tiers = min(10, len(df) // 5 + 1)
    if num_tiers < 2:
        df['Tier'] = 1
        return df
    try:
        df['Tier'] = pd.qcut(df[points_col], q=num_tiers, labels=range(num_tiers, 0, -1), duplicates='drop')
    except ValueError:
        df['Tier'] = 1
    return df

def load_and_process_cheatsheet(file_path):
    wb = pd.ExcelFile(file_path)
    sheets = wb.sheet_names
    data = {}
    for sheet in sheets:
        df = pd.read_excel(wb, sheet)
        df.columns = df.columns.str.strip().str.replace(r'Unnamed:\s*\d+', '', regex=True).str.strip()
        if 'Player Name' in df.columns:
            df = df.rename(columns={'Player Name': 'Name'})
        if 'Team' not in df.columns:
            df['Team'] = ''
        if 'Pos' not in df.columns:
            df['Pos'] = sheet.split('_')[-1].upper() if '_' in sheet else ''
        data[sheet] = df
    overall_key = [k for k in data if 'overall' in k.lower()]
    if not overall_key:
        return pd.DataFrame(), {}
    overall_key = overall_key[0]
    df_overall = data[overall_key]
    df_overall['Projected_Points'] = df_overall.apply(calculate_fantasy_points, axis=1)
    positional = {}
    for pos in ['QB', 'RB', 'TE', 'WR']:
        pos_key = [k for k in data if pos.lower() in k.lower()]
        if pos_key:
            df_pos = data[pos_key[0]]
            df_pos['Projected_Points'] = df_pos.apply(calculate_fantasy_points, axis=1)
            positional[pos] = df_pos
    return df_overall, positional

def load_and_process_rotowire(file_path):
    wb = pd.ExcelFile(file_path)
    df_passing = pd.read_excel(wb, 'rotowire-passing-basic-stats')
    df_rushing = pd.read_excel(wb, 'rotowire-rushing-basic-stats')
    df_receiving = pd.read_excel(wb, 'rotowire-receiving-basic-stats')
    df_all = df_passing.merge(df_rushing, on=['Name', 'Team', 'Pos'], how='outer', suffixes=('_pass', '_rush'))
    df_all = df_all.merge(df_receiving, on=['Name', 'Team', 'Pos'], how='outer')
    stat_cols = [col for col in df_all.columns if col not in ['Name', 'Team', 'Pos', 'G']]
    df_all[stat_cols] = df_all[stat_cols].fillna(0)
    df_all['G'] = df_all.filter(regex='^G').max(axis=1)
    rename_dict = {
        'Passing_COMP_pass': 'Passing_COMP', 'Passing_ATT_pass': 'Passing_ATT', 'Passing_YDS_pass': 'Passing_YDS',
        'Passing_TD_pass': 'Passing_TD', 'Passing_INT_pass': 'Passing_INT',
        'Rushing_ATT_rush': 'Rushing_ATT', 'Rushing_YDS_rush': 'Rushing_YDS', 'Rushing_TD_rush': 'Rushing_TD',
        'Receiving_REC': 'Receiving_REC', 'Receiving_YDS': 'Receiving_YDS', 'Receiving_TD': 'Receiving_TD',
        'Receiving_TAR': 'Receiving_TAR', 'Fumbles_LOST': 'Fumbles_LOST'
    }
    df_all = df_all.rename(columns=rename_dict)
    df_all['Projected_Points'] = df_all.apply(calculate_fantasy_points, axis=1)
    positional = {}
    for pos in ['QB', 'RB', 'TE', 'WR']:
        pos_df = df_all[df_all['Pos'] == pos].copy()
        positional[pos] = pos_df
    df_overall = df_all.copy()
    return df_overall, positional

def load_and_process_fantasypros(file_path):
    try:
        wb = pd.ExcelFile(file_path)
        sheets = wb.sheet_names
        if 'Empty' in sheets:
            return pd.DataFrame(), {}
        data = {}
        for sheet in sheets:
            df = pd.read_excel(wb, sheet)
            pos = sheet.split('_')[-1].upper() if '_' in sheet else 'OVERALL'
            df['Pos'] = pos
            data[sheet] = df
        overall_key = [k for k in data if 'overall' in k.lower()]
        df_overall = pd.DataFrame()
        if overall_key:
            df_overall = data[overall_key[0]]
        positional = {}
        for pos in ['QB', 'RB', 'TE', 'WR']:
            pos_key = [k for k in data if pos.lower() in k.lower()]
            if pos_key:
                positional[pos] = data[pos_key[0]]
        for df in [df_overall] + list(positional.values()):
            if not df.empty:
                df['Projected_Points'] = df.apply(calculate_fantasy_points, axis=1)
        return df_overall, positional
    except Exception as e:
        print(f"Error loading FantasyPros: {e}")
        return pd.DataFrame(), {}

def points_allowed_score(pts):
    if pd.isna(pts):
        return 0
    pts = int(pts)
    if pts <= 0:
        return 10
    elif pts <= 6:
        return 7
    elif pts <= 13:
        return 4
    elif pts <= 20:
        return 1
    elif pts <= 27:
        return 0
    elif pts <= 34:
        return -1
    else:
        return -4

def yards_allowed_score(yds):
    if pd.isna(yds):
        return 0
    yds = int(yds)
    if yds < 100:
        return 5
    elif yds < 200:
        return 3
    elif yds < 300:
        return 2
    elif yds < 350:
        return 0
    elif yds < 400:
        return -1
    elif yds < 450:
        return -3
    else:
        return -5

def load_team_stats(file_path):
    wb = pd.ExcelFile(file_path)
    df_def = pd.read_excel(wb, 'defense-team-stats')
    df_def.columns = df_def.columns.str.strip()
    df_def = df_def.rename(columns={'Own_Team': 'Team'})
    df_def_opp = pd.read_excel(wb, 'defense-opp-team-stats')
    df_def_opp.columns = df_def_opp.columns.str.strip()
    df_def_opp = df_def_opp.rename(columns={'Opponents_Team': 'Team'})
    df_overall_opp = pd.read_excel(wb, 'overall-opp-team-stats')
    df_overall_opp.columns = df_overall_opp.columns.str.strip()
    df_overall_opp = df_overall_opp.rename(columns={'Opponents_Team': 'Team'})
    df_dst = df_def.merge(df_def_opp[['Team', 'Basic Stats_PTS Allowed']], on='Team', how='left', suffixes=('', '_opp'))
    df_dst = df_dst.merge(df_overall_opp[['Team', 'Basic Stats_Yards']], on='Team', how='left', suffixes=('', '_opp'))
    df_dst['Pos'] = 'DST'
    df_dst['Name'] = df_dst['Team'] + ' DST'
    df_dst['Projected_Points'] = 0.0
    if 'Basic Stats_PTS Allowed' in df_dst:
        df_dst['Projected_Points'] += df_dst['Basic Stats_PTS Allowed'].apply(points_allowed_score)
    if 'Basic Stats_Yards' in df_dst:
        df_dst['Projected_Points'] += df_dst['Basic Stats_Yards'].apply(yards_allowed_score)
    if 'Sacks_Sacks' in df_dst:
        df_dst['Projected_Points'] += df_dst['Sacks_Sacks'] * 1
    if 'Interceptions_Interceptions' in df_dst:
        df_dst['Projected_Points'] += df_dst['Interceptions_Interceptions'] * 2
    if 'Fumbles_Recoveries' in df_dst:
        df_dst['Projected_Points'] += df_dst['Fumbles_Recoveries'] * 2
    if 'Interceptions_TD' in df_dst and 'Fumbles_TD' in df_dst:
        df_dst['Projected_Points'] += (df_dst['Interceptions_TD'] + df_dst['Fumbles_TD']) * 6
    if 'Scoring_Safeties' in df_dst:
        df_dst['Projected_Points'] += df_dst['Scoring_Safeties'] * 2
    return df_dst[['Name', 'Team', 'Pos', 'Projected_Points']]

def generate_rankings(source, df_overall, positional, df_dst, is_superflex=False):
    if not df_overall.empty:
        df_overall = pd.concat([df_overall, df_dst], ignore_index=True)
        df_overall = create_tiers(df_overall)
        df_overall['Rank'] = df_overall['Projected_Points'].rank(ascending=False, method='min')
    else:
        df_overall = df_dst
        df_overall = create_tiers(df_overall)
        df_overall['Rank'] = df_overall['Projected_Points'].rank(ascending=False, method='min')
    if not df_overall.empty:
        df_no_qb = df_overall[df_overall['Pos'] != 'QB'].copy()
        df_no_qb = create_tiers(df_no_qb)
        df_no_qb['Rank'] = df_no_qb['Projected_Points'].rank(ascending=False, method='min')
    else:
        df_no_qb = pd.DataFrame()
    pos_rankings = {}
    positional['DST'] = df_dst
    for pos, df_pos in positional.items():
        if not df_pos.empty:
            df_pos = create_tiers(df_pos)
            df_pos['Rank'] = df_pos['Projected_Points'].rank(ascending=False, method='min')
            pos_rankings[pos] = df_pos
    return df_overall, df_no_qb, pos_rankings

def compare_lists(set1_overall, set2_overall, set1_no_qb, set2_no_qb, set1_pos, set2_pos):
    comparison = "Comparison of Rankings:\n\n"
    comparison += "Overall Top 10:\n"
    comparison += "With Cheatsheet Dynasty Superflex:\n"
    comparison += str(set1_overall[['Name', 'Pos', 'Projected_Points', 'Tier', 'Rank']].head(10)) + "\n\n"
    comparison += "With Rotowire and Team Stats:\n"
    comparison += str(set2_overall[['Name', 'Pos', 'Projected_Points', 'Tier', 'Rank']].head(10)) + "\n\n"
    comparison += "Overall without QB Top 10:\n"
    comparison += "With Cheatsheet Dynasty Superflex:\n"
    comparison += str(set1_no_qb[['Name', 'Pos', 'Projected_Points', 'Tier', 'Rank']].head(10)) + "\n\n"
    comparison += "With Rotowire and Team Stats:\n"
    comparison += str(set2_no_qb[['Name', 'Pos', 'Projected_Points', 'Tier', 'Rank']].head(10)) + "\n\n"
    for pos in ['QB', 'RB', 'WR', 'TE', 'DST']:
        comparison += f"{pos} Top 5:\n"
        comparison += "With Cheatsheet Dynasty Superflex:\n"
        if pos in set1_pos:
            comparison += str(set1_pos[pos][['Name', 'Projected_Points', 'Tier', 'Rank']].head(5)) + "\n\n"
        comparison += "With Rotowire and Team Stats:\n"
        if pos in set2_pos:
            comparison += str(set2_pos[pos][['Name', 'Projected_Points', 'Tier', 'Rank']].head(5)) + "\n\n"
    set1_top10 = set(set1_overall['Name'].head(10))
    set2_top10 = set(set2_overall['Name'].head(10))
    diff1 = set1_top10 - set2_top10
    diff2 = set2_top10 - set1_top10
    comparison += f"Players in With Cheatsheet Dynasty Superflex top 10 not in With Rotowire and Team Stats: {diff1}\n"
    comparison += f"Players in With Rotowire and Team Stats top 10 not in With Cheatsheet Dynasty Superflex: {diff2}\n"
    return comparison

# Main
output_file = os.path.join(directory, 'fantasy_rankings.xlsx')
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    cheatsheet_path = os.path.join(directory, 'Cheatsheet_Dynasty_Superflex_combined.xlsx')
    df_overall1, positional1 = load_and_process_cheatsheet(cheatsheet_path)
    rotowire_path = os.path.join(directory, 'Rotowire_Stats_combined.xlsx')
    df_overall_r, positional_r = load_and_process_rotowire(rotowire_path)
    team_stats_path = os.path.join(directory, 'Team_Stats_combined.xlsx')
    df_dst1 = load_team_stats(team_stats_path)
    fantasypros_path = os.path.join(directory, 'FantasyPros_combined.xlsx')
    df_overall_fp, positional_fp = load_and_process_fantasypros(fantasypros_path)
    df_overall1_set, df_no_qb1, pos_rank1 = generate_rankings('with_cheatsheet', df_overall1, positional1, df_dst1, is_superflex=True)
    df_overall1_set.to_excel(writer, sheet_name='With_Cheatsheet_Overall', index=False)
    df_no_qb1.to_excel(writer, sheet_name='With_Cheatsheet_No_QB', index=False)
    for pos, df in pos_rank1.items():
        df.to_excel(writer, sheet_name=f'With_Cheatsheet_{pos}', index=False)
    df_overall2 = df_overall_r
    positional2 = positional_r
    df_dst2 = df_dst1
    df_overall2_set, df_no_qb2, pos_rank2 = generate_rankings('without_cheatsheet', df_overall2, positional2, df_dst2)
    df_overall2_set.to_excel(writer, sheet_name='Without_Cheatsheet_Overall', index=False)
    df_no_qb2.to_excel(writer, sheet_name='Without_Cheatsheet_No_QB', index=False)
    for pos, df in pos_rank2.items():
        df.to_excel(writer, sheet_name=f'Without_Cheatsheet_{pos}', index=False)

print(f'Rankings Excel file created at: {output_file}')

comparison = compare_lists(df_overall1_set, df_overall2_set, df_no_qb1, df_no_qb2, pos_rank1, pos_rank2)
print(comparison)