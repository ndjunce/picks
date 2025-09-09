import pandas as pd

# Load data from the provided Excel file
df = pd.read_excel('rankings-ALL.xlsx', sheet_name='rankings-ALL', header=1)

# Define replacement rank formulas for each position based on league size
replacement_factors = {
    'QB': lambda ls: ls + 3,            # e.g., 12-team league -> 15th QB
    'RB': lambda ls: ls * 2 + ls // 2,  # e.g., 12-team league -> 30th RB
    'WR': lambda ls: ls * 2 + ls // 2,  # e.g., 12-team league -> 30th WR
    'TE': lambda ls: ls + 3             # e.g., 12-team league -> 15th TE
}

# Function to calculate replacement level for a position
def get_replacement_level(df_pos, replacement_rank):
    df_pos_sorted = df_pos.sort_values('Pts', ascending=False)
    if len(df_pos_sorted) < replacement_rank + 1:
        # If not enough players, take the last 3 available
        start = max(0, len(df_pos_sorted) - 3)
        replacement_players = df_pos_sorted.iloc[start:]
    else:
        # Take average of 3 players around the replacement rank
        start = replacement_rank - 2  # 0-based index
        end = start + 3
        if end > len(df_pos_sorted):
            end = len(df_pos_sorted)
            start = max(0, end - 3)
        replacement_players = df_pos_sorted.iloc[start:end]
    return replacement_players['Pts'].mean()

# Create a copy of the DataFrame to store results
df_tiered = df.copy()

# Process league sizes from 4 to 12 (inclusive, step 2)
for league_size in range(4, 13, 2):
    # Calculate replacement ranks for each position
    replacement_ranks = {pos: replacement_factors[pos](league_size) for pos in ['QB', 'RB', 'WR', 'TE']}
    for pos in ['QB', 'RB', 'WR', 'TE']:
        # Filter players by position
        df_pos = df_tiered[df_tiered['Pos'] == pos]
        replacement_rank = replacement_ranks[pos]
        replacement_level = get_replacement_level(df_pos, replacement_rank)
        
        # Calculate value score (Pts - replacement level)
        value_score_col = f'value_score_{league_size}'
        df_tiered.loc[df_tiered['Pos'] == pos, value_score_col] = df_tiered['Pts'] - replacement_level
        
        # Assign tiers based on value scores
        value_scores = df_tiered.loc[df_tiered['Pos'] == pos, value_score_col]
        tier_col = f'tier_{league_size}'
        if len(value_scores) > 5:
            try:
                # Divide into 5 tiers using quantiles
                tiers = pd.qcut(value_scores, q=5, labels=range(1, 6), duplicates='drop')
            except ValueError:
                # Fallback if qcut fails (e.g., too few unique values)
                tiers = [1] * len(value_scores)
        else:
            # Assign all to tier 1 if too few players
            tiers = [1] * len(value_scores)
        df_tiered.loc[df_tiered['Pos'] == pos, tier_col] = tiers

# Save the results to a new Excel file
df_tiered.to_excel('tiered_rankings.xlsx', index=False)