import subprocess
import os
import sys

def start_services():
    print("🚀 Starting FastAPI backend on port 8000...")
    # Launch FastAPI internally on port 8000
    backend_process = subprocess.Popen([
        "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", "8000"
    ])

    print("🎨 Starting Streamlit frontend on port 7860...")
    # Launch Streamlit on port 7860 (Hugging Face's mandatory public port)
    frontend_process = subprocess.Popen([
        "streamlit", "run", "app.py",
        "--server.port", "7860",
        "--server.address", "0.0.0.0"
    ])

    # Keep the script alive and tracking both processes
    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("Stopping services...")
        backend_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    start_services()