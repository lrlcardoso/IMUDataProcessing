"""
==============================================================================
Title:          Helper Functions
Description:    This tool is meant to be used separately from the 
                main.py pipeline, primarily to fill in or correct missing 
                global date fields in raw logger files.

                 - IMU_Global_Date_Filler: Opens all IMU CSV files in a 
                                           specified folder and overwrites 
                                           the 'g_year', 'g_month', and 'g_day'
                                           columns using user-defined values. 
                                           The first data row is always set to 
                                           0 for all three columns. 
Author:         Lucas R. L. Cardoso
Project:        VRRehab_UQ-MyTurn
Date:           2025-05-08
Version:        1.0
==============================================================================
Usage:
    Run from terminal:
        python utils/helper_functions.py "path/to/folder" 25 03 03

    Example:
        python utils/helper_functions.py "C:\\MyProject\\Logger1\\" 25 03 03

Dependencies:
    - Python >= 3.x
    - Required libraries: os, glob, pandas

Changelog:
    - v1.0: [2025-05-08] Initial release.
==============================================================================
"""

import os
import pandas as pd
import glob

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

            # Ensure first row is set to 0s
            df.at[0, 'g_year'] = 0
            df.at[0, 'g_month'] = 0
            df.at[0, 'g_day'] = 0

            df.to_csv(csv_file, index=False)
            print(f"✅ Updated: {csv_file}")
        else:
            print(f"⚠️ Skipped (missing columns): {csv_file}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Overwrite g_year, g_month, and g_day in CSV files.")
    parser.add_argument("folder", help="Path to folder containing CSV files")
    parser.add_argument("year", type=int, help="Year to set (e.g., 25)")
    parser.add_argument("month", type=int, help="Month to set (e.g., 3)")
    parser.add_argument("day", type=int, help="Day to set (e.g., 3)")

    args = parser.parse_args()
    IMU_Global_Date_Filler(args.folder, args.year, args.month, args.day)
