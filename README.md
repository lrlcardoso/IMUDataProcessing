# RehabTrack_Workflow – IMU Data Processing

This is part of the [RehabTrack_Workflow](https://github.com/lrlcardoso/RehabTrack_Workflow): a modular Python pipeline for **tracking and analysing physiotherapy movements**, using video and IMU data.  
This module automates the preprocessing of IMU logger CSV data collected during experimental sessions, preparing it for subsequent synchronisation and analysis.

---

## 📌 Overview

This module performs:
- **Merging** of chunked IMU CSV files by logger and session
- **Conversion** of global time columns to UNIX timestamps (specify TZ)
- **Trimming** of the first N minutes of each logger’s data
- **Alignment** of multiple loggers to a common time window  
- **Saving** processed files in a mirrored folder structure under a `Processed` directory

**Inputs:**
- Raw IMU CSV files exported from loggers
- Configuration file (`config.py`) specifying:
  - Root directory
  - Patients and sessions to process
  - Loggers to include
  - Timezone and trim duration

**Outputs:**
- Processed CSV files in a `Processed` directory
- All loggers aligned to a common time window

---

## 📂 Repository Structure

```
IMU_Data_Processing/
├── main.py                   # Main entry point
├── config.py                 # Configurable parameters & paths
├── utils/                    # Helper modules for processing and fixing IMU data
│   ├── data_fixes_utils.py    # Functions to detect and fix timestamp/data issues
│   ├── file_utils.py          # File handling, merging, and organisation utilities
│   ├── helper_functions.py    # General-purpose helper functions
│   └── imu_utils.py           # IMU-specific processing utilities
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

---

## 🛠 Installation

```bash
git clone https://github.com/yourusername/IMU_Data_Processing.git
cd IMU_Data_Processing
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🚀 Usage

Run the desired preprocessing step using the available commands:

1️⃣ **Combine and process** logger CSVs (from WMORE output)  
```bash
python main.py --combineCSV
```
Merges chunked CSV files, trims the first N minutes, converts timestamps, and aligns loggers to a common time window.  

2️⃣ **Check data quality**  
```bash
python main.py --checkData
```
Visually inspect and analyse the processed CSVs for sampling rate consistency, time gaps, and total duration.  

3️⃣ **(Optional) Fix data issues**  
```bash
python main.py --fixDataIssue
```
Repair logger files if data corruption or timestamp irregularities are detected.  

**Inputs:**  
- Raw IMU logger CSV files for each patient/session/logger  

**Outputs:**  
- Merged and processed CSV files in the `Processed` folder  
- Time‑synchronised data across all selected loggers  


---

## 📖 Citation

If you use this module in your research, please cite:
```
Cardoso, L. R. L. (2025). RehabTrack_Workflow. 
GitHub. https://doi.org/XXXX/zenodo.XXXXX
```

---

## 📝 License

Code: [MIT License](LICENSE)  
Documentation & figures: [CC BY 4.0](LICENSE-docs)

---

## 🤝 Acknowledgments

- pandas, NumPy  
- datetime, zoneinfo  
