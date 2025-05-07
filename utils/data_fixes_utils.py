"""
==============================================================================
Title:          IMU Data Fix Utility
Description:    Identifies and fixes timestamp columns in IMU CSV files based on
                expected date and session time patterns.
Author:         Lucas R. L. Cardoso
Project:        VRRehab_UQ-MyTurn
Date:           2025-04-28
Version:        1.1
==============================================================================
Usage:
    from data_fixes_utils import fix_imu_file

Dependencies:
    - Python >= 3.x
    - Required libraries: os, glob

Changelog:
    - v1.0: [2025-04-25] Initial release.
    - v1.1: [2025-05-07] Improved detection.
==============================================================================
"""

import os
import argparse
import pandas as pd
import numpy as np

def fix_imu_file(input_csv, output_dir, date_part, time_of_the_session, log_path):
    try:
        yy, mm, dd = int(date_part[:2]), int(date_part[2:4]), int(date_part[4:6])
        df = pd.read_csv(input_csv)

        time_cols = ["g_year", "g_month", "g_day", "g_hour", "g_minute", "g_second", "g_hund"]
        available_cols = [col for col in time_cols if col in df.columns]
        if not available_cols:
            raise ValueError("No expected time columns found.")

        # Skip if all time columns are zero
        if df[available_cols].eq(0).all(axis=None):
            with open(log_path, "a") as logf:
                logf.write(f"[SKIPPED] {os.path.basename(input_csv)}: all time columns are zero\n")
            print(f"[SKIPPED] {os.path.basename(input_csv)}: all time columns are zero")
            return

        id_map = {}

        def match_strict(value):
            return [col for col in available_cols if set(df[col].dropna().unique()).issubset({value, 0})]

        # Steps 1–3: year, month, day
        for key, val in zip(["year", "month", "day"], [yy, mm, dd]):
            matches = match_strict(val)
            if not matches:
                raise ValueError(f"{key.capitalize()} column not found (no matching candidates)")
            if len(matches) > 1:
                raise ValueError(f"{key.capitalize()} column not uniquely identified: {matches}")
            id_map[key] = matches[0]
            available_cols.remove(matches[0])

        # Step 4: hour
        hour_range = {time_of_the_session - 1, time_of_the_session, time_of_the_session + 1}
        hour_matches = [
            col for col in available_cols
            if 0 < len(non_zero := set(df[col].dropna().unique()) - {0}) <= 2 and non_zero.issubset(hour_range)
        ]
        if not hour_matches:
            raise ValueError("Hour column not found (no matching candidates)")
        if len(hour_matches) > 1:
            raise ValueError(f"Hour column not uniquely identified: {hour_matches}")
        id_map["hour"] = hour_matches[0]
        available_cols.remove(id_map["hour"])

        # Step 5: hundredths
        hund_matches = [
            col for col in available_cols
            if df[col].min() == 0 and df[col].max() == 99 and df[col].nunique() > 50
        ]
        if not hund_matches:
            raise ValueError("Hundredths column not found (no matching candidates)")
        if len(hund_matches) > 1:
            raise ValueError(f"Hundredths column not uniquely identified: {hund_matches}")
        id_map["hund"] = hund_matches[0]
        available_cols.remove(id_map["hund"])

        # Step 6: seconds
        second_matches = []
        for col in available_cols:
            if df[col].between(0, 59).all():
                values = df[col].values
                idx = np.where(values != 0)[0]
                if len(idx) > 1:
                    changes = np.where(np.diff(values[idx]) != 0)[0]
                    if len(changes) > 1:
                        avg = np.mean(np.diff(idx[changes]))
                        if 80 <= avg <= 120:
                            second_matches.append(col)
        if not second_matches:
            raise ValueError("Second column not found (no matching candidates)")
        if len(second_matches) > 1:
            raise ValueError(f"Second column not uniquely identified: {second_matches}")
        id_map["second"] = second_matches[0]
        available_cols.remove(id_map["second"])

        # Step 7: minute
        minute_matches = []
        sec_col = df[id_map["second"]].values
        for col in available_cols:
            if df[col].between(0, 59).all():
                min_col = df[col].values
                roll = np.where(np.diff(sec_col) < 0)[0]
                if len(roll) > 1 and np.all(np.abs(np.diff(min_col[roll])) <= 1):
                    minute_matches.append(col)
        if not minute_matches:
            raise ValueError("Minute column not found (no matching candidates)")
        if len(minute_matches) > 1:
            raise ValueError(f"Minute column not uniquely identified: {minute_matches}")
        id_map["minute"] = minute_matches[0]

        # Rename to standard names
        std_names = {
            "year": "g_year", "month": "g_month", "day": "g_day",
            "hour": "g_hour", "minute": "g_minute", "second": "g_second", "hund": "g_hund"
        }
        df.rename(columns={id_map[k]: v for k, v in std_names.items() if id_map[k] != v}, inplace=True)

        # Reorder columns
        orig_order = pd.read_csv(input_csv, nrows=0).columns.tolist()
        existing = [c for c in orig_order if c in df.columns]
        rest = [c for c in df.columns if c not in existing]
        df = df[existing + rest]

        # Output filename
        ts_cols = list(std_names.values())
        valid_row = df[df[ts_cols].ne(0).any(axis=1)].iloc[0]
        h, m, s = map(int, valid_row[["g_hour", "g_minute", "g_second"]])
        suffix = os.path.basename(input_csv).split("_")[-1]
        new_name = f"{date_part}_{h:02d}{m:02d}{s:02d}_{suffix}"
        out_path = os.path.join(output_dir, new_name)

        os.makedirs(output_dir, exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"[SUCCESS] Saved: {out_path}")

    except Exception as e:
        # Log error
        with open(log_path, "a") as logf:
            logf.write(f"[ERROR] {os.path.basename(input_csv)}: {str(e)}\n")

        # Fallback save
        fallback_dir = os.path.join(output_dir, "Still_needs_to_fix")
        os.makedirs(fallback_dir, exist_ok=True)
        fallback_path = os.path.join(fallback_dir, os.path.basename(input_csv))
        pd.read_csv(input_csv).to_csv(fallback_path, index=False)
        print(f"[WARNING] Original file copied to: {fallback_path}")


# === Standalone Runner ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix IMU CSV timestamp columns.")
    # parser.add_argument("--input", required=True, help="Path to input CSV file.")
    parser.add_argument("--output", required=True, help="Directory to save fixed CSV.")
    parser.add_argument("--date", required=True, help="Date string in format yymmdd (e.g., 250320).")
    parser.add_argument("--hour", required=True, type=int, help="Session hour as integer (1–24).")

    args = parser.parse_args()
    fix_imu_file(
        input_csv=r"C:\Users\s4659771\Documents\MyTurn_Project\Data\Raw\P01\Session3_20250217\WMORE\Logger3\440502_171135_03.csv",
        output_dir=args.output,
        date_part=args.date,
        time_of_the_session=args.hour
    )
