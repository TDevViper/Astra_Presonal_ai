import psutil
import platform
from typing import Dict


def get_system_info() -> Dict:
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                cpu = proc.info['cpu_percent'] or 0.0
                mem = proc.info['memory_percent'] or 0.0
                processes.append({
                    "name": proc.info['name'],
                    "cpu": round(cpu, 1),
                    "memory": round(mem, 1)
                })
            except:
                pass

        processes = sorted(processes, key=lambda p: p["cpu"], reverse=True)[:5]

        return {
            "success": True,
            "cpu": {
                "percent": round(cpu_percent, 1),
                "count": psutil.cpu_count()
            },
            "memory": {
                "percent": round(memory.percent, 1),
                "used_gb": round(memory.used / (1024**3), 1),
                "total_gb": round(memory.total / (1024**3), 1)
            },
            "disk": {
                "percent": round(disk.percent, 1),
                "free_gb": round(disk.free / (1024**3), 1),
                "total_gb": round(disk.total / (1024**3), 1)
            },
            "platform": platform.system(),
            "top_processes": processes
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_performance() -> str:
    info = get_system_info()
    if not info["success"]:
        return "Couldn't check system status."

    cpu = info["cpu"]["percent"]
    mem = info["memory"]["percent"]
    status = []

    if cpu > 80:
        status.append(f"CPU is high ({cpu}%)")
        if info["top_processes"]:
            top = info["top_processes"][0]
            status.append(f"{top['name']} using {top['cpu']}% CPU")
    elif cpu < 20:
        status.append(f"CPU is idle ({cpu}%)")
    else:
        status.append(f"CPU at {cpu}%")

    if mem > 80:
        status.append(f"Memory high ({mem}%)")
    else:
        status.append(f"Memory at {mem}%")

    disk_free = info["disk"]["free_gb"]
    if disk_free < 10:
        status.append(f"⚠️ Only {disk_free}GB free disk space")

    return " | ".join(status)
