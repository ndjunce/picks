import pandas as pd
import os

directory = r'C:\fantasy python\fantasy excel docs\sorting'

# List of folder names
folder_names = [
    '4man',
    '10man auction',
    '12man snake',
    'Dynasty superflex',
    'ppr',
    'snap count and targets',
    'stats'
]

# Create a workbook for each folder
for folder in folder_names:
    folder_path = os.path.join(directory, folder)
    if not os.path.isdir(folder_path) or folder == 'plots':
        continue
    files = [f for f in os.listdir(folder_path) if f.endswith('.xlsx')]
    wb_name = folder.replace(' ', '_') + '_combined.xlsx'
    output_file = os.path.join(directory, wb_name)
    written_sheets = False
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for filename in files:
            try:
                file_path = os.path.join(folder_path, filename)
                df = pd.read_excel(file_path, header=None)
                # Check if multi-level header
                if len(df) > 1 and df.iloc[0].isna().sum() > len(df.columns) / 2:
                    # Multi-level
                    category_row = df.iloc[0].ffill().fillna('')
                    subheader_row = df.iloc[1].fillna('')
                    new_cols = []
                    for cat, sub in zip(category_row, subheader_row):
                        parts = [str(p).strip() for p in [cat, sub] if str(p).strip()]
                        new_col = '_'.join(parts) if parts else 'Unknown'
                        new_cols.append(new_col)
                    df.columns = new_cols
                    df = df.iloc[2:].reset_index(drop=True)
                    df = df.dropna(axis=1, how='all')
                    df = df.drop(columns=['Health_Report_Status', 'Health_Report_Injury'], errors='ignore')
                else:
                    # Single header, re-read with header=0
                    df = pd.read_excel(file_path, header=0)
                sheet_name = filename.replace('.xlsx', '')[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                written_sheets = True
            except Exception as e:
                print(f"Error with {filename} in {folder}: {e}")
        if not written_sheets:
            pd.DataFrame([['No data available']]).to_excel(writer, sheet_name='Empty', index=False)
    print(f'Workbook created at: {output_file}')