import pandas as pd
import numpy as np
from itertools import permutations
import os
import shutil
from glob import glob

def find_constant_col(df, value):
    for col in df.columns:
        col_data = df[col][df[col] != 0]
        if len(col_data) > 0 and (col_data.nunique() == 1) and (col_data.iloc[0] == value):
            return col
    return None

def get_allowed_hours(session_hour):
    # Returns e.g. {0, session_hour-1, session_hour, session_hour+1} for validation
    # Handles edge cases for 0 and 23 as needed
    hours = {session_hour}
    if session_hour > 0:
        hours.add(session_hour - 1)
    hours.add((session_hour + 1) % 24)
    hours.add(0)  # Always add 0 (reset)
    return hours

def score_time_perm_strict(df, cols, allowed_hours):
    hour, minute, second, hund = cols
    score = 0
    if df[minute].max() > 59 or df[second].max() > 59 or df[hund].max() > 99:
        return float('inf')
    vals_hour = set(df[hour].unique())
    if not vals_hour <= allowed_hours:
        score += 1000
    hour_values = df[hour].values
    minute_values = df[minute].values
    second_values = df[second].values
    hund_values = df[hund].values
    for i in range(1, len(df)):
        if hund_values[i] == 0 and hund_values[i-1] == 99:
            if second_values[i] != (second_values[i-1] + 1 if second_values[i-1] < 59 else 0):
                score += 10
        if second_values[i] == 0 and second_values[i-1] == 59:
            if minute_values[i] != (minute_values[i-1] + 1 if minute_values[i-1] < 59 else 0):
                score += 10
        if minute_values[i] == 0 and minute_values[i-1] == 59:
            if hour_values[i] != (hour_values[i-1] + 1 if hour_values[i-1] < 10 else 8):
                score += 10
    return score

def fix_imu_file(input_csv, output_dir, date_part, time_of_the_session):
    columns_required = [
        "ax", "ay", "az", "gx", "gy", "gz", "mx", "my", "mz", "temp", "valid",
        "g_year", "g_month", "g_day", "g_hour", "g_minute", "g_second", "g_hund"
    ]
    time_fields = ["g_year", "g_month", "g_day", "g_hour", "g_minute", "g_second", "g_hund"]

    df = pd.read_csv(input_csv)
    global_time_cols = ["g_year", "g_month", "g_day", "g_hour", "g_minute", "g_second", "g_hund"]
    if all(col in df.columns for col in global_time_cols):
        if (df[global_time_cols] == 0).all(axis=None):
            msg = f"[SKIP] {os.path.basename(input_csv)} -> All global time columns are zero | Size: {os.path.getsize(input_csv)} bytes"
            print(msg)
            return None, msg

    potential_time_cols = [col for col in df.columns if col.endswith(("_year", "_month", "_day", "_hour", "_minute", "_second", "_hund"))]
    nonzero_rows = ~(df[potential_time_cols] == 0).all(axis=1)
    df_time = df[nonzero_rows].copy()
    col_g_year = find_constant_col(df_time, 25)
    col_g_month = find_constant_col(df_time, 3)
    col_g_day = find_constant_col(df_time, 20)
    locked_cols = [col_g_year, col_g_month, col_g_day]
    remaining_time_candidates = [col for col in potential_time_cols if col not in locked_cols]
    if len(remaining_time_candidates) > 4:
        g_cols = [col for col in remaining_time_candidates if col.startswith("g_")]
        if len(g_cols) >= 4:
            time_perm_candidates = g_cols[:4]
        else:
            time_perm_candidates = remaining_time_candidates[:4]
    else:
        time_perm_candidates = remaining_time_candidates
    df_time_200 = df_time.iloc[:200].copy()
    
    allowed_hours = get_allowed_hours(time_of_the_session)
    best_score = float('inf')
    best_perm = None
    for perm in permutations(time_perm_candidates):
        perm_score = score_time_perm_strict(df_time_200, perm, allowed_hours)
        if perm_score < best_score:
            best_score = perm_score
            best_perm = perm
    if best_perm is None:
        msg = f"[SKIP] {os.path.basename(input_csv)} -> Could not find valid mapping | Size: {os.path.getsize(input_csv)} bytes"
        print(msg)
        return None, msg
    best_time_col_map = {
        "g_year": col_g_year,
        "g_month": col_g_month,
        "g_day": col_g_day,
        "g_hour": best_perm[0],
        "g_minute": best_perm[1],
        "g_second": best_perm[2],
        "g_hund": best_perm[3]
    }
    df_clean = pd.DataFrame()
    for col in columns_required:
        if col in best_time_col_map and best_time_col_map[col]:
            df_clean[col] = df_time[best_time_col_map[col]]
        else:
            df_clean[col] = df_time[col]
    valid_idx = df_clean[time_fields].apply(lambda x: any(x != 0), axis=1).idxmax()
    first_valid_row = df_clean.loc[valid_idx]
    hour = f"{int(first_valid_row['g_hour']):02d}"
    minute = f"{int(first_valid_row['g_minute']):02d}"
    second = f"{int(first_valid_row['g_second']):02d}"

    # ---- OUTPUT FILENAME LOGIC (no _02, handle duplicates) ----
    base_name = f"{date_part}_{hour}{minute}{second}"
    final_filename = f"{base_name}.csv"
    final_csv_path = os.path.join(output_dir, final_filename)
    counter = 2
    while os.path.exists(final_csv_path):
        final_filename = f"{base_name}_{counter:02d}.csv"
        final_csv_path = os.path.join(output_dir, final_filename)
        counter += 1
    # ----------------------------------------------------------

    df_clean.to_csv(final_csv_path, index=False)
    msg = f"[OK] {os.path.basename(input_csv)} -> {final_filename} | Size: {os.path.getsize(input_csv)} bytes"
    print(msg)
    return final_csv_path, msg

def fix_imu_folder(folder_path, output_dir="./", date_part="250408"):
    csv_files = glob(os.path.join(folder_path, "*.csv"))
    print(f"Found {len(csv_files)} CSV files in {folder_path}.")
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "logfile.txt")
    logs = []
    for file in csv_files:
        orig_name = os.path.basename(file)
        file_size = os.path.getsize(file)
        if orig_name.startswith(f"{date_part}_"):
            shutil.copy(file, os.path.join(output_dir, orig_name))
            msg = f"[COPY] {orig_name} -> already starts with {date_part}_ (copied) | Size: {file_size} bytes"
            print(msg)
            logs.append(msg)
            continue
        out, logmsg = fix_imu_file(file, output_dir, date_part)
        if logmsg is not None:
            logs.append(logmsg)
    with open(log_path, "w") as f:
        f.write('\n'.join(logs))
    print(f"Log file saved to {log_path}")

# USAGE EXAMPLE:
# if __name__ == "__main__":
#     fix_imu_folder(r"E:\Data_MyTurn\Raw\P09\Session2_20250320\WMORE\Logger2", output_dir='./fixed', date_part="250320")