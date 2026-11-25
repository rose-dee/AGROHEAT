"""Jalankan backend penerima data ESP32:  python run_api.py"""
import sys
from services.api_service import run_server

if __name__ == "__main__":
    run_server(port=int(sys.argv[1]) if len(sys.argv) > 1 else None)
