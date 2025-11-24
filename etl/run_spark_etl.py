"""
Wrapper script to run Spark ETL job

This script provides a convenient way to run the Spark ETL job
with proper environment setup.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from etl.spark_etl import main

if __name__ == "__main__":
    main()

