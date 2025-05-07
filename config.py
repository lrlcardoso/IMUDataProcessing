"""
==============================================================================
Title:          Configuration Settings
Description:    Defines global settings for IMU data processing, including
                root directory and which patients, sessions, and loggers
                are to be processed for the VRRehab_UQ-MyTurn project.
Author:         Lucas R. L. Cardoso
Project:        VRRehab_UQ-MyTurn
Date:           2025-04-25
Version:        1.1

Changelog:
    - v1.0: [2025-04-25] Initial release.
    - v1.1: [2025-04-28] Added the variable TIME_OF_THE_SESSION.
==============================================================================
"""

# Path to root data directory
ROOT_DIR = r"C:\Users\s4659771\Documents\MyTurn_Project\Data"

# Patient and session selection (edit as required)
SELECTED_PATIENTS = ["P05"]
SELECTED_SESSIONS = ["Session1"]
SELECTED_LOGGERS = ["Logger3"]

# Trim first N minutes from logger data (default: 5)
TRIM_MINUTES = 5

TIME_OF_THE_SESSION = 10   # or whatever the true session hour is (int, 24h format)
