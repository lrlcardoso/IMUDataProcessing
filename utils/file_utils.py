"""
==============================================================================
Title:          IMU Data Path Finder
Description:    Utility functions to dynamically construct and locate
                IMU logger folders for Raw/Processed data structures,
                removing hardcoded folder names from main scripts.
Author:         Lucas R. L. Cardoso
Project:        VRRehab_UQ-MyTurn
Date:           2025-04-25
Version:        1.0
==============================================================================
Usage:
    from utils.file_utils import get_logger_folders

Dependencies:
    - Python >= 3.x
    - Required libraries: os, glob

Changelog:
    - v1.0: [2025-04-25] Initial release
==============================================================================
"""

import os
import glob

# These constants are only here so you can change folder names in ONE place.
RAW_FOLDER = "Raw"
PROCESSED_FOLDER = "Processed"
WMORE_FOLDER = "WMORE"

def get_logger_folders(
    root_dir, patients, sessions, logger_names, mode="Raw"
):
    """
    Returns the absolute paths to all specified logger folders for given
    patients and sessions, for either Raw or Processed data.

    Parameters:
    - root_dir: str, e.g. C:/path/to/Data
    - patients: list of str, e.g. ["P01"]
    - sessions: list of str, e.g. ["Session2"]
    - logger_names: list of str, e.g. ["Logger1", "Logger2"]
    - mode: str, either "Raw" or "Processed"

    Returns:
    - logger_folders: list of (patient, session_dir, logger, logger_folder_path)
    """
    logger_folders = []
    if mode not in [RAW_FOLDER, PROCESSED_FOLDER]:
        raise ValueError(f"mode must be '{RAW_FOLDER}' or '{PROCESSED_FOLDER}'")
    for patient in patients:
        patient_path = os.path.join(root_dir, mode, patient)
        if not os.path.exists(patient_path):
            continue
        # Example: Session2_20250210
        for session in sessions:
            session_dirs = glob.glob(os.path.join(patient_path, f"{session}_*"))
            for session_dir in session_dirs:
                wmore_path = os.path.join(session_dir, WMORE_FOLDER)
                if not os.path.exists(wmore_path):
                    continue
                for logger in logger_names:
                    logger_folder = os.path.join(wmore_path, logger)
                    if os.path.exists(logger_folder):
                        logger_folders.append(
                            (patient, session_dir, logger, logger_folder)
                        )
    return logger_folders

def get_processed_logger_save_path(root_dir, session_dir, logger, mode="Processed"):
    """
    Returns the output path for the processed logger CSV,
    using the same session_dir base as found in the raw folder.
    """
    rel = os.path.relpath(session_dir, os.path.join(root_dir, RAW_FOLDER))
    processed_session_dir = os.path.join(root_dir, mode, rel, WMORE_FOLDER)
    os.makedirs(processed_session_dir, exist_ok=True)
    save_path = os.path.join(processed_session_dir, f"{logger}.csv")
    return save_path
