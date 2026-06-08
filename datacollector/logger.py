import json
import os
from datetime import datetime

LOG_DIR = "ops_logs"


def _ensure_log_dir(project_dir):
    log_dir = os.path.join(project_dir, LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def log_operation(project_dir, action, detail=""):
    log_dir = _ensure_log_dir(project_dir)
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{date_str}.log")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {"timestamp": ts, "action": action, "detail": detail}
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_logs(project_dir, date_filter=None, action_filter=None):
    log_dir = _ensure_log_dir(project_dir)
    entries = []
    for fname in sorted(os.listdir(log_dir)):
        if not fname.endswith(".log"):
            continue
        if date_filter and date_filter not in fname:
            continue
        with open(os.path.join(log_dir, fname), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if action_filter and action_filter not in entry.get("action", ""):
                    continue
                entries.append(entry)
    return entries
