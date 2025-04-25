# MyTurn IMU Data Preprocessing

This tool automates the preprocessing of IMU logger CSV data collected during experimental sessions. It merges chunked CSVs, computes UNIX timestamps, trims the first N minutes, synchronizes time windows across multiple loggers, and saves processed files.

## How It Works

1. **Combines** all logger CSVs for each session and logger.
2. **Converts** global time columns into UNIX time (Brisbane TZ).
3. **Trims** the first 5 minutes of each logger's data.
4. **Synchronizes** all selected loggers to a common time window.
5. **Saves** processed data to the same folder structure as original, but in a `Processed` directory.

## Config

Modify `config.py` to set the root directory, patients, sessions, loggers, timezone, and other options.

## Usage

```bash
python main.py
