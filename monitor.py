import yaml
import requests
from rich.console import Console
from rich.table import Table
from prometheus_client import start_http_server, Gauge
import time
import threading

# --------------------------
# Setup 
https://chatgpt.com/share/68a7ff6b-2e1c-8012-8747-526de70196b8
# --------------------------
console = Console()

# Carregar configuração
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

services = config["services"]
latency_threshold = config["thresholds"]["latency_seconds"]

# Métricas Prometheus
g_service_up = Gauge("service_up", "Service UP status", ["name"])
g_service_latency = Gauge("service_latency_seconds", "Service latency in seconds", ["name"])
g_service_status = Gauge("service_status_code", "HTTP status code", ["name"])

# --------------------------
# Função de monitoramento
# --------------------------
def check_service(service):
    name = service["name"]
    url = service["url"]
    status = "UNKNOWN"
    latency = None
    code = None
    try:
        start = time.time()
        response = requests.get(url, timeout=latency_threshold)
        latency = round(time.time() - start, 3)
        code = response.status_code

        if code == 200 and latency <= latency_threshold:
            status = "UP"
        elif code == 200 and latency > latency_threshold:
            status = "DEGRADED"
        else:
            status = "DOWN"

    except requests.exceptions.Timeout:
        status = "TIMEOUT"
        latency = latency_threshold
        code = 0
    except Exception:
        status = "DOWN"
        latency = 0
        code = 0

    # Atualiza métricas Prometheus
    g_service_up.labels(name=name).set(1 if status=="UP" else 0)
    g_service_latency.labels(name=name).set(latency)
    g_service_status.labels(name=name).set(code)

    return {"name": name, "status": status, "latency": latency, "code": code}

# --------------------------
# Função de exibição no terminal
# --------------------------
def display_dashboard(results):
    table = Table(title="InfraGuard - Monitoramento HTTPBin")
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("HTTP Code", style="yellow")
    table.add_column("Latency (s)", style="green")

    for r in results:
        if r["status"] == "UP":
            status_style = "[bold green]UP[/bold green]"
        elif r["status"] == "DEGRADED":
            status_style = "[bold yellow]DEGRADED[/bold yellow]"
        elif r["status"] == "DOWN":
            status_style = "[bold red]DOWN[/bold red]"
        else:
            status_style = "[bold red]TIMEOUT[/bold red]"
        table.add_row(r["name"], status_style, str(r["code"]), str(r["latency"]))
    
    console.clear()
    console.print(table)

# --------------------------
# Loop principal
# --------------------------
def monitor_loop():
    while True:
        results = [check_service(s) for s in services]
        display_dashboard(results)
        time.sleep(5)

# --------------------------
# Start Prometheus server
# --------------------------
def start_prometheus():
    start_http_server(8000)
    console.print("[bold blue]Prometheus metrics available at http://localhost:8000/metrics[/bold blue]")

# --------------------------
# Main
# --------------------------
if __name__ == "__main__":
    threading.Thread(target=start_prometheus, daemon=True).start()
    monitor_loop()
