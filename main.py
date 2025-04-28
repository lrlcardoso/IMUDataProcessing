"""
==============================================================================
Title:          IMU Data Processing Main
Description:    Entry point for IMU logger data processing pipeline. Loads,
                merges, trims, synchronizes, and saves processed logger CSVs
                for all selected patients/sessions/loggers, using centralized
                file/folder utilities. Supports additional data fixing via arguments.
Author:         Lucas R. L. Cardoso
Project:        VRRehab_UQ-MyTurn
Date:           2025-04-25
Version:        1.1
==============================================================================
Usage:
    python main.py --combineCSV
    python main.py --fixDataIssue

Dependencies:
    - Python >= 3.x
    - pandas, glob, os, argparse
    - Local modules: config.py, utils.imu_utils, utils.file_utils

Changelog:
    - v1.0: Initial release.
    - v1.1: [2025-04-25] Added argument parsing for pipeline modes.
==============================================================================
"""

import os
import re
import time
import glob
import argparse
from tqdm import tqdm
from config import (
    ROOT_DIR, SELECTED_PATIENTS, SELECTED_SESSIONS,
    SELECTED_LOGGERS, TRIM_MINUTES, TIME_OF_THE_SESSION
)
from utils.imu_utils import preprocess_logger_folder, synchronize_loggers
from utils.file_utils import get_logger_folders, get_processed_logger_save_path
from utils.data_fixes_utils import fix_imu_file

def combine_csv_pipeline():
    start_time_all = time.time()

    for patient in SELECTED_PATIENTS:
        for session in SELECTED_SESSIONS:
            logger_folders = get_logger_folders(
                ROOT_DIR,
                [patient],
                [session],
                SELECTED_LOGGERS,
                mode="Raw"
            )
            if not logger_folders:
                continue
            print("="*100)
            print(f"📝 Processing: {patient} | {session}")
            print("="*100)
            dfs = []
            loggers_for_sync = []
            for _, session_dir, logger, logger_raw_folder in logger_folders:
                print()
                print(f"📂 {logger}")
                print("-"*100)
                df = preprocess_logger_folder(logger_raw_folder, TRIM_MINUTES)
                dfs.append(df)
                loggers_for_sync.append((session_dir, logger))
            # Synchronize and save for this patient/session
            if dfs:
                print()
                dfs_sync = synchronize_loggers(dfs)
                for (session_dir, logger), df_out in tqdm(
                    zip(loggers_for_sync, dfs_sync),
                    total=len(dfs_sync),
                    desc="Synchronizing Loggers"
                ):
                    save_path = get_processed_logger_save_path(ROOT_DIR, session_dir, logger, mode="Processed")
                    df_out.to_csv(save_path, index=False)
                print(f"✅ Saved: {os.path.dirname(save_path)}")
                print()
                print()

    print(f"---\nAll files processed in {time.strftime('%H:%M:%S', time.gmtime(time.time() - start_time_all))}.\n---\n")

def fix_data_issue():
    # Find all logger folders for all patients and sessions
    logger_folders = get_logger_folders(
        ROOT_DIR,
        SELECTED_PATIENTS,
        SELECTED_SESSIONS,
        SELECTED_LOGGERS,
        mode="Raw"
    )

    for _, session_dir, logger, logger_raw_folder in logger_folders:
        # Find all CSV files in each logger folder
        csv_files = glob.glob(os.path.join(logger_raw_folder, "*.csv"))
        for csv_file in csv_files:
            # Output directory = same as input but with "Fixed_Data" as subfolder
            output_dir = os.path.join(os.path.dirname(csv_file), "Fixed_Data")
            os.makedirs(output_dir, exist_ok=True)
            # Extract date_part from session_dir (expects SessionX_YYYYMMDD format)
            session_folder = os.path.basename(session_dir)
            match = re.search(r"(\d{8})", session_folder)
            if match:
                yyyymmdd = match.group(1)  # e.g., '20250217'
                date_part = yyyymmdd[2:]   # take last 6 chars: '250217'
            else:
                date_part = "unknown"
            # Run the fix
            fix_imu_file(
                input_csv=csv_file,
                output_dir=output_dir,
                date_part=date_part,
                time_of_the_session=TIME_OF_THE_SESSION
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IMU Data Processing Pipeline")
    parser.add_argument('--combineCSV', action='store_true', help='Combine and process logger CSV files')
    parser.add_argument('--fixDataIssue', action='store_true', help='Run data fixing routine')
    args = parser.parse_args()

    if args.combineCSV:
        combine_csv_pipeline()
    elif args.fixDataIssue:
        fix_data_issue()
    else:
        print("No valid argument provided. Use --combineCSV or --fixDataIssue.")
