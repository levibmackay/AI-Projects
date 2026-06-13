// PiPulse Mission Control // Core Logic

async function updateAll() {
    updateStats();
    updateSpotify();
    updatePihole();
}

async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        // Core Gauges
        updateGauge('cpu-widget', data.cpu);
        updateGauge('mem-widget', data.memory);
        updateGauge('disk-widget', data.disk);
        updateGauge('temp-widget', data.temp, 85);

        // I/O Speeds
        document.getElementById('net-up').innerText = data.net_up.toFixed(2);
        document.getElementById('net-down').innerText = data.net_down.toFixed(2);

        // Uptime
        const hours = Math.floor(data.uptime / 3600);
        const mins = Math.floor((data.uptime % 3600) / 60);
        const secs = data.uptime % 60;
        document.getElementById('uptime').innerText = `UPTIME: ${String(hours).padStart(2,'0')}:${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;

    } catch (err) { console.error("Stats Error:", err); }
}

async function updateSpotify() {
    try {
        const response = await fetch('/api/spotify');
        const data = await response.json();
        const panel = document.getElementById('spotify-panel');

        if (data.status === 'playing') {
            document.getElementById('spotify-title').innerText = data.title;
            document.getElementById('spotify-artist').innerText = `${data.artist} // ${data.album}`;
            document.getElementById('spotify-art').style.backgroundImage = `url(${data.cover})`;
            document.getElementById('spotify-art').style.backgroundSize = 'cover';
            
            const progress = (data.progress / data.duration) * 100;
            document.getElementById('spotify-bar').style.width = `${progress}%`;
            panel.classList.remove('unconfigured');
        } else if (data.status === 'unconfigured') {
            document.getElementById('spotify-title').innerText = "LINK_REQUIRED";
            document.getElementById('spotify-artist').innerText = "CHECK_.ENV_FILE";
            panel.classList.add('unconfigured');
        } else {
            document.getElementById('spotify-title').innerText = "IDLE";
            document.getElementById('spotify-artist').innerText = "NO_STREAM_DETECTED";
            document.getElementById('spotify-bar').style.width = `0%`;
        }
    } catch (err) { console.error("Spotify Error:", err); }
}

async function updatePihole() {
    try {
        const response = await fetch('/api/pihole');
        const data = await response.json();
        
        if (data.status === 'online') {
            document.getElementById('pi-queries').innerText = data.queries.toLocaleString();
            document.getElementById('pi-blocked').innerText = data.blocked.toLocaleString();
            document.getElementById('pi-percent').innerText = `${data.percent}%`;
            document.getElementById('pi-bar').style.width = `${data.percent}%`;
        } else if (data.status === 'unconfigured') {
            document.getElementById('pi-queries').innerText = "OFFLINE";
        }
    } catch (err) { console.error("Pi-hole Error:", err); }
}

async function updateExternal() {
    try {
        const response = await fetch('/api/external');
        const data = await response.json();

        if (data.nasa && data.nasa.url) {
            document.getElementById('nasa-bg').style.backgroundImage = `url(${data.nasa.url})`;
            document.getElementById('nasa-title').innerText = data.nasa.title.toUpperCase();
        }

        if (data.weather) {
            document.getElementById('weather-data').innerText = `${data.weather.temp_C}°C // ${data.weather.desc.toUpperCase()}`;
        }
    } catch (err) { console.error("External Error:", err); }
}

function updateGauge(id, value, max = 100) {
    const container = document.getElementById(id);
    if (!container) return;
    const fill = container.querySelector('.fill');
    const label = container.querySelector('.value');
    
    const percent = Math.min((value / max) * 100, 100);
    fill.style.width = `${percent}%`;
    
    if (id === 'temp-widget') {
        label.innerText = `${Math.round(value)}°C`;
    } else {
        label.innerText = `${Math.round(value)}%`;
    }

    if (percent > 85) fill.style.background = 'var(--neon-pink)';
    else fill.style.background = 'var(--accent)';
}

function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString('en-US', { hour12: false });
}

// Initialization
setInterval(updateStats, 1000);
setInterval(updateSpotify, 3000);
setInterval(updatePihole, 10000);
setInterval(updateClock, 1000);
setInterval(updateExternal, 3600000);

updateClock();
updateAll();
updateExternal();
