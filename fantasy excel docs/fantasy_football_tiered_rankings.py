import pandas as pd

import os
print(os.path.isfile(r'C:\Users\ndjun\OneDrive\Desktop\fantasy python\Rankings-All.xlsx'))


# Load data from the provided Excel file
df = pd.read_excel(r'C:\Users\ndjun\OneDrive\Desktop\fantasy python\Rankings-All.xlsx', sheet_name='rankings-ALL', header=1)


# Define replacement rank formulas for each position based on league size
replacement_factors = {
    'QB': lambda ls: ls + 3,
    'RB': lambda ls: ls * 2 + ls // 2,
    'WR': lambda ls: ls * 2 + ls // 2,
    'TE': lambda ls: ls + 3
}

# Function to calculate replacement level for a position
def get_replacement_level(df_pos, replacement_rank):
    df_pos_sorted = df_pos.sort_values('Pts', ascending=False)
    if len(df_pos_sorted) < replacement_rank + 1:
        start = max(0, len(df_pos_sorted) - 3)
        replacement_players = df_pos_sorted.iloc[start:]
    else:
        start = replacement_rank - 2
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
    replacement_ranks = {pos: replacement_factors[pos](league_size) for pos in ['QB', 'RB', 'WR', 'TE']}
    for pos in ['QB', 'RB', 'WR', 'TE']:
        df_pos = df_tiered[df_tiered['Pos'] == pos]
        replacement_rank = replacement_ranks[pos]
        replacement_level = get_replacement_level(df_pos, replacement_rank)

        value_score_col = f'value_score_{league_size}'
        df_tiered.loc[df_tiered['Pos'] == pos, value_score_col] = df_tiered.loc[df_tiered['Pos'] == pos, 'Pts'] - replacement_level

        value_scores = df_tiered.loc[df_tiered['Pos'] == pos, value_score_col]
        tier_col = f'tier_{league_size}'
        if len(value_scores) > 5:
            try:
                tiers = pd.qcut(value_scores, q=5, labels=False, duplicates='drop') + 1  # Labels 1–5
            except ValueError:
                tiers = pd.Series([1] * len(value_scores), index=value_scores.index)
        else:
            tiers = pd.Series([1] * len(value_scores), index=value_scores.index)

        # Ensure tiers is an int Series before assigning
        df_tiered.loc[df_tiered['Pos'] == pos, tier_col] = tiers.astype("Int64")

# Save the results to a new Excel file
df_tiered.to_excel(r'C:\Users\ndjun\OneDrive\Desktop\fantasy python\tiered_rankings.xlsx', index=False)

