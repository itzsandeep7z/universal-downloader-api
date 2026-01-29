import threading
import subprocess

def run_api():
    subprocess.run([
        "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "8080"
    ])

def run_bot():
    subprocess.run(["python", "bot.py"])

threading.Thread(target=run_api).start()
threading.Thread(target=run_bot).start()
