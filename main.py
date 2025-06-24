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
Version:        1.4
==============================================================================
Usage:
    Typical processing workflow:

        1. Combine and process logger CSVs (from WMORE output):
            python main.py --combineCSV

        2. Visually inspect and analyze final CSVs (sampling rate, gaps, duration):
            python main.py --checkData

        3. (Optional) Fix logger files if data corruption or timing issues are detected:
            python main.py --fixDataIssue

    This pipeline consolidates raw multi-part WMORE logger files, ensures 
    consistent timestamps based on `l_*` time fields, and provides diagnostics
    through visual plots and summary tables.

Dependencies:
    - Python >= 3.x
    - pandas, numpy, glob, os, argparse, matplotlib, pytz, tqdm
    - Local modules: config.py, utils.imu_utils, utils.file_utils, utils.data_fixes_utils

Changelog:
    - v1.0: Initial release.
    - v1.1: [2025-04-25] Added argument parsing for pipeline modes.
    - v1.2: [2025-04-28] Added the option to fix the IMU data (--fixDataIssue).
    - v1.3: [2025-06-21] Added duration check with time formatting before sync,
                         and loggers signal plotting for visual inspection.
    - v1.4: [2025-06-24] Rewrote g_time reconstruction using l_time; added checkData()
==============================================================================
"""

import os
import re
import time
import glob
import pytz
import shutil
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
from tqdm import tqdm
from config import (
    ROOT_DIR, SELECTED_PATIENTS, SELECTED_SESSIONS,
    SELECTED_LOGGERS, TRIM_MINUTES, TIME_OF_THE_SESSION
)
from utils.imu_utils import preprocess_logger_folder, synchronize_loggers
from utils.file_utils import get_logger_folders, get_processed_logger_save_path
from utils.data_fixes_utils import fix_imu_file

def unix_to_brisbane(unix_ts):
    brisbane_tz = pytz.timezone("Australia/Brisbane")
    return datetime.fromtimestamp(unix_ts, tz=pytz.utc).astimezone(brisbane_tz).strftime("%Y-%m-%d %H:%M:%S")

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
    
        # The remainder of this function reconstructs the CSVs so that timestamp fields
        # are based on local time (`l_*` columns). The previous implementation relied on
        # global time (`g_*` columns), but this proved unreliable due to instability and
        # frequent timing gaps in the data. Using local time ensures more consistent and
        # gap-free reconstruction of the temporal sequence.
        files = sorted(glob.glob(os.path.join(logger_raw_folder, "*.csv")))
        for f in tqdm(files, desc=f"🔄 Re-organizing CSVs in {os.path.basename(logger_raw_folder)}"):
            df = pd.read_csv(f)

            # Skip last row becaue it is most of the times corrupted
            df = df.iloc[:-1]

            time_cols = ["g_year", "g_month", "g_day", "g_hour", "g_minute", "g_second", "g_hund"]

            # Find first valid row with all g_ time values non-zero
            non_zero_mask = (df[time_cols] != 0).any(axis=1)
            if not non_zero_mask.any():
                continue

            first_valid_idx = non_zero_mask.idxmax()

            # Warn if the first valid g_hund is 99
            if df.loc[first_valid_idx, "g_hund"] == 99:
                print(f"⚠️  Warning: {os.path.basename(f)} starts at g_hund == 99 (line {first_valid_idx})")

            # Initialize columns
            new_g_hund = df["g_hund"].copy()
            new_g_second = df["g_second"].copy()
            new_g_minute = df["g_minute"].copy()
            new_g_hour = df["g_hour"].copy()

            # Set 0s before the valid time
            new_g_hund.iloc[:first_valid_idx] = 0
            new_g_second.iloc[:first_valid_idx] = 0
            new_g_minute.iloc[:first_valid_idx] = 0
            new_g_hour.iloc[:first_valid_idx] = 0

            # Start from known values at the first valid row
            current_g_hund = df.loc[first_valid_idx, "g_hund"]
            current_g_second = df.loc[first_valid_idx, "g_second"]
            current_g_minute = df.loc[first_valid_idx, "g_minute"]
            current_g_hour = df.loc[first_valid_idx, "g_hour"]
            prev_l_hund = df.loc[first_valid_idx, "l_hund"]

            valid_rows = [*range(first_valid_idx + 1)]  # keep all rows up to and including the first valid one

            for i in range(first_valid_idx + 1, len(df)):
                next_l_hund = df.loc[i, "l_hund"]
                raw_delta = (next_l_hund - prev_l_hund) % 100
                time_delta = raw_delta / 100.0  # in seconds

                if time_delta > 0.05:
                    
                    l_hund = df.loc[i, "l_hund"]
                    l_second = df.loc[i, "l_second"]
                    l_minute = df.loc[i, "l_minute"]
                    g_hour = df.loc[i, "g_hour"]
                    g_minute = df.loc[i, "g_minute"]
                    g_second = df.loc[i, "g_second"]

                    if (l_minute == g_hour and l_second == g_minute and l_hund == g_second):
                    
                        raw_delta = 1  # force counting with +1

                next_g_hund = (current_g_hund + raw_delta) % 100

                # Check for g_hund wraparound
                if next_g_hund < current_g_hund:
                    current_g_second += 1
                    if current_g_second >= 60:
                        current_g_second = 0
                        current_g_minute += 1
                        if current_g_minute >= 60:
                            current_g_minute = 0
                            current_g_hour += 1
                            if current_g_hour >= 24:
                                current_g_hour = 0

                current_g_hund = next_g_hund
                prev_l_hund = next_l_hund

                # Assign updated values
                new_g_hund.iloc[i] = current_g_hund
                new_g_second.iloc[i] = current_g_second
                new_g_minute.iloc[i] = current_g_minute
                new_g_hour.iloc[i] = current_g_hour

                valid_rows.append(i)

            # Update DataFrame
            df["g_hund"] = new_g_hund
            df["g_second"] = new_g_second
            df["g_minute"] = new_g_minute
            df["g_hour"] = new_g_hour

            # Copy into local columns
            df["l_hour"] = df["g_hour"]
            df["l_minute"] = df["g_minute"]
            df["l_second"] = df["g_second"]
            df["l_hund"] = df["g_hund"]

            # Copy date values from first valid row to all l_year/month/day
            first_valid_row = df.loc[first_valid_idx]
            df["l_year"] = first_valid_row["g_year"]
            df["l_month"] = first_valid_row["g_month"]
            df["l_day"] = first_valid_row["g_day"]

            df = df.iloc[valid_rows]

            output_folder = os.path.join(logger_raw_folder, "Fixed_Data")
            os.makedirs(output_folder, exist_ok=True)

            output_path = os.path.join(output_folder, os.path.basename(f))
            df.to_csv(output_path, index=False)

def checkData():
    for patient in SELECTED_PATIENTS:
        for session in SELECTED_SESSIONS:
            session_root = os.path.join(ROOT_DIR, "Processed", patient)
            session_dirs = glob.glob(os.path.join(session_root, f"{session}_*"))

            for session_dir in session_dirs:
                wmore_folder = os.path.join(session_dir, "WMORE")
                if not os.path.exists(wmore_folder):
                    continue

                print("=" * 100)
                print(f"📝 Processing: {patient} | {os.path.basename(session_dir)}")
                print("=" * 100)

                if SELECTED_LOGGERS is None:
                    csv_files = sorted(glob.glob(os.path.join(wmore_folder, "Logger*.csv")))
                else:
                    csv_files = [
                        os.path.join(wmore_folder, f"{logger}.csv")
                        for logger in SELECTED_LOGGERS
                        if os.path.exists(os.path.join(wmore_folder, f"{logger}.csv"))
                    ]

                summary_rows = []

                for csv_path in csv_files:
                    logger_name = os.path.splitext(os.path.basename(csv_path))[0]
                    print()

                    df = pd.read_csv(csv_path)
                    if df.empty or "Unix Time" not in df.columns:
                        print(f"⚠️ Skipping {logger_name}: No data or missing 'Unix Time'")
                        continue

                    unix_start = df["Unix Time"].iloc[0]
                    unix_end = df["Unix Time"].iloc[-1]
                    num_points = len(df)

                    # Convert to Brisbane timestamps
                    ts_start = unix_to_brisbane(unix_start)
                    ts_end = unix_to_brisbane(unix_end)

                    duration = unix_end - unix_start
                    expected_points = duration * 100  # 100 Hz
                    error_percent = 100.0 * (1 - (num_points / expected_points)) if expected_points > 0 else 0.0

                    # --- Detect highest gap ---
                    time_diffs = np.diff(df["Unix Time"].values)
                    
                    # for the max
                    max_gap = np.max(time_diffs) if len(time_diffs) > 0 else 0
                    max_gap_points = int(round(max_gap / 0.01)) - 1  # number of missing points
                    # for the second max:
                    # if len(time_diffs) > 1:
                    #     second_max_gap = np.sort(time_diffs)[-2]
                    # else:
                    #     second_max_gap = 0
                    # max_gap_points = max(int(round(second_max_gap / 0.01)) - 1, 0)
                    
                    max_gap_points = max(max_gap_points, 0)  # clamp to zero

                    summary_rows.append({
                        "Logger": logger_name,
                        "Start Time": ts_start,
                        "End Time": ts_end,
                        "Num Points": num_points,
                        "Expected Points": int(expected_points),
                        "Error (%)": round(error_percent, 3),
                        "Max Gap (pts)": max_gap_points
                    })

                    print(f"📂 {logger_name} - done")

                    
                    # --- Extract actual times ---
                    time_values = df["Unix Time"].values
                    time_diffs = np.diff(time_values)
                    sample_indices = np.arange(len(time_values))

                    # --- Generate ideal 100Hz trace over same Unix time range ---
                    start_unix = time_values[0]
                    end_unix = time_values[-1]
                    ideal_time = np.arange(start_unix, end_unix, 0.01)
                    ideal_indices = np.arange(len(ideal_time))

                    # --- Plot ---
                    fig, ax1 = plt.subplots(figsize=(10, 5))

                    # Left Y-axis: sample index
                    ax1.plot(time_values, sample_indices, label="Actual Samples", linewidth=0.8)
                    ax1.plot(ideal_time, ideal_indices, label="Ideal (100 Hz)", linestyle="--", color="red")
                    ax1.set_xlabel("Unix Time (s)")
                    ax1.set_ylabel("Sample Index")
                    ax1.grid(True)
                    ax1.legend(loc="upper left")

                    # Right Y-axis: Δ Unix Time between points
                    ax2 = ax1.twinx()
                    ax2.plot(time_values[1:], time_diffs, label="Δ Unix Time", color="green", alpha=0.6)
                    ax2.set_ylabel("Δ Time (s)", color="green")
                    ax2.tick_params(axis='y', labelcolor='green')
                    ax2.axhline(0.01, color="gray", linestyle="--", linewidth=0.5)

                    # Save plot
                    plt.title(f"{logger_name} - Time Progression & Sampling Gaps")
                    plot_path = os.path.join(wmore_folder, "Plots", f"{logger_name}_time.png")
                    plt.tight_layout()
                    plt.savefig(plot_path)
                    plt.close(fig)

                # Save summary CSV
                if summary_rows:
                    df_summary = pd.DataFrame(summary_rows)
                    summary_path = os.path.join(wmore_folder, "00_logger_summary.csv")
                    df_summary.to_csv(summary_path, index=False)
                    print()
                    print(f"✅ Summary saved to: {summary_path}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IMU Data Processing Pipeline")
    parser.add_argument('--combineCSV', action='store_true', help='Combine and process logger CSV files')
    parser.add_argument('--fixDataIssue', action='store_true', help='Run data fixing routine')
    parser.add_argument('--checkData', action='store_true', help='Run data checking and generate summary table')
    args = parser.parse_args()

    if args.combineCSV:
        combine_csv_pipeline()
    elif args.fixDataIssue:
        fix_data_issue()
    elif args.checkData:
        checkData()
    else:
        print("No valid argument provided. Use --combineCSV, --fixDataIssue or --checkData.")
