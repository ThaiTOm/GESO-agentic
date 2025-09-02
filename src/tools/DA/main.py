#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path

def main():
    try:
        # Run streamlit app
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--theme.base", "light",
            "--theme.primaryColor", "#1f77b4"
        ])
    except KeyboardInterrupt:
        print("\n Dashboard stopped.")
    except Exception as e:
        print(f" Error starting dashboard: {e}")

if __name__ == "__main__":
    main()
