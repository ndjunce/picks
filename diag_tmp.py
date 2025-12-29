import pandas as pd
import sqlite3

def main():
    excel = "nfl_picks_2025.xlsx"
    conn = sqlite3.connect("picks.db")
    people = ["bobby","chet","clyde","henry","nick","riley"]
    print("DB tiebreakers:")
    rows = list(conn.execute("select week, count(*) from picks where is_tiebreaker_game=1 group by week order by week"))
    col_list = ",".join([f"{p}_tiebreaker" for p in people])
    for w, c in rows:
        vals = conn.execute(f"select {col_list} from picks where week=? and is_tiebreaker_game=1", (w,)).fetchone()
        print(f"Week {w}: count={c}, tbs={vals}")

    print("\nBogus numeric team rows:")
    for r in conn.execute("select week, away_team, home_team from picks where (away_team glob '[0-9]*' or home_team glob '[0-9]*')"):
        print(r)

    print("\nExcel detection:")
    xl = pd.ExcelFile(excel)
    sheets = [s for s in xl.sheet_names if s.lower() != 'cumulative']
    for sheet in sheets:
        df = xl.parse(sheet, header=None)
        game_rows = []
        for idx, row in df.iterrows():
            if idx < 2 or pd.isna(row.iloc[7]) or pd.isna(row.iloc[9]):
                continue
            pick_cols = list(row.iloc[1:7]) + list(row.iloc[10:16])
            has_x = any((isinstance(v, str) and v.strip().lower() == 'x') for v in pick_cols)
            if has_x:
                game_rows.append(idx)
        last_game = game_rows[-1] if game_rows else None
        tb_row = None
        tb_vals = None
        if last_game is not None:
            for offset in range(1, 4):
                if last_game + offset >= len(df):
                    break
                next_row = df.iloc[last_game + offset]
                vals1 = next_row.iloc[1:7]
                vals2 = next_row.iloc[10:16]
                combined = []
                for v1, v2 in zip(vals1, vals2):
                    chosen = None
                    for candidate in (v1, v2):
                        if pd.notna(candidate) and str(candidate).replace('.', '', 1).isdigit():
                            chosen = int(float(candidate))
                            break
                    combined.append(chosen)
                if any(c is not None for c in combined):
                    tb_row = last_game + offset
                    tb_vals = combined
                    break
        print(f"{sheet}: last_game={last_game}, tb_row={tb_row}, tb_vals={tb_vals}")

if __name__ == "__main__":
    main()
