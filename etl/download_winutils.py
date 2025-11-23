"""
Download winutils.exe for Spark on Windows

This script downloads winutils.exe which is required for Spark to work
on Windows when writing files (like Parquet).
"""

import os
import urllib.request
from pathlib import Path
import sys

def download_winutils():
    """Download winutils.exe for Windows"""
    hadoop_home = Path.home() / ".hadoop"
    hadoop_bin = hadoop_home / "bin"
    hadoop_bin.mkdir(parents=True, exist_ok=True)
    
    winutils_exe = hadoop_bin / "winutils.exe"
    
    if winutils_exe.exists():
        print(f"✓ winutils.exe already exists at: {winutils_exe}")
        print("  Delete it if you want to re-download.")
        return
    
    # Use the winutils from the cdarlint repository
    winutils_url = "https://github.com/cdarlint/winutils/raw/master/hadoop-3.3.6/bin/winutils.exe"
    
    print("Downloading winutils.exe...")
    print(f"  From: {winutils_url}")
    print(f"  To: {winutils_exe}")
    
    try:
        urllib.request.urlretrieve(winutils_url, str(winutils_exe))
        print(f"✓ Successfully downloaded winutils.exe!")
        print(f"  Location: {winutils_exe}")
        
        # Set HADOOP_HOME environment variable
        os.environ["HADOOP_HOME"] = str(hadoop_home)
        print(f"\n✓ Set HADOOP_HOME={hadoop_home}")
        print("\nYou can now run Spark ETL jobs on Windows!")
        
    except Exception as e:
        print(f"✗ Failed to download winutils.exe: {e}")
        print("\nManual download instructions:")
        print("1. Visit: https://github.com/cdarlint/winutils/tree/master/hadoop-3.3.6/bin")
        print("2. Download winutils.exe")
        print(f"3. Save it to: {winutils_exe}")
        sys.exit(1)

if __name__ == "__main__":
    if os.name != "nt":
        print("This script is for Windows only.")
        sys.exit(1)
    
    download_winutils()

