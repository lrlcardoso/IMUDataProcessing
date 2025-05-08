"""
==============================================================================
Title:          Helper Functions
Description:    This tool is meant to be used separately from the 
                main.py pipeline, primarily to fill in or correct missing 
                global date fields in raw logger files.

                 - IMU_Global_Date_Filler: Overwrites the 'g_year', 'g_month',
                   and 'g_day' columns using user-defined values. First data 
                   row is always set to 0.

                 - IMU_Global_Timestamp_Filler: Fills full global time columns
                   ['g_year' to 'g_hund'] using user-defined date and starting 
                   time, based on local time deltas from ['l_hour' to 'l_hund'].
                   Also renames files based on start global time.

Author:         Lucas R. L. Cardoso
Project:        VRRehab_UQ-MyTurn
Date:           2025-05-08
Version:        1.1
==============================================================================
Usage:
    For global date only:
        python utils/helper_functions.py date_only "path/to/folder" 25 03 03

    For full global timestamp filling:
        python utils/helper_functions.py full_timestamp "path/to/folder" 25 03 03 13 20 0 0

Dependencies:
    - Python >= 3.x
    - Required libraries: os, glob, pandas, datetime
Changelog:
    - v1.0: [2025-05-08] Initial release.
    - v1.1: [2025-05-08] Added full timestamp filling via local deltas.
==============================================================================
"""

import os
import pandas as pd
import glob
from datetime import datetime, timedelta

def IMU_Global_Date_Filler(folder_path, year, month, day):
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    print(f"Searching in: {folder_path}")
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, encoding="utf-8")
        except UnicodeDecodeError:
            print(f"[Warning] UTF-8 decode failed for: {csv_file}, trying latin1...")
            try:
                df = pd.read_csv(csv_file, encoding="latin1", error_bad_lines=False, engine='python')
            except Exception as e:
                print(f"[Error] Failed to read {csv_file}: {e}")
                continue

        required_cols = ['g_year', 'g_month', 'g_day']
        if all(col in df.columns for col in required_cols):
            df['g_year'] = year
            df['g_month'] = month
            df['g_day'] = day

            df.at[0, 'g_year'] = 0
            df.at[0, 'g_month'] = 0
            df.at[0, 'g_day'] = 0

            df.to_csv(csv_file, index=False)
            print(f"✅ Updated: {csv_file}")
        else:
            print(f"⚠️ Skipped (missing columns): {csv_file}")

def IMU_Global_Timestamp_Filler(folder_path, year, month, day, first_global_time):
    csv_files = sorted(glob.glob(os.path.join(folder_path, "*.csv")))
    if not csv_files:
        print("[ERROR] No CSV files found.")
        return

    g_time = datetime(year=2000 + year, month=month, day=day,
                      hour=first_global_time[0], minute=first_global_time[1],
                      second=first_global_time[2], microsecond=first_global_time[3] * 10000)

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, encoding="utf-8")
        except UnicodeDecodeError:
            print(f"[Warning] UTF-8 decode failed for: {csv_file}, trying latin1...")
            try:
                df = pd.read_csv(csv_file, encoding="latin1", error_bad_lines=False, engine='python')
            except Exception as e:
                print(f"[Error] Failed to read {csv_file}: {e}")
                continue

        local_cols = ['l_hour', 'l_minute', 'l_second', 'l_hund']
        if not all(col in df.columns for col in local_cols):
            print(f"[SKIPPED] Missing local time columns in: {csv_file}")
            continue

        first_l = df.loc[0, local_cols].astype(int)
        base_local_time = timedelta(
            hours=int(first_l['l_hour']),
            minutes=int(first_l['l_minute']),
            seconds=int(first_l['l_second']),
            milliseconds=int(first_l['l_hund']) * 10
        )

        g_times = []
        for _, row in df.iterrows():
            current_l = timedelta(
                hours=int(row['l_hour']),
                minutes=int(row['l_minute']),
                seconds=int(row['l_second']),
                milliseconds=int(row['l_hund']) * 10
            )
            delta = current_l - base_local_time
            this_global = g_time + delta
            g_times.append(this_global)

        g_time = g_times[-1]

        df['g_year'] = year
        df['g_month'] = month
        df['g_day'] = day
        df['g_hour'] = [t.hour for t in g_times]
        df['g_minute'] = [t.minute for t in g_times]
        df['g_second'] = [t.second for t in g_times]
        df['g_hund'] = [t.microsecond // 10000 for t in g_times]

        first_g = g_times[0]
        original_suffix = os.path.basename(csv_file).rsplit('_', 1)[-1]
        new_filename = f"{year:02}{month:02}{day:02}_{first_g.hour:02}{first_g.minute:02}{first_g.second:02}_{original_suffix}"
        new_path = os.path.join(folder_path, new_filename)

        df.to_csv(new_path, index=False)
        os.remove(csv_file) 

        print(f"✅ Saved: {new_path} (original deleted)")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Helper tool to update IMU global time columns.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Mode 1: date only
    parser_date = subparsers.add_parser("date_only", help="Fill g_year, g_month, g_day (first row = 0)")
    parser_date.add_argument("folder", help="Folder with CSV files")
    parser_date.add_argument("year", type=int, help="Year (e.g. 25)")
    parser_date.add_argument("month", type=int, help="Month (e.g. 3)")
    parser_date.add_argument("day", type=int, help="Day (e.g. 3)")

    # Mode 2: full timestamp fill
    parser_full = subparsers.add_parser("full_timestamp", help="Fill g_year to g_hund using local deltas")
    parser_full.add_argument("folder", help="Folder with CSV files")
    parser_full.add_argument("year", type=int)
    parser_full.add_argument("month", type=int)
    parser_full.add_argument("day", type=int)
    parser_full.add_argument("hour", type=int)
    parser_full.add_argument("minute", type=int)
    parser_full.add_argument("second", type=int)
    parser_full.add_argument("hund", type=int)

    args = parser.parse_args()

    if args.mode == "date_only":
        IMU_Global_Date_Filler(args.folder, args.year, args.month, args.day)
    elif args.mode == "full_timestamp":
        IMU_Global_Timestamp_Filler(args.folder, args.year, args.month, args.day,
                                    (args.hour, args.minute, args.second, args.hund))
