/* ════════════════════════════════════════════════════════
   Earth Intelligence — app.js
   Multi-hazard live monitor + history + predictions + news
════════════════════════════════════════════════════════ */

const API = 'http://localhost:8000/api';

// ── State ─────────────────────────────────────────────
let map, streetLayer, satelliteLayer, usingSatellite = false;
let markerLayers = {};        // hazard_type -> L.LayerGroup
let activeFilters = new Set(['fire','flood','earthquake','cyclone','landslide','heatwave','drought']);
let heatLayer = null;         // Leaflet.heat layer for temperature overlay
let currentTab = 'live';
let chatHistory = [];
let currentContext = {};
let historyChart = null, radarChart = null;
let historyEvents = [];
let allNews = [];
let playInterval = null;
let predictLat = 20.5937, predictLon = 78.9629;
let selectedCountry = 'India';

const HAZARD_ICONS = {
  fire:'🔥', flood:'🌊', earthquake:'🏔️', cyclone:'🌀',
  landslide:'⛰️', heatwave:'☀️', drought:'🏜️', volcano:'🌋',
  wildfire:'🔥', tsunami:'🌊', general:'⚠️'
};
const HAZARD_COLORS = {
  fire:'#FCA47C', flood:'#23CED9', earthquake:'#A1CCA6', cyclone:'#097C87',
  landslide:'#A1CCA6', heatwave:'#F9D779', drought:'#FCA47C',
  wildfire:'#FCA47C', volcano:'#FCA47C', general:'#097C87'
};

// ════════════════════════════════════════════════════════
// MAP INIT
// ════════════════════════════════════════════════════════
function initMap() {
  map = L.map('map', { center: [20.5937, 78.9629], zoom: 5, zoomControl: true });
  map.on('moveend', refreshAll);

  streetLayer = L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    { attribution: '© CARTO', maxZoom: 19 }
  ).addTo(map);

  satelliteLayer = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { attribution: '© ESRI', maxZoom: 19 }
  );

  // Hazard layer groups
  ['fire','flood','earthquake','cyclone','landslide','heatwave','drought','volcano','wildfire','general'].forEach(h => {
    markerLayers[h] = L.layerGroup().addTo(map);
  });

  // Click on map → trigger prediction
  map.on('click', e => {
    predictLat = e.latlng.lat;
    predictLon = e.latlng.lng;
    document.getElementById('predictCoords').textContent =
      `${predictLat.toFixed(2)}°N, ${predictLon.toFixed(2)}°E`;
    if (currentTab === 'predict') loadPredictions();
    if (currentTab === 'live') {
      analyzePoint(predictLat, predictLon);
    }
  });
}

function toggleMapStyle() {
  const btn = document.getElementById('mapStyleBtn');
  if (usingSatellite) {
    map.removeLayer(satelliteLayer);
    streetLayer.addTo(map);
    btn.textContent = '🛰️ Satellite';
  } else {
    map.removeLayer(streetLayer);
    satelliteLayer.addTo(map);
    btn.textContent = '🗺️ Street';
  }
  usingSatellite = !usingSatellite;
}

// ════════════════════════════════════════════════════════
// TAB NAVIGATION
// ════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  
  // Set default to India
  document.getElementById('continentSelect').value = 'Asia';
  onContinentChange();
  document.getElementById('countrySelect').value = 'India';
  onCountryChange(true); // pass true to avoid flying on init if preferred, or just let it fly
  
  setupFilterBtns();
  refreshAll();
  setInterval(refreshAll, 5 * 60 * 1000); // auto-refresh every 5 min

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });
});

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.panel-section').forEach(p => p.classList.add('hidden'));
  document.getElementById(`panel-${tab}`).classList.remove('hidden');

  const tl = document.getElementById('timelineBar');
  tl.style.display = tab === 'history' ? 'flex' : 'none';

  if (tab === 'history') loadHistory();
  if (tab === 'predict') loadPredictions();
  if (tab === 'news') loadNews();
}

// ════════════════════════════════════════════════════════
// FILTER BUTTONS
// ════════════════════════════════════════════════════════
function setupFilterBtns() {
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const h = btn.dataset.hazard;
      btn.classList.toggle('active');
      if (btn.classList.contains('active')) {
        activeFilters.add(h);
        markerLayers[h] && map.addLayer(markerLayers[h]);
        // Re-draw heat overlay when heatwave is toggled on
        if (h === 'heatwave') { loadFires(); loadHeatwaveGrid(); }
      } else {
        activeFilters.delete(h);
        markerLayers[h] && map.removeLayer(markerLayers[h]);
        // Hide heat overlay when heatwave is toggled off
        if (h === 'heatwave') {
          if (heatLayer)       { map.removeLayer(heatLayer);       heatLayer = null; }
          if (heatCircleLayer) { map.removeLayer(heatCircleLayer); heatCircleLayer = null; }
          if (heatGridLayer)   { map.removeLayer(heatGridLayer);   heatGridLayer = null; }
        }
      }
    });
  });
}

// ════════════════════════════════════════════════════════
// REFRESH ALL
// ════════════════════════════════════════════════════════
async function refreshAll() {
  setStatus('Refreshing…', false);
  try {
    await Promise.all([loadFires(), loadDisasters(), loadStats(), loadAlerts(), loadHeatwaveGrid(), loadWeather()]);
    setStatus('Live', true);
    document.getElementById('lastUpdated').textContent =
      '↺ ' + new Date().toLocaleTimeString();
  } catch(e) {
    setStatus('Offline', false);
  }
}

function getVisibleBBox() {
  if (typeof map !== 'undefined' && map.getBounds) {
    const b = map.getBounds();
    return `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`;
  }
  return '';
}

function setStatus(text, online) {
  document.getElementById('statusText').textContent = text;
  const dot = document.getElementById('statusDot');
  dot.className = 'status-dot' + (online ? ' online' : '');
}

// ════════════════════════════════════════════════════════
// FIRES
// ════════════════════════════════════════════════════════
async function loadFires() {
  const days = document.getElementById('daysSlider').value;
  const bbox = getVisibleBBox();
  const bboxParam = bbox ? `&bbox=${bbox}` : '';
  const res = await fetch(`${API}/fires/?days=${days}${bboxParam}`);
  const fires = await res.json();
  markerLayers['fire'].clearLayers();
  fires.forEach(f => {
    if (!activeFilters.has('fire')) return;
    // We can't easily filter FIRMS by country string natively, but we can rely on bbox.
    // If the backend returned country, we would filter here.
    const size = f.frp > 50 ? 32 : f.frp > 20 ? 26 : 20;
    const icon = L.divIcon({
      className: '', iconSize: [size, size], iconAnchor: [size/2, size/2],
      html: `<div class="hazard-marker fire" style="width:${size}px;height:${size}px;font-size:${size*0.55}px">🔥</div>`
    });
    L.marker([f.lat, f.lon], { icon })
      .bindPopup(firePopup(f))
      .addTo(markerLayers['fire']);
  });
  updateHeatLayer(fires); // draw temperature gradient overlay
}

function firePopup(f) {
  return `<div class="popup-title">🔥 Fire Hotspot</div>
    <div class="popup-row"><span>FRP</span><span class="popup-val">${f.frp.toFixed(1)} MW</span></div>
    <div class="popup-row"><span>Brightness</span><span class="popup-val">${f.brightness.toFixed(0)} K</span></div>
    <div class="popup-row"><span>Confidence</span><span class="popup-val">${f.confidence === 'h' ? '🟢 High' : f.confidence === 'n' ? '🟡 Nominal' : '🔴 Low'}</span></div>
    <div class="popup-row"><span>Date</span><span class="popup-val">${f.acq_date}</span></div>
    <button class="popup-btn" onclick="analyzePoint(${f.lat},${f.lon})">🔍 Analyze Region</button>`;
}

// ════════════════════════════════════════════════════════
// DISASTERS
// ════════════════════════════════════════════════════════
async function loadDisasters() {
  const res = await fetch(`${API}/disasters/live`);
  const disasters = await res.json();

  // Clear non-fire layers
  ['flood','earthquake','cyclone','drought','volcano','landslide'].forEach(h => {
    markerLayers[h] && markerLayers[h].clearLayers();
  });

  disasters.forEach(d => {
    // Filter by selected country
    if (selectedCountry && d.country && d.country.toLowerCase() !== selectedCountry.toLowerCase() && d.country !== 'Unknown') return;

    const htype = d.type || 'general';
    const layer = markerLayers[htype] || markerLayers['general'];
    if (!layer) return;
    if (!activeFilters.has(htype)) return;

    const size = d.severity === 'Red' ? 34 : d.severity === 'Orange' ? 28 : 22;
    const icon = L.divIcon({
      className: '', iconSize: [size, size], iconAnchor: [size/2, size/2],
      html: `<div class="hazard-marker ${htype}" style="width:${size}px;height:${size}px;font-size:${size*0.5}px">${d.icon||'⚠️'}</div>`
    });
    L.marker([d.lat, d.lon], { icon })
      .bindPopup(disasterPopup(d))
      .addTo(layer);
  });
}

function disasterPopup(d) {
  return `<div class="popup-title">${d.icon||'⚠️'} ${d.title}</div>
    <div class="popup-row"><span>Type</span><span class="popup-val">${d.type}</span></div>
    <div class="popup-row"><span>Severity</span><span class="popup-val" style="color:${d.severity==='Red'?'#ef4444':d.severity==='Orange'?'#FCA47C':'#A1CCA6'}">${d.severity}</span></div>
    <div class="popup-row"><span>Region</span><span class="popup-val">${d.region}</span></div>
    ${d.affected ? `<div class="popup-row"><span>Affected</span><span class="popup-val">${d.affected.toLocaleString()}</span></div>` : ''}
    <div style="font-size:11px;color:#9ba8c0;margin-top:6px;line-height:1.4">${d.description}</div>
    <button class="popup-btn" onclick="analyzePoint(${d.lat},${d.lon})">🔍 Analyze Region</button>`;
}

// ════════════════════════════════════════════════════════
// STATS
// ════════════════════════════════════════════════════════
async function loadStats() {
  const bbox = getVisibleBBox();
  const bboxParam = bbox ? `?bbox=${bbox}` : '';
  const res = await fetch(`${API}/stats${bboxParam}`);
  const s = await res.json();
  document.getElementById('statFires').textContent = s.total_fires_7d ?? '–';
  document.getElementById('statDisasters').textContent = s.active_disasters ?? '–';
  document.getElementById('statFlood').textContent = s.flood_risk ?? '–';
  document.getElementById('statCO2').textContent = s.co2_tons ? `${Math.round(s.co2_tons)}t` : '–';
  const badge = document.getElementById('alertBadge');
  badge.textContent = s.alert_level || '–';
  badge.className = 'al-badge ' + (s.alert_level || '');
  document.getElementById('alertPulse').className = 'al-pulse ' + (s.alert_level || '');
  // Plain-English meaning for each alert level
  const meanings = {
    Green:  'All clear — no major hazards detected',
    Yellow: 'Watch — elevated risk in some areas',
    Orange: 'Warning — multiple active hazards',
    Red:    'Emergency — immediate action required'
  };
  const meaning = document.getElementById('alertMeaning');
  if (meaning) meaning.textContent = meanings[s.alert_level] || '';
}

// ════════════════════════════════════════════════════════
// ALERTS
// ════════════════════════════════════════════════════════
async function loadAlerts() {
  const bbox = getVisibleBBox();
  const bboxParam = bbox ? `?bbox=${bbox}` : '';
  const res = await fetch(`${API}/alerts/${bboxParam}`);
  const alerts = await res.json();
  const list = document.getElementById('alertsList');
  if (!alerts.length) { list.innerHTML = '<div class="loading-state">No active alerts</div>'; return; }
  list.innerHTML = alerts.map(a => `
    <div class="alert-item ${a.severity}" onclick="flyTo(${a.lat},${a.lon})">
      <div class="alert-title">${a.title}</div>
      <div class="alert-desc">${a.description}</div>
      <div class="alert-meta">📍 ${a.region}</div>
    </div>`).join('');
}

// ════════════════════════════════════════════════════════
// ANALYSIS
// ════════════════════════════════════════════════════════
async function analyzeIndia() {
  const btn = document.getElementById('analyzeBtn');
  btn.textContent = '⏳ Analyzing…'; btn.disabled = true;
  try {
    const days = document.getElementById('daysSlider').value;
    
    let data;
    if (selectedCountry.toLowerCase() === 'india') {
      const res = await fetch(`${API}/analysis/india?days=${days}`);
      data = await res.json();
      flyTo(20.5937, 78.9629, 5);
    } else {
      const radius = document.getElementById('radiusSlider').value;
      const res = await fetch(`${API}/analysis/`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ lat: predictLat, lon: predictLon, radius_km: parseFloat(radius), days: parseInt(days), region_name: selectedCountry })
      });
      data = await res.json();
    }
    
    currentContext = data;
    const insight = data.llm_insight || 'Analysis complete.';
    document.getElementById('insightText').textContent = insight;
    const it2 = document.getElementById('insightText2');
    if (it2) it2.textContent = insight;
  } catch(e) {
    const msg = '⚠️ Analysis failed. Check backend connection.';
    document.getElementById('insightText').textContent = msg;
    const it2 = document.getElementById('insightText2');
    if (it2) it2.textContent = msg;
  }
  btn.textContent = `🛰️ Analyze ${selectedCountry || 'Region'}`; btn.disabled = false;
}

async function analyzePoint(lat, lon) {
  const radius = document.getElementById('radiusSlider').value;
  const days = document.getElementById('daysSlider').value;
  try {
    const res = await fetch(`${API}/analysis/`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ lat, lon, radius_km: parseFloat(radius), days: parseInt(days), region_name: `(${lat.toFixed(2)}°N, ${lon.toFixed(2)}°E)` })
    });
    const data = await res.json();
    currentContext = data;
    const insight = data.llm_insight || 'Analysis complete.';
    document.getElementById('insightText').textContent = insight;
    const it2 = document.getElementById('insightText2');
    if (it2) it2.textContent = insight;
    showRegionPanel(lat, lon, data);
  } catch(e) { console.error('analyzePoint failed', e); }
}

function showRegionPanel(lat, lon, data) {
  const panel = document.getElementById('regionPanel');
  document.getElementById('regionTitle').textContent = `📍 ${data.region}`;
  document.getElementById('regionContent').innerHTML = `
    <div class="popup-row"><span>Fires (${data.days}d)</span><span class="popup-val">${data.fire_count}</span></div>
    <div class="popup-row"><span>Forest Loss</span><span class="popup-val">${data.forest_loss_pct.toFixed(1)}%</span></div>
    <div class="popup-row"><span>Flood Risk</span><span class="popup-val">${data.flood_risk}</span></div>
    <div class="popup-row"><span>Air Quality</span><span class="popup-val">${data.air_quality_impact}</span></div>
    <div class="popup-row"><span>CO₂ Est.</span><span class="popup-val">${data.estimated_co2_tons.toFixed(0)}t</span></div>
    <div class="popup-row"><span>Alert</span><span class="popup-val" style="color:${alertColor(data.alert_level)}">${data.alert_level}</span></div>`;
  panel.style.display = 'block';
}

function closeRegionPanel() { document.getElementById('regionPanel').style.display = 'none'; }
function alertColor(l) { return {Red:'#ef4444',Orange:'#FCA47C',Yellow:'#F9D779',Green:'#A1CCA6'}[l]||'#94a3b8'; }
function flyTo(lat, lon, zoom=7) { map.flyTo([lat, lon], zoom, { duration: 1.2 }); }

// Collapsible how-to guide
function toggleHowto() {
  const body  = document.getElementById('howtoBody');
  const arrow = document.getElementById('howtoArrow');
  const open  = body.classList.toggle('open');
  arrow.classList.toggle('open', open);
}

// ════════════════════════════════════════════════════════
// WEATHER PANEL
// ════════════════════════════════════════════════════════
async function loadWeather(lat = 20.5937, lon = 78.9629, label = 'India') {
  try {
    const res = await fetch(`${API}/weather/?lat=${lat}&lon=${lon}`);
    const w = await res.json();

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('wxTemp',    w.current_temp != null ? w.current_temp.toFixed(1) : '–');
    set('wxMaxTemp', w.max_temp_7d  != null ? w.max_temp_7d.toFixed(1)  : '–');
    set('wxWind',    w.windspeed_kmh != null ? Math.round(w.windspeed_kmh) : '–');
    set('wxRain',    w.total_precip_7d != null ? w.total_precip_7d.toFixed(1) : '–');
    set('wxHeatIdx', w.heatwave_index != null ? w.heatwave_index + '/100' : '–');
    set('wxDrought', w.drought_severity || '–');
    set('wxLoc',     label);

    // Colour-code temperature tile
    const tempEl = document.getElementById('wxTemp');
    if (tempEl && w.current_temp != null) {
      const t = w.current_temp;
      tempEl.style.color = t >= 44 ? '#ef4444' : t >= 40 ? '#f97316' : t >= 35 ? '#eab308' : '#22c55e';
    }
    const hiEl = document.getElementById('wxHeatIdx');
    if (hiEl && w.heatwave_index != null) {
      const h = w.heatwave_index;
      hiEl.style.color = h >= 75 ? '#ef4444' : h >= 50 ? '#f97316' : h >= 25 ? '#eab308' : '#22c55e';
    }
  } catch(e) { console.warn('Weather load failed', e); }
}

// ════════════════════════════════════════════════════════
// RUD AI — FLOATING BUTTON TOGGLE
// ════════════════════════════════════════════════════════
function toggleRudAI() {
  const popup = document.getElementById('rudAiPopup');
  const fab   = document.getElementById('rudAiFab');
  const isOpen = popup.classList.contains('open');
  popup.classList.toggle('open', !isOpen);
  fab.style.background = isOpen
    ? 'linear-gradient(135deg, var(--accent) 0%, #1d5aab 100%)'
    : 'linear-gradient(135deg, #1d5aab 0%, var(--accent) 100%)';
}

// ════════════════════════════════════════════════════════
// CHAT
// ════════════════════════════════════════════════════════
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  appendMsg('user', msg);
  chatHistory.push({ role: 'user', content: msg });
  appendMsg('assistant', '⏳ Thinking…', 'typing');
  try {
    const res = await fetch(`${API}/chat/`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ message: msg, history: chatHistory.slice(-6), context: currentContext })
    });
    const data = await res.json();
    removeTyping();
    appendMsg('assistant', data.reply);
    chatHistory.push({ role: 'assistant', content: data.reply });
  } catch(e) {
    removeTyping();
    appendMsg('assistant', '⚠️ Chat service unavailable. Check backend + LLM config.');
  }
}

function appendMsg(role, text, id='') {
  const wrap = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = `msg ${role}`; if(id) div.id = id;
  div.innerHTML = `<div class="msg-bubble">${text}</div>`;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
}
function removeTyping() { const el = document.getElementById('typing'); if(el) el.remove(); }
function clearChat() {
  chatHistory = [];
  document.getElementById('chatMessages').innerHTML = '';
  appendMsg('assistant','💬 Chat cleared. Ask RUD AI anything about natural hazards!');
}

// ════════════════════════════════════════════════════════
// HISTORY
// ════════════════════════════════════════════════════════
async function loadHistory() {
  const type  = document.getElementById('historyTypeFilter').value;
  const days  = document.getElementById('historyDaysFilter').value;
  const url   = `${API}/history/events?days=${days}${type ? '&event_type='+type : ''}`;
  document.getElementById('historyList').innerHTML = '<div class="loading-state"><span class="spinner"></span> Loading…</div>';
  try {
    const res = await fetch(url);
    historyEvents = await res.json();
    renderHistoryList(historyEvents);
    renderHistoryChart(historyEvents);
    renderHistoryMarkers(historyEvents);
  } catch(e) {
    document.getElementById('historyList').innerHTML = '<div class="loading-state">Failed to load history</div>';
  }
}

function renderHistoryList(events) {
  const list = document.getElementById('historyList');
  if (!events.length) { list.innerHTML = '<div class="loading-state">No events found</div>'; return; }
  list.innerHTML = events.slice(0, 80).map(e => `
    <div class="event-item ${e.type}" onclick="flyTo(${e.lat},${e.lon})">
      <div class="event-title">${HAZARD_ICONS[e.type]||'⚠️'} ${e.title}</div>
      <div class="event-meta">📍 ${e.lat.toFixed(2)}°N, ${e.lon.toFixed(2)}°E · ${formatDate(e.date)}</div>
      <span class="event-sev ${e.severity||'low'}">${e.severity||'low'}</span>
    </div>`).join('');
}

function renderHistoryMarkers(events) {
  Object.values(markerLayers).forEach(l => l.clearLayers());
  events.forEach(e => {
    if (selectedCountry && e.country && e.country.toLowerCase() !== selectedCountry.toLowerCase() && e.country !== 'Unknown') return;
    const htype = e.type || 'general';
    const layer = markerLayers[htype];
    if (!layer || !activeFilters.has(htype)) return;
    const icon = L.divIcon({
      className: '', iconSize: [22,22], iconAnchor: [11,11],
      html: `<div class="hazard-marker ${htype}" style="width:22px;height:22px;font-size:12px">${HAZARD_ICONS[htype]||'⚠️'}</div>`
    });
    L.marker([e.lat, e.lon], { icon })
      .bindPopup(`<div class="popup-title">${HAZARD_ICONS[htype]||'⚠️'} ${e.title}</div><div style="font-size:11px;color:#9ba8c0;margin-top:4px">${formatDate(e.date)}</div>`)
      .addTo(layer);
  });
}

function renderHistoryChart(events) {
  const ctx = document.getElementById('historyChart');
  if (!ctx) return;
  if (historyChart) { historyChart.destroy(); historyChart = null; }

  // Count events per type
  const counts = {};
  events.forEach(e => { counts[e.type] = (counts[e.type]||0) + 1; });
  const labels = Object.keys(counts);
  const data = labels.map(l => counts[l]);
  const colors = labels.map(l => HAZARD_COLORS[l] || '#94a3b8');

  historyChart = new Chart(ctx, {
    type: 'bar',
    data: { labels: labels.map(l => `${HAZARD_ICONS[l]||''} ${l}`), datasets: [{
      label: 'Events', data, backgroundColor: colors.map(c => c+'99'), borderColor: colors, borderWidth: 1, borderRadius: 4
    }]},
    options: {
      responsive: true, plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color:'#9ba8c0', font:{size:10} }, grid: { color:'rgba(255,255,255,0.04)' } },
        y: { ticks: { color:'#9ba8c0', font:{size:10} }, grid: { color:'rgba(255,255,255,0.06)' }, beginAtZero: true }
      }
    }
  });
}

// History Timeline Scrubber
function scrubHistory(val) {
  const daysAgo = parseInt(val);
  const date = new Date(); date.setDate(date.getDate() - daysAgo);
  document.getElementById('timelineDate').textContent =
    daysAgo === 0 ? 'Today' : `${daysAgo}d ago`;
  const cutoff = date.toISOString();
  const filtered = historyEvents.filter(e => e.date >= cutoff);
  renderHistoryMarkers(filtered);
}

function togglePlay() {
  const btn = document.getElementById('playBtn');
  const slider = document.getElementById('timelineSlider');
  if (playInterval) {
    clearInterval(playInterval); playInterval = null; btn.textContent = '▶ Play';
  } else {
    slider.value = 30;
    btn.textContent = '⏹ Stop';
    playInterval = setInterval(() => {
      let v = parseInt(slider.value) - 1;
      if (v < 0) { clearInterval(playInterval); playInterval = null; btn.textContent = '▶ Play'; return; }
      slider.value = v;
      scrubHistory(v);
    }, 600);
  }
}

// ════════════════════════════════════════════════════════
// PREDICTIONS
// ════════════════════════════════════════════════════════
async function loadPredictions() {
  document.getElementById('riskGauges').innerHTML = '<div class="loading-state"><span class="spinner"></span> Computing risk…</div>';
  try {
    const res = await fetch(`${API}/predict/region?lat=${predictLat}&lon=${predictLon}`);
    const data = await res.json();
    renderGauges(data.risks);
    renderRadarChart(data.risks);
  } catch(e) {
    document.getElementById('riskGauges').innerHTML = '<div class="loading-state">Prediction failed — check backend</div>';
  }
}

function renderGauges(risks) {
  const hazards = [
    {key:'wildfire', icon:'🔥', label:'Wildfire'},
    {key:'flood',    icon:'🌊', label:'Flood'},
    {key:'landslide',icon:'⛰️', label:'Landslide'},
    {key:'cyclone',  icon:'🌀', label:'Cyclone'},
    {key:'earthquake',icon:'🏔️', label:'Earthquake'},
    {key:'heatwave', icon:'☀️', label:'Heatwave'},
    {key:'drought',  icon:'🏜️', label:'Drought'},
  ];
  document.getElementById('riskGauges').innerHTML = hazards.map(h => {
    const pct = risks[h.key] || 0;
    const cls = pct >= 75 ? 'critical' : pct >= 50 ? 'high' : pct >= 25 ? 'moderate' : 'low';
    return `<div class="gauge-row">
      <span class="gauge-icon">${h.icon}</span>
      <span class="gauge-label">${h.label}</span>
      <div class="gauge-bar-wrap">
        <div class="gauge-bar gauge-${cls}" style="width:${pct}%"></div>
      </div>
      <span class="gauge-pct pct-${cls}">${pct}%</span>
    </div>`;
  }).join('');
}

function renderRadarChart(risks) {
  const ctx = document.getElementById('radarChart');
  if (!ctx) return;
  if (radarChart) { radarChart.destroy(); radarChart = null; }
  const labels = ['Wildfire','Flood','Landslide','Cyclone','Earthquake','Heatwave','Drought'];
  const keys   = ['wildfire','flood','landslide','cyclone','earthquake','heatwave','drought'];
  const values = keys.map(k => risks[k] || 0);
  radarChart = new Chart(ctx, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: 'Risk %',
        data: values,
        backgroundColor: 'rgba(35,206,217,0.15)',
        borderColor: '#23CED9',
        pointBackgroundColor: '#23CED9',
        pointRadius: 3
      }]
    },
    options: {
      responsive: true,
      scales: { r: {
        min: 0, max: 100, ticks: { display: false },
        grid: { color: 'rgba(255,255,255,0.08)' },
        pointLabels: { color: '#9ba8c0', font:{size:9} },
        angleLines: { color: 'rgba(255,255,255,0.06)' }
      }},
      plugins: { legend: { display: false } }
    }
  });
}

// ════════════════════════════════════════════════════════
// NEWS
// ════════════════════════════════════════════════════════
async function loadNews(hazard='') {
  document.getElementById('newsList').innerHTML = '<div class="loading-state"><span class="spinner"></span> Fetching news…</div>';
  try {
    const url = hazard ? `${API}/news/hazard/${hazard}` : `${API}/news/`;
    const res = await fetch(url);
    allNews = await res.json();
    renderNews(allNews);
  } catch(e) {
    document.getElementById('newsList').innerHTML = '<div class="loading-state">Failed to load news</div>';
  }
}

function filterNews(type, btn) {
  document.querySelectorAll('.news-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (type === 'all') { renderNews(allNews); return; }
  renderNews(allNews.filter(n => n.hazard_type === type));
}

function renderNews(items) {
  const list = document.getElementById('newsList');
  if (!items.length) { list.innerHTML = '<div class="loading-state">No news found</div>'; return; }
  list.innerHTML = items.map(n => `
    <a class="news-item" href="${n.url}" target="_blank" rel="noopener">
      <div class="news-item-top">
        <div class="news-headline">${HAZARD_ICONS[n.hazard_type]||'📰'} ${n.title}</div>
        <span class="news-tone ${n.tone||'neutral'}">${n.tone||'neutral'}</span>
      </div>
      <div class="news-summary">${n.summary || ''}</div>
      <div class="news-meta">
        <span class="news-source">${n.source||'Unknown'}</span>
        <span>${formatDate(n.date)}</span>
      </div>
    </a>`).join('');
}

// ════════════════════════════════════════════════════════
// HELPERS
// ════════════════════════════════════════════════════════
function formatDate(iso) {
  if (!iso) return '–';
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffH = Math.floor((now - d) / 3600000);
    if (diffH < 1) return 'Just now';
    if (diffH < 24) return `${diffH}h ago`;
    const diffD = Math.floor(diffH / 24);
    if (diffD < 7) return `${diffD}d ago`;
    return d.toLocaleDateString('en-IN', {day:'numeric', month:'short'});
  } catch { return iso.slice(0,10); }
}

// ════════════════════════════════════════════════════════
// HEAT LAYER — Temperature / Heatwave Overlay
// ════════════════════════════════════════════════════════
let heatCircleLayer = null; // fallback circle-based layer group
let heatGridLayer   = null; // dedicated heatwave grid layer

// India grid: lat/lon points to sample for the heatwave overlay
const HEATWAVE_GRID = [
  // Northwest (Rajasthan, Punjab, Haryana)
  [28.7, 77.1], [27.0, 74.2], [25.0, 71.5], [30.5, 74.5], [29.1, 76.0],
  // Central (MP, UP, Bihar)
  [23.5, 77.5], [25.4, 81.8], [26.8, 83.0], [24.5, 79.0], [22.7, 75.8],
  // North (Delhi, Uttarakhand)
  [28.6, 77.2], [30.3, 78.0],
  // South (AP, Telangana, Tamil Nadu)
  [17.4, 78.5], [15.3, 78.5], [13.1, 80.3], [11.0, 77.0],
  // East (Odisha, West Bengal)
  [20.3, 85.8], [22.6, 88.4],
  // West (Gujarat, Maharashtra)
  [23.0, 72.6], [19.1, 72.9], [21.2, 81.0],
];

function tempToColor(idx) {
  // Map heatwave_index (0-100) to a vivid color scale
  if (idx >= 80) return '#ef4444'; // red – extreme
  if (idx >= 60) return '#f97316'; // orange – severe
  if (idx >= 40) return '#eab308'; // yellow – high
  if (idx >= 20) return '#84cc16'; // lime – moderate
  return '#06b6d4';                // cyan – low
}

function frpToColor(frp) {
  const t = Math.min(1, (frp || 1) / 120);
  if (t < 0.2)  return { color: '#3b82f6', fill: '#3b82f6' };
  if (t < 0.4)  return { color: '#06b6d4', fill: '#06b6d4' };
  if (t < 0.55) return { color: '#84cc16', fill: '#84cc16' };
  if (t < 0.7)  return { color: '#eab308', fill: '#eab308' };
  if (t < 0.85) return { color: '#f97316', fill: '#f97316' };
  return { color: '#ef4444', fill: '#ef4444' };
}

// ── Load dedicated heatwave grid from backend ───────────
async function loadHeatwaveGrid() {
  if (!activeFilters.has('heatwave')) return;
  if (heatGridLayer) { map.removeLayer(heatGridLayer); heatGridLayer = null; }
  
  // Heatwave grid is currently hardcoded for India, so only show it for India
  if (selectedCountry && selectedCountry.toLowerCase() !== 'india') return;

  heatGridLayer = L.layerGroup().addTo(map);
  const pts = [];

  // Fetch heatwave data for all grid points in parallel
  const results = await Promise.allSettled(
    HEATWAVE_GRID.map(([lat, lon]) =>
      fetch(`${API}/weather/heatwave?lat=${lat}&lon=${lon}`).then(r => r.json())
    )
  );

  results.forEach((res, i) => {
    if (res.status !== 'fulfilled') return;
    const d = res.value;
    const [lat, lon] = HEATWAVE_GRID[i];
    const idx   = d.heatwave_index || 0;
    const color = tempToColor(idx);
    const radKm = 80000 + idx * 1200; // radius in metres: bigger = hotter

    // Only draw if there is measurable heat risk
    if (idx < 5) return;

    // Outer glow
    L.circle([lat, lon], {
      radius: radKm * 2,
      color: 'transparent', fillColor: color,
      fillOpacity: 0.08, interactive: false
    }).addTo(heatGridLayer);

    // Mid ring
    L.circle([lat, lon], {
      radius: radKm,
      color: 'transparent', fillColor: color,
      fillOpacity: 0.15, interactive: false
    }).addTo(heatGridLayer);

    // Hot core
    L.circle([lat, lon], {
      radius: radKm * 0.4,
      color: color, weight: 1, fillColor: color,
      fillOpacity: 0.25, interactive: true
    }).bindPopup(
      `<div class="popup-title">☀️ Heatwave Zone</div>` +
      `<div class="popup-row"><span>Heat Index</span><span class="popup-val">${idx}/100</span></div>` +
      `<div class="popup-row"><span>Max Temp</span><span class="popup-val">${d.max_temp?.toFixed(1) ?? '–'}°C</span></div>` +
      `<div class="popup-row"><span>Risk</span><span class="popup-val" style="color:${color}">${d.risk_level}</span></div>` +
      `<button class="popup-btn" onclick="analyzePoint(${lat},${lon})">🔍 Analyze Region</button>`
    ).addTo(heatGridLayer);
  });
}

function updateHeatLayer(fires) {
  // Clean up previous FRP-based layers
  if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }
  if (heatCircleLayer) { map.removeLayer(heatCircleLayer); heatCircleLayer = null; }
  if (!activeFilters.has('heatwave') || !fires.length) return;

  // ── Try leaflet.heat plugin first ──────────────────────
  if (typeof L.heatLayer !== 'undefined') {
    const pts = fires.map(f => [f.lat, f.lon, Math.min(1, (f.frp || 1) / 120)]);
    heatLayer = L.heatLayer(pts, {
      radius: 50, blur: 40, maxZoom: 12, max: 1.0,
      gradient: {
        0.0: '#3b82f6', 0.2: '#06b6d4', 0.45: '#84cc16',
        0.65: '#eab308', 0.82: '#f97316', 1.0: '#ef4444'
      }
    }).addTo(map);
    return;
  }

  // ── Fallback: stacked semi-transparent circles ──────────
  heatCircleLayer = L.layerGroup().addTo(map);
  fires.forEach(f => {
    const t   = Math.min(1, (f.frp || 1) / 120);
    const c   = frpToColor(f.frp);
    const km  = 60 + t * 120;

    // Outer glow
    L.circle([f.lat, f.lon], {
      radius: km * 1400,
      color: 'transparent', fillColor: c.fill,
      fillOpacity: 0.10, interactive: false
    }).addTo(heatCircleLayer);

    // Mid ring
    L.circle([f.lat, f.lon], {
      radius: km * 700,
      color: 'transparent', fillColor: c.fill,
      fillOpacity: 0.18, interactive: false
    }).addTo(heatCircleLayer);

    // Hot core
    L.circle([f.lat, f.lon], {
      radius: km * 300,
      color: 'transparent', fillColor: c.fill,
      fillOpacity: 0.28, interactive: false
    }).addTo(heatCircleLayer);
  });
}


// ════════════════════════════════════════════════════════
// LOCATION SEARCH
// ════════════════════════════════════════════════════════
const CONTINENTS = {
  'Asia': ['Afghanistan','Bangladesh','Cambodia','China','India','Indonesia','Iran','Iraq','Japan','Kazakhstan','Kuwait','Laos','Lebanon','Malaysia','Myanmar','Nepal','Oman','Pakistan','Philippines','Qatar','Saudi Arabia','Singapore','South Korea','Sri Lanka','Syria','Taiwan','Thailand','Turkey','UAE','Uzbekistan','Vietnam','Yemen'],
  'Europe': ['Austria','Belarus','Belgium','Bulgaria','Croatia','Czech Republic','Denmark','Finland','France','Germany','Greece','Hungary','Ireland','Italy','Netherlands','Norway','Poland','Portugal','Romania','Russia','Serbia','Slovakia','Spain','Sweden','Switzerland','Ukraine','United Kingdom'],
  'North America': ['Belize','Canada','Costa Rica','Cuba','Dominican Republic','El Salvador','Guatemala','Haiti','Honduras','Jamaica','Mexico','Nicaragua','Panama','United States'],
  'South America': ['Argentina','Bolivia','Brazil','Chile','Colombia','Ecuador','Paraguay','Peru','Uruguay','Venezuela'],
  'Africa': ['Algeria','Angola','Cameroon','DR Congo','Egypt','Ethiopia','Ghana','Ivory Coast','Kenya','Libya','Madagascar','Mali','Morocco','Mozambique','Namibia','Nigeria','Rwanda','Senegal','Somalia','South Africa','Sudan','Tanzania','Tunisia','Uganda','Zambia','Zimbabwe'],
  'Oceania': ['Australia','Fiji','New Zealand','Papua New Guinea','Samoa','Solomon Islands','Tonga']
};

const CONTINENT_CENTERS = {
  'Asia':          [34, 100, 3],
  'Europe':        [54,  15, 4],
  'North America': [40, -95, 3],
  'South America': [-15,-60, 3],
  'Africa':        [ 5,  20, 3],
  'Oceania':       [-25,140, 4]
};

function onContinentChange() {
  const cont = document.getElementById('continentSelect').value;
  const countrySel = document.getElementById('countrySelect');
  const cityInput  = document.getElementById('cityInput');
  countrySel.innerHTML = '<option value="">🏳️ Country</option>';
  countrySel.disabled  = !cont;
  cityInput.value = '';
  cityInput.placeholder = 'State or city…';
  if (cont) {
    (CONTINENTS[cont] || []).sort().forEach(c => {
      const o = document.createElement('option'); o.value = c; o.textContent = c;
      countrySel.appendChild(o);
    });
    const cc = CONTINENT_CENTERS[cont];
    if (cc) map.flyTo([cc[0], cc[1]], cc[2], { duration: 1.5 });
  }
}

function onCountryChange(skipFly = false) {
  const country = document.getElementById('countrySelect').value;
  if (!country) return;
  selectedCountry = country;
  document.getElementById('cityInput').placeholder = `City or state in ${country}…`;
  
  const analyzeBtn = document.getElementById('analyzeBtn');
  if (analyzeBtn) analyzeBtn.textContent = `🛰️ Analyze ${country}`;
  
  if (!skipFly) {
    geocodeAndFly(country);
  }
  
  // Refresh data to show problems of selected country
  refreshAll();
}

async function searchLocation() {
  const country = document.getElementById('countrySelect').value;
  const city    = document.getElementById('cityInput').value.trim();
  if (!city && !country) return;
  // NOTE: never include the continent — geocoding APIs don't understand continent names
  const query = [city, country].filter(Boolean).join(', ');
  await geocodeAndFly(query);
}

async function geocodeAndFly(query) {
  const btn = document.getElementById('locSearchBtn');
  if (btn) { btn.textContent = '⏳'; btn.disabled = true; }

  let lat = null, lon = null, shortName = '', zoom = 8;

  try {
    // ── Primary: Open-Meteo Geocoding (no User-Agent needed, no CORS issues) ──
    const omUrl = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query)}&count=5&language=en&format=json`;
    const omRes  = await fetch(omUrl);
    const omData = await omRes.json();

    if (omData.results && omData.results.length > 0) {
      const r = omData.results[0];
      lat  = r.latitude;
      lon  = r.longitude;
      shortName = [r.name, r.admin1, r.country].filter(Boolean).join(', ');
      // Zoom by feature type
      const fc = (r.feature_code || '').toUpperCase();
      zoom = fc.startsWith('PCL') ? 5        // country-level
           : fc.startsWith('ADM') ? 7        // state/region
           : (r.population > 500000) ? 10    // large city
           : (r.population > 50000)  ? 11    // small city
           : 9;
    }
  } catch(e) { console.warn('Open-Meteo geocoding failed:', e); }

  // ── Fallback: Nominatim ──────────────────────────────────────────────────────
  if (lat === null) {
    try {
      const nomUrl = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1&accept-language=en`;
      const nomRes  = await fetch(nomUrl);
      const nomData = await nomRes.json();
      if (nomData && nomData[0]) {
        lat  = parseFloat(nomData[0].lat);
        lon  = parseFloat(nomData[0].lon);
        shortName = nomData[0].display_name.split(',').slice(0, 2).join(',').trim();
        const t = nomData[0].type;
        zoom = (t === 'city' || t === 'town') ? 10 : t === 'country' ? 5 : 8;
      }
    } catch(e) { console.warn('Nominatim fallback failed:', e); }
  }

  if (lat !== null && lon !== null) {
    map.flyTo([lat, lon], zoom, { duration: 1.5 });
    showLocToast(`📍 ${shortName || query}`);
    predictLat = lat; predictLon = lon;
    document.getElementById('predictCoords').textContent =
      `${lat.toFixed(2)}°N, ${lon.toFixed(2)}°E`;
    loadWeather(lat, lon, (shortName || query).split(',')[0].trim());
  } else {
    showLocToast('⚠️ Location not found — try a different spelling');
  }

  if (btn) { btn.textContent = '🔍'; btn.disabled = false; }
}

function showLocToast(msg) {
  const existing = document.querySelector('.loc-toast');
  if (existing) existing.remove();
  const t = document.createElement('div');
  t.className = 'loc-toast'; t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}
