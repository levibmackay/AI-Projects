import os
import time
import psutil
import requests
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

load_dotenv()

app = FastAPI(title="PiPulse Mission Control")

# Path to static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# State for Network I/O calculation
net_state = {
    "last_bytes_sent": psutil.net_io_counters().bytes_sent,
    "last_bytes_recv": psutil.net_io_counters().bytes_recv,
    "last_time": time.time()
}

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/api/stats")
async def get_stats():
    """Returns core system telemetry including I/O speeds."""
    global net_state
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Calculate Network Speeds (Mbps)
        curr_net = psutil.net_io_counters()
        curr_time = time.time()
        dt = curr_time - net_state["last_time"]
        
        up_speed = (curr_net.bytes_sent - net_state["last_bytes_sent"]) / dt / 125000  # Mbps
        down_speed = (curr_net.bytes_recv - net_state["last_bytes_recv"]) / dt / 125000 # Mbps
        
        net_state = {
            "last_bytes_sent": curr_net.bytes_sent,
            "last_bytes_recv": curr_net.bytes_recv,
            "last_time": curr_time
        }

        # Temperature
        temp = None
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read()) / 1000.0
        elif hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if "cpu-thermal" in temps:
                temp = temps["cpu-thermal"][0].current

        return {
            "cpu": cpu_percent,
            "memory": memory.percent,
            "disk": disk.percent,
            "temp": temp,
            "net_up": round(up_speed, 2),
            "net_down": round(down_speed, 2),
            "uptime": int(time.time() - psutil.boot_time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spotify")
async def get_spotify():
    """Fetches current Spotify playback state."""
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    refresh_token = os.getenv("SPOTIPY_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        return {"status": "unconfigured"}

    try:
        # Simple manual token refresh for headless operation
        auth_url = "https://accounts.spotify.com/api/token"
        resp = requests.post(auth_url, data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        })
        token = resp.json().get("access_token")
        
        sp = spotipy.Spotify(auth=token)
        current = sp.current_playback()
        
        if current and current['item']:
            item = current['item']
            return {
                "status": "playing",
                "title": item['name'],
                "artist": item['artists'][0]['name'],
                "album": item['album']['name'],
                "cover": item['album']['images'][0]['url'],
                "progress": current['progress_ms'],
                "duration": item['duration_ms'],
                "is_playing": current['is_playing']
            }
        return {"status": "idle"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/pihole")
async def get_pihole():
    """Fetches stats from Pi-hole."""
    url = os.getenv("PIHOLE_URL")
    token = os.getenv("PIHOLE_API_TOKEN")

    if not url:
        return {"status": "unconfigured"}

    try:
        full_url = f"{url}?summary&auth={token}"
        resp = requests.get(full_url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "status": "online",
                "queries": data.get("dns_queries_today"),
                "blocked": data.get("ads_blocked_today"),
                "percent": data.get("ads_percentage_today"),
                "unique_clients": data.get("unique_clients")
            }
        return {"status": "offline"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/external")
async def get_external_data():
    """Proxies NASA APOD and Weather."""
    # (Same as before but combined with load_dotenv support)
    nasa_url = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
    weather_url = "https://wttr.in/?format=j1"
    
    data = {"nasa": {}, "weather": {}}
    try:
        nasa_resp = requests.get(nasa_url, timeout=5)
        if nasa_resp.status_code == 200:
            data["nasa"] = nasa_resp.json()
            
        weather_resp = requests.get(weather_url, timeout=5)
        if weather_resp.status_code == 200:
            w_json = weather_resp.json()
            curr = w_json['current_condition'][0]
            data["weather"] = {
                "temp_C": curr['temp_C'],
                "desc": curr['weatherDesc'][0]['value']
            }
    except: pass
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
