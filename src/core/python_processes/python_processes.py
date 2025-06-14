""" -------------------- HEADERS -------------------- """

import sys
import os
import time
sys.path.append('../')
from pathlib import Path
from src.core.python_processes.enums import ProcessType
from src.config.json_script import rule_loader
import psutil
import orjson
from datetime import datetime

""" -------------------- HEADERS -------------------- """

""" --------------------- GLOBAL VAR -----------------"""

rules = rule_loader()

""" --------------------- GLOBAL VAR -----------------"""

""" -------------------- FUNCTIONS -------------------- """

def getProcessesWithParent() -> dict:
    data = {}
    parent_name_cache = {}

    for proc in psutil.process_iter(attrs=['pid', 'ppid', 'name', 'status', 'exe']):
        try:
            info = proc.info
            ppid = info['ppid']

            if ppid not in parent_name_cache:
                try:
                    parent_name_cache[ppid] = psutil.Process(ppid).name().removesuffix('.exe')
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    parent_name_cache[ppid] = "unknown"

            parent_name = parent_name_cache[ppid]
            parent_key = f"parent_{ppid}_{parent_name}"
            child_key = f"child_{info['pid']}"
            parent_dict = data.setdefault(parent_key, {})
            parent_dict[child_key] = {
                "name": info['name'],
                "status": info['status'],
                "path": info['exe'],
                "process_type": get_process_category(info['exe'])
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
            continue

    return data


def display_process_tree(process_dict, indent=0):
    for parent_pid, children in process_dict.items():
        print("    " * indent + f"{parent_pid}: {{")
        for child_pid, info in children.items():
            print("    " * (indent + 1) + f"{child_pid}: {{")
            for key, value in info.items():
                print("    " * (indent + 2) + f'"{key}": {repr(value)}')
            print("    " * (indent + 1) + "},")
        print("    " * indent + "},")

def monitor_system_to_json(log_interval=2, duration=10, output_path='./output/process_log.json'):
    log_data = []
    start_time = time.time()

    while time.time() - start_time < duration:
        timestamp = datetime.now().isformat()
        snapshot = []

        for proc in psutil.process_iter(['pid', 'name','cpu_percent', 'memory_info']):
            try:
                cpu = proc.cpu_percent(interval=0)
                mem = proc.info['memory_info'].rss / (1024 * 1024) # MB
                snapshot.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu_percent': round(cpu, 2),
                    'memory_mb': round(mem, 2)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        log_data.append({
            'timestamp': timestamp,
            'processes': snapshot
        })

        time.sleep(log_interval)
        with open(output_path, 'wb') as f:
            f.write(orjson.dumps(log_data))



def get_process_category(path: str) -> ProcessType:
    if not path:
        return ProcessType.PROCESS_CATEGORY_SYSTEM

    path = path.lower()

    for sys_path in rules["system_paths"]:
        if sys_path in path:
            return ProcessType.PROCESS_CATEGORY_SYSTEM

    return ProcessType.PROCESS_CATEGORY_APP


""" -------------------- FUNCTIONS -------------------- """
