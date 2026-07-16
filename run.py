import subprocess
import sys
import time

def start_services():
    # 1. Start FastAPI backend
    print("🚀 Starting FastAPI backend on port 8000...")
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"
    ])

    # Give the backend a couple of seconds to boot up
    time.sleep(3)

    # 2. Start Streamlit frontend
    print("🎨 Starting Streamlit frontend on port 7860...")
    frontend_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "7860", "--server.address", "0.0.0.0"
    ])

    # Keep the orchestrator alive while both processes run
    backend_process.wait()
    frontend_process.wait()

if __name__ == "__main__":
    start_services()