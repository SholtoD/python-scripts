This tool provides a simple GUI application for processing web archive files. It allows you to:

Extract .wacz files (Web Archive Collections)
Decompress and validate embedded .warc.gz files
Merge extracted .warc files into a central location
Optionally clean up processed files

It is designed to streamline workflows for web archiving, digital preservation, and analysis tasks.

Features

✅ Extracts .wacz (ZIP-based) archive files

✅ Decompresses .warc.gz files into .warc format

✅ Validates WARC files using warcio

✅ Merges extracted WARCs into a single folder per collection

✅ Skips already-processed files automatically

✅ Optional cleanup (delete processed WACZ files)

✅ GUI with progress bar, status updates, and logging

✅ Exportable processing log


Requirements

Python Version
Python 3.8+ recommended

Dependencies

Install required packages:
pip install ttkbootstrap warcio

Built-in modules used
os, zipfile, gzip, shutil, threading, logging, time
tkinter (included with most Python installs)


Installation

Clone or download the script:
git clone <repo-url>
cd <project-folder>


Install dependencies:
pip install ttkbootstrap warcio


Run the script:
python your_script_name.py


Usage
1. Launch the Application
  Running the script opens a GUI window.

2. Select Input Folder

  Click Browse
  Choose a directory containing:
  .wacz files, OR
  subfolders containing .wacz files

3. Configure Options
  ✅ Optional: Enable
  "Delete WACZs after successful processing"

4. Start Processing
  Click Start
  Monitor:
  Progress bar
  Status updates (including ETA)
  Log output in real-time

5. Cancel (Optional)
  Click Cancel to stop processing safely

6. Export Log
  Click Save Log to export the processing log as a .txt file
