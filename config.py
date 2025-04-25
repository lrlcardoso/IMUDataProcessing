"""
==============================================================================
Title:          Configuration Settings
Description:    Defines global settings for IMU data processing, including
                root directory and which patients, sessions, and loggers
                are to be processed for the VRRehab_UQ-MyTurn project.
Author:         Lucas R. L. Cardoso
Project:        VRRehab_UQ-MyTurn
Date:           2025-04-25
Version:        1.0

Changelog:
    - v1.0: [2025-04-25] Initial release.
==============================================================================
"""

# Path to root data directory
ROOT_DIR = r"C:\Users\s4659771\Documents\MyTurn_Project\Data"

# Patient and session selection (edit as required)
SELECTED_PATIENTS = ["P01","P02"]
SELECTED_SESSIONS = ["Session2"]
SELECTED_LOGGERS = ["Logger1","Logger2"]

# Trim first N minutes from logger data (default: 5)
TRIM_MINUTES = 5
