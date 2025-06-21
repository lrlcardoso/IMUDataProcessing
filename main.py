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
Version:        1.3
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
    - v1.2: [2025-04-28] Added the option to fix the IMU data (--fixDataIssue).
    - v1.3: [2025-06-21] Added duration check with time formatting before sync,
                         and loggers signal plotting for visual inspection.
==============================================================================
"""

import os
import re
import time
import glob
import shutil
import argparse
import matplotlib.pyplot as plt
from datetime import timedelta
from tqdm import tqdm
from config import (
    ROOT_DIR, SELECTED_PATIENTS, SELECTED_SESSIONS,
    SELECTED_LOGGERS, TRIM_MINUTES, TIME_OF_THE_SESSION
)
from utils.imu_utils import preprocess_logger_folder, synchronize_loggers
from utils.file_utils import get_logger_folders, get_processed_logger_save_path
from utils.data_fixes_utils import fix_imu_file

def format_seconds_hhmmss(seconds):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    millis = int((td.total_seconds() - total_seconds) * 1000)
    return time.strftime("%H:%M:%S", time.gmtime(total_seconds)) + f".{millis:03d}"

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

                # === Duration check BEFORE sync ===
                time_col = "Unix Time"
                MIN_DURATION_SECONDS = 3000
                if time_col in df.columns and not df.empty:
                    start_time = df[time_col].iloc[0]
                    # print(start_time) #for debbuging
                    end_time = df[time_col].iloc[-1]
                    # print(end_time) #for debbuging
                    duration_sec = end_time - start_time
                    if duration_sec < MIN_DURATION_SECONDS:
                        duration_str = format_seconds_hhmmss(duration_sec)
                        print(f"⚠️  [WARNING] {logger} duration is less than 50 minutes: {duration_str}")

                dfs.append(df)
                loggers_for_sync.append((session_dir, logger))


            # Synchronize and save for this patient/session
            if dfs:
                print()
                dfs_sync = synchronize_loggers(dfs)
                # dfs_sync = dfs
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

            # === Generate and save plots ===
            for (session_dir, logger), df_out in zip(loggers_for_sync, dfs_sync):
                save_path = get_processed_logger_save_path(ROOT_DIR, session_dir, logger, mode="Processed")
                output_dir = os.path.dirname(save_path)
                plot_dir = os.path.join(output_dir, "Plots")
                os.makedirs(plot_dir, exist_ok=True)
                plot_path = os.path.join(plot_dir, f"{logger}.png")

                # === Plotting ===
                fig, axes = plt.subplots(3, 3, figsize=(15, 9), sharex=True)
                fig.suptitle(f"{logger} - IMU Signals", fontsize=16)

                signals = {
                    "acc": ["ax", "ay", "az"],
                    "gyro": ["gx", "gy", "gz"],
                    "mag": ["mx", "my", "mz"]
                }

                time_col = "Unix Time"
                if time_col in df_out.columns and not df_out.empty:
                    time_vec = df_out[time_col] - df_out[time_col].iloc[0]
                else:
                    time_vec = range(len(df_out))  # fallback

                for i, (sensor_type, dims) in enumerate(signals.items()):
                    for j, dim in enumerate(dims):
                        ax = axes[i, j]
                        if dim in df_out.columns:
                            ax.plot(time_vec, df_out[dim], linewidth=0.8)
                            ax.set_xlim(0, 3600)
                            ax.set_title(f"{sensor_type.upper()} - {dim}")
                            ax.set_xlabel("Time (s)")
                            ax.grid(True)
                        else:
                            ax.set_title(f"{sensor_type.upper()} - {dim} (missing)")
                            ax.axis("off")

                plt.tight_layout(rect=[0, 0.03, 1, 0.95])
                plt.savefig(plot_path)
                plt.close(fig)


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
        # === Step 1: Move everything into Original_Data_WithIssues ===
        backup_folder = os.path.join(logger_raw_folder, "Original_Data_WithIssues")
        os.makedirs(backup_folder, exist_ok=True)

        for item in os.listdir(logger_raw_folder):
            src_path = os.path.join(logger_raw_folder, item)
            dst_path = os.path.join(backup_folder, item)
            # Skip the backup folder itself
            if os.path.abspath(src_path) == os.path.abspath(backup_folder):
                continue
            shutil.move(src_path, dst_path)

        # === Step 2: Process CSVs inside Original_Data_WithIssues ===
        csv_files = glob.glob(os.path.join(backup_folder, "*.csv"))

        # Extract date_part from session_dir
        session_folder = os.path.basename(session_dir)
        log_path = os.path.join(logger_raw_folder, "00_logfile.txt")
        match = re.search(r"(\d{8})", session_folder)
        if not match:
            with open(log_path, "a") as logf:
                logf.write(f"[ERROR] Invalid session folder name: '{session_folder}' — no date found\n")
            print(f"[SKIP] No date found in session folder: {session_folder}")
            continue

        yyyymmdd = match.group(1)
        date_part = yyyymmdd[2:]  # e.g., '250217'

 
        for csv_file in csv_files:
            output_dir = logger_raw_folder
            fix_imu_file(
                input_csv=csv_file,
                output_dir=output_dir,
                date_part=date_part,
                time_of_the_session=TIME_OF_THE_SESSION,
                log_path=log_path
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
