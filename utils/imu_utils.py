"""
==============================================================================
Title:          IMU Data Processing Utilities
Description:    Provides core utility functions for loading, merging, 
                filtering, timestamp-converting, and synchronizing IMU logger 
                data as part of the VRRehab_UQ-MyTurn project.
Author:         Lucas R. L. Cardoso
Project:        VRRehab_UQ-MyTurn
Date:           2025-04-25
Version:        1.0
==============================================================================
Usage:
    Import as a module:
        from utils.imu_utils import preprocess_logger_folder, synchronize_loggers

Dependencies:
    - Python >= 3.x
    - pandas, glob, os, datetime

Changelog:
    - v1.0: [2025-04-25] Initial release
==============================================================================
"""

import os
import glob
import pandas as pd
from tqdm import tqdm
tqdm.pandas()
from datetime import datetime, timezone, timedelta

def combine_csv_files(folder):
    """Combine all CSVs in a folder into a single DataFrame, preserving order."""
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    dfs = []
    for f in tqdm(files, desc=f"🔄 [1/2] Reading CSVs in {os.path.basename(folder)}"):
        df = pd.read_csv(f)
        dfs.append(df)
    combined = pd.concat(dfs, ignore_index=True)
    return combined

def compute_unix_time(row):
    brisbane = timezone(timedelta(hours=10))  # UTC+10
    dt = datetime(
        int(row['g_year'])+2000,
        int(row['g_month']),
        int(row['g_day']),
        int(row['g_hour']),
        int(row['g_minute']),
        int(row['g_second']),
        int(row['g_hund']) * 10000  # hundredths to microseconds
    )
    dt = dt.replace(tzinfo=brisbane)
    return dt.timestamp()  # in seconds (float, includes ms)


def preprocess_logger_folder(raw_logger_folder, trim_minutes=5):
    """Load, merge, process, and trim logger data."""
    df = combine_csv_files(raw_logger_folder)
    
    # Filter by valid == 1
    df = df[df['valid'] == 1].reset_index(drop=True)

    # Filter for valid date fields
    df = df[
        (df['g_year'] >= 25) &
        (df['g_month'] >= 1) & (df['g_month'] <= 12) &
        (df['g_day'] >= 1) & (df['g_day'] <= 31)
    ].reset_index(drop=True)

    # Remove any existing 'Unix Time' column before creating a new one.
    # This avoids duplicate columns (which can cause assignment errors)
    # and ensures that 'Unix Time' is freshly and consistently computed
    # for the current data, even if previously processed CSVs are included.
    if "Unix Time" in df.columns:
        df = df.drop(columns=["Unix Time"])
    # Remove any duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]

    # Compute UNIX time
    tqdm.pandas(desc="🔄 [2/2] Computing Unix Time")
    df['Unix Time'] = df.progress_apply(compute_unix_time, axis=1)

    # Trim first N minutes
    min_time = df['Unix Time'].min()
    trim_time = min_time + (trim_minutes * 60)
    df = df[df['Unix Time'] >= trim_time].reset_index(drop=True)

    # Select required columns
    final_cols = [
        "Unix Time", "ax", "ay", "az", "gx", "gy", "gz", "mx", "my", "mz"
    ]
    df_final = df[final_cols]
    return df_final


def synchronize_loggers(dfs):
    """Crop all dfs to the common time window across all loggers."""
    start = max(df['Unix Time'].min() for df in dfs)
    end = min(df['Unix Time'].max() for df in dfs)
    synced = []
    for df in dfs:
        df_sync = df[(df['Unix Time'] >= start) & (df['Unix Time'] <= end)].reset_index(drop=True)
        synced.append(df_sync)
    return synced
