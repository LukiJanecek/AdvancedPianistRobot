from fastapi import APIRouter
import subprocess
import platform
import psutil

router = APIRouter(prefix="/system", tags=["General"])

@router.get("/health")
def health():
    return {"status": "ok", "app": "Ahoj, klavirista!"}


def get_cpu_temperature() -> float:
    try:
        output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8")
        return float(output.replace("temp=", "").replace("'C", "").strip())
    except Exception:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_str = f.read().strip()
            return float(temp_str) / 1000.0

@router.get("/temperature")
def read_temperature():
    temp_c = get_cpu_temperature()
    return {"cpu_temperature_c": temp_c}


@router.get("/info")
def get_system_info():
    return {
        "hostname": platform.node(),
        "os": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "uptime_seconds": psutil.boot_time(), 
    }

@router.get("/disk")
def get_disk_usage():
    usage = psutil.disk_usage("/")
    return {
        "total_gb": usage.total / (1024 ** 3),
        "used_gb": usage.used / (1024 ** 3),
        "free_gb": usage.free / (1024 ** 3),
        "percent": usage.percent,
    }

@router.get("/throttle")
def get_throttle_status():
    try:
        output = subprocess.check_output(["vcgencmd", "get_throttled"]).decode("utf-8")
        hex_val = output.split("=")[1]
        val = int(hex_val, 16)
        return {
            "raw": output,
            "under_voltage": bool(val & 1),
            "freq_capped": bool(val & 2),
            "throttled": bool(val & 4),
            "temp_limit": bool(val & 8),
        }
    except Exception as e:
        return {"error": str(e)}