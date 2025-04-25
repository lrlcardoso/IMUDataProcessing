"""
==============================================================================
Title:          IMU Data Processing Main
Description:    Entry point for IMU logger data processing pipeline. Loads,
                merges, trims, synchronizes, and saves processed logger CSVs
                for all selected patients/sessions/loggers, using centralized
                file/folder utilities.
Author:         Lucas R. L. Cardoso
Project:        VRRehab_UQ-MyTurn
Date:           2025-04-25
Version:        1.0
==============================================================================
Usage:
    python main.py

Dependencies:
    - Python >= 3.x
    - pandas, glob, os
    - Local modules: config.py, utils.imu_utils, utils.file_utils

Changelog:
    - v1.0: Initial release.
==============================================================================
"""

import os
import time
from tqdm import tqdm
from config import (
    ROOT_DIR, SELECTED_PATIENTS, SELECTED_SESSIONS,
    SELECTED_LOGGERS, TRIM_MINUTES
)
from utils.imu_utils import preprocess_logger_folder, synchronize_loggers
from utils.file_utils import get_logger_folders, get_processed_logger_save_path

def main():

    start_time_all = time.time()

    for patient in SELECTED_PATIENTS:
        for session in SELECTED_SESSIONS:
            # Find all loggers for this patient and session
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

if __name__ == "__main__":
    main()
