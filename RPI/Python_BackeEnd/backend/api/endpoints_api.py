from fastapi import APIRouter
import subprocess

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