import threading
import subprocess
import os
import time

def run_api():
    port = os.getenv("PORT", "8080")
    subprocess.run([
        "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", port
    ])

def run_bot():
    subprocess.run(["python", "bot.py"])

threading.Thread(target=run_api).start()
threading.Thread(target=run_bot).start()

while True:
    time.sleep(60)
