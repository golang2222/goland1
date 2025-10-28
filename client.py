import requests
import time
import psutil
import pyautogui
import os
import subprocess
import shutil
import tempfile
import platform
import socket
import logging

# Configuration (set these via environment variables or hardcode; use secrets for token/chat_id)
SERVER_URL = "https://api.farhamaghdasi.ir/github-actions/api.php"  # Your hosted PHP server URL
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7526435726:AAFBc6ZyUhN5vxX7HAFRBoOs2uhJehwxPlo')  # From GitHub secrets
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '5296263534')  # From GitHub secrets
BACKUP_FOLDER = "C:\\MyBackupFolder"  # Same as periodic backup
INSTANCE_ID = os.environ.get('GITHUB_RUN_ID', 'unknown')  # Unique per run

# Set up logging
logging.basicConfig(filename='client.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_system_info():
    try:
        # OS and version
        os_info = platform.system() + " " + platform.release()
        
        # IP address (local IP; for public IP, use external service)
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Public IP and location
        ip_response = requests.get('https://ipapi.co/json/')
        ip_data = ip_response.json()
        public_ip = ip_data.get('ip', 'unknown')
        location = f"{ip_data.get('city', 'unknown')}, {ip_data.get('region', 'unknown')}, {ip_data.get('country_name', 'unknown')}"
        
        # RAM
        mem = psutil.virtual_memory()
        ram = f"{mem.total / (1024 ** 3):.2f} GB total, {mem.used / (1024 ** 3):.2f} GB used"
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_info = f"{disk.total / (1024 ** 3):.2f} GB total, {disk.used / (1024 ** 3):.2f} GB used"
        
        return {
            'os': os_info,
            'local_ip': local_ip,
            'public_ip': public_ip,
            'location': location,
            'ram': ram,
            'disk': disk_info
        }
    except Exception as e:
        logging.error(f"Failed to get system info: {e}")
        return {}

def send_to_telegram(file_path=None, caption=None, text=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram token or chat ID missing - skipping send")
        return
    cmd = ['curl.exe', '-F', f'chat_id={TELEGRAM_CHAT_ID}']
    if file_path:
        cmd.extend(['-F', f'document=@{file_path}'])
        if caption:
            cmd.extend(['-F', f'caption={caption}'])
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument'
    else:
        cmd.extend(['-F', f'text={text}'])
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    subprocess.run(cmd + [url])

def register():
    system_info = get_system_info()
    data = {'action': 'register', 'id': INSTANCE_ID}
    data.update(system_info)
    try:
        r = requests.post(SERVER_URL, data=data)
        logging.info(f"Register response: {r.text}")
    except Exception as e:
        logging.error(f"Register failed: {e}")

def heartbeat():
    try:
        r = requests.post(SERVER_URL, data={'action': 'heartbeat', 'id': INSTANCE_ID})
        logging.info(f"Heartbeat response: {r.text}")
    except Exception as e:
        logging.error(f"Heartbeat failed: {e}")

def get_commands():
    try:
        r = requests.get(SERVER_URL, params={'action': 'get_commands', 'id': INSTANCE_ID})
        commands = r.json().get('commands', [])
        logging.info(f"Retrieved commands: {commands}")
        return commands
    except Exception as e:
        logging.error(f"Get commands failed: {e}")
        return []

def clear_command(cmd):
    try:
        r = requests.post(SERVER_URL, data={'action': 'clear_command', 'id': INSTANCE_ID, 'cmd': cmd})
        logging.info(f"Clear command response: {r.text}")
    except Exception as e:
        logging.error(f"Clear command failed: {e}")

def execute_command(cmd):
    logging.info(f"Executing command: {cmd}")
    if cmd == 'backup':
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, f"instant_backup_{timestamp}.zip")
            shutil.make_archive(zip_path[:-4], 'zip', BACKUP_FOLDER)  # make_archive adds .zip
            caption = f"Instant backup for instance {INSTANCE_ID} - {timestamp}"
            send_to_telegram(file_path=zip_path, caption=caption)
            logging.info("Backup sent")
    elif cmd == 'screenshot':
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "screenshot.png")
            pyautogui.screenshot(path)
            caption = f"Screenshot for instance {INSTANCE_ID}"
            send_to_telegram(file_path=path, caption=caption)
            logging.info("Screenshot sent")
    elif cmd == 'status':
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        text = f"Status for instance {INSTANCE_ID}:\nCPU usage: {cpu}%\nRAM usage: {mem.percent}% ({mem.used / (1024 ** 3):.2f} GB used / {mem.total / (1024 ** 3):.2f} GB total)"
        send_to_telegram(text=text)
        logging.info("Status sent")

# Main loop
logging.info("Starting client")
register()
while True:
    heartbeat()
    commands = get_commands()
    for c in commands:
        execute_command(c)
        clear_command(c)

    time.sleep(60)  # Poll every minute
