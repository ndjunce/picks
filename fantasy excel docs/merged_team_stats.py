import pandas as pd
import os

# Define the folder path
folder_path = r"C:\fantasy python\fantasy excel docs"

# List of file names to merge
files_to_merge = [
    "rushing-opp-team-stats", "rushing-team-stats", "passing-opp-team-stats",
    "passing-team-stats", "overall-opp-team-stats", "overall-team-stats",
    "WRTERB-targets (1)", "WRTERB-targets", "snap-counts-DLLBDB",
    "snap-counts-QBRBWRTE", "rotowire-passing-basic-stats",
    "rotowire-passing-advanced-stats", "rotowire-passing-redzone-stats",
    "rotowire-passing-fantasy-stats", "rotowire-rushing-basic-stats",
    "rotowire-rushing-advanced-stats", "rotowire-rushing-redzone-stats",
    "rotowire-rushing-fantasy-stats", "rotowire-receiving-fantasy-stats",
    "rotowire-receiving-redzone-stats", "rotowire-receiving-advanced-stats",
    "rotowire-receiving-basic-stats", "rotowire-defense-basic-stats",
    "rotowire-defense-passdef-stats", "rotowire-defense-fantasy-stats",
    "rotowire-kicking-fantasy-stats", "rotowire-kicking-basic-stats",
    "split-stats", "rotowire-projections", "cheatsheet-te_dynasty",
    "cheatsheet-wr_dynasty", "cheatsheet-rb_dynasty", "cheatsheet-qb_dynasty",
    "cheatsheet-overall_dynasty", "cheatsheet-wr_dyansty superflex",
    "cheatsheet-rb_dyansty superflex", "cheatsheet-qb_dyansty superflex",
    "cheatsheet-overall_dyansty superflex", "cheatsheet-db", "cheatsheet-lb",
    "cheatsheet-dl", "cheatsheet-ov", "cheatsheet-ol", "cheatsheet-def",
    "cheatsheet-k", "cheatsheet-te_ppr", "cheatsheet-wr_ppr",
    "cheatsheet-rb_ppr", "cheatsheet-ov_ppr", "misc-opp-team-stats",
    "misc-team-stats", "returns-opp-team-stats", "returns-team-stats",
    "punting-opp-team-stats", "punting-team-stats", "kicking-opp-team-stats",
    "kicking-team-stats", "passdef-team-stats", "defense-opp-team-stats",
    "defense-team-stats", "receiving-opp-team-stats", "receiving-team-stats",
    "auction-values-TE_4man", "auction-values-WR_4man", "auction-values-RB_4man",
    "auction-values-QB_4man", "auction-values-ALL_4man", "auction-values-TE_10team",
    "auction-values-WR_10team", "auction-values-RB_10team", "auction-values-QB_10team",
    "auction-values-ALL_10team"
]

# Create a dictionary to store DataFrames with sheet names
excel_data = {}
for file in files_to_merge:
    file_path = os.path.join(folder_path, file)
    for ext in ['.csv', '.xlsx', '.xls']:  # Check common extensions
        full_path = file_path + ext
        if os.path.exists(full_path):
            try:
                if full_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(full_path)
                else:
                    df = pd.read_csv(full_path)
                sheet_name = file.replace(" ", "_")  # Replace spaces for valid sheet names
                if len(sheet_name) > 31:  # Excel sheet name limit is 31 characters
                    sheet_name = sheet_name[:31]
                excel_data[sheet_name] = df
                break
            except Exception as e:
                continue
    else:
        print(f"Warning: File {file} not found with any supported extension.")

# Save all DataFrames to a single Excel file with each on its own sheet
if excel_data:
    output_path = os.path.join(folder_path, 'merged_team_stats.xlsx')
    with pd.ExcelWriter(output_path) as writer:
        for sheet_name, df in excel_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"Merged file saved as: {output_path}")
else:
    print("No valid files were found to merge.")