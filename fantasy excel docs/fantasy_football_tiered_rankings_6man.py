import pandas as pd

# Load data from the provided Excel file
df = pd.read_excel(r'C:\Users\ndjun\OneDrive\Desktop\fantasy python\rankings-ALL.xlsx', sheet_name='rankings-ALL', header=1)

# Define replacement ranks for a 6-man league
replacement_ranks = {
    'QB': 15,  # 6 teams * 2 QBs + buffer
    'RB': 21,  # 6 teams * 3.5 (2 RBs + Flex) ≈ 21
    'WR': 21,  # Similar to RBs
    'TE': 9,   # 6 teams * 1 TE + buffer
    'K': 8,    # 6 teams * 1 K + buffer
    'D': 8     # 6 teams * 1 D + buffer
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
df_tiered['value_score'] = pd.NA
df_tiered['tier'] = pd.NA

# Calculate replacement levels for each position
replacement_levels = {}
for pos in ['QB', 'RB', 'WR', 'TE', 'K', 'D']:
    df_pos = df_tiered[df_tiered['Pos'] == pos]
    replacement_levels[pos] = get_replacement_level(df_pos, replacement_ranks[pos])

# Calculate value scores for each player
for pos in ['QB', 'RB', 'WR', 'TE', 'K', 'D']:
    df_tiered.loc[df_tiered['Pos'] == pos, 'value_score'] = (
        df_tiered.loc[df_tiered['Pos'] == pos, 'Pts'] - replacement_levels[pos]
    )

# Assign tiers based on value scores (5 tiers per position)
for pos in ['QB', 'RB', 'WR', 'TE', 'K', 'D']:
    pos_mask = df_tiered['Pos'] == pos
    value_scores = df_tiered.loc[pos_mask, 'value_score']
    
    if len(value_scores.dropna()) > 5:
        try:
            tiers = pd.qcut(value_scores, q=5, labels=range(1, 6), duplicates='drop')
            df_tiered.loc[pos_mask, 'tier'] = tiers.astype(int).values
        except ValueError:
            df_tiered.loc[pos_mask, 'tier'] = 1
    else:
        df_tiered.loc[pos_mask, 'tier'] = 1

# Save the results to a new Excel file
df_tiered.to_excel(r'C:\fantasy python\tiered_rankings_6man.xlsx', index=False)



