// ===================================
// Landslide Warning Dashboard - Frontend Logic
// ===================================

const API_BASE = window.location.origin;

// Global state
let map;
let markers = {};
let markerCluster;
let allPredictions = [];
let filters = {
    danger: true,
    warning: true,
    normal: true
};

// ===================================
// Initialize
// ===================================

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadData();
    setupEventListeners();

    // Auto-refresh every 5 minutes
    setInterval(loadData, 5 * 60 * 1000);
});

// ===================================
// Map Initialization
// ===================================

function initMap() {
    // Center on Northern Thailand
    map = L.map('map').setView([18.8, 100.5], 9);

    // Dark theme tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // Initialize marker cluster
    markerCluster = L.markerClusterGroup({
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true
    });

    map.addLayer(markerCluster);
}

// ===================================
// Data Loading
// ===================================

async function loadData() {
    try {
        // Load statistics
        const stats = await fetch(`${API_BASE}/api/stats`).then(r => r.json());
        updateStatistics(stats);

        // Load predictions
        const predictions = await fetch(`${API_BASE}/api/predictions/latest?limit=3000`).then(r => r.json());
        allPredictions = predictions;
        updateMap(predictions);

    } catch (error) {
        console.error('Failed to load data:', error);
    }
}

// ===================================
// Update Statistics
// ===================================

function updateStatistics(stats) {
    document.getElementById('dangerCount').textContent = stats.danger_count;
    document.getElementById('warningCount').textContent = stats.warning_count;
    document.getElementById('normalCount').textContent = stats.normal_count;
    document.getElementById('totalCount').textContent = stats.total_locations;

    if (stats.last_update) {
        const lastUpdate = new Date(stats.last_update);
        document.getElementById('lastUpdate').textContent = formatDateTime(lastUpdate);
    }
}

// ===================================
// Update Map
// ===================================

function updateMap(predictions) {
    // Clear existing markers
    markerCluster.clearLayers();
    markers = {};

    // Add markers
    predictions.forEach(pred => {
        if (!shouldShowMarker(pred.risk_level)) return;

        const marker = createMarker(pred);
        markers[pred.location_id] = marker;
        markerCluster.addLayer(marker);
    });
}

function createMarker(pred) {
    // Marker color based on risk level
    const color = pred.risk_color;

    // Custom icon
    const icon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="
            background-color: ${getColorHex(color)};
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        "></div>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6]
    });

    const marker = L.marker([pred.latitude, pred.longitude], { icon });

    // Popup content
    const popupContent = `
        <div class="popup-title">📍 ${pred.district || 'Unknown'}, ${pred.tambon || ''}</div>
        <div class="popup-status">${pred.status}</div>
        <div class="popup-details">
            <strong>Probability:</strong> ${pred.probability}%<br>
            <strong>Slope:</strong> ${pred.details?.Slope_Extracted?.toFixed(1) || 'N/A'}°<br>
            <strong>Elevation:</strong> ${pred.details?.Elevation_Extracted?.toFixed(0) || 'N/A'} m<br>
            <strong>NDVI:</strong> ${pred.details?.NDVI?.toFixed(3) || 'N/A'}<br>
            <strong>Rain (7d):</strong> ${pred.details?.Rain_Ant_7D?.toFixed(1) || 'N/A'} mm<br>
            <strong>Updated:</strong> ${formatDateTime(new Date(pred.predicted_at))}
        </div>
    `;

    marker.bindPopup(popupContent);

    return marker;
}

function getColorHex(color) {
    const colors = {
        'red': '#EF4444',
        'yellow': '#F59E0B',
        'green': '#10B981'
    };
    return colors[color] || '#94A3B8';
}

// ===================================
// Filters
// ===================================

function shouldShowMarker(riskLevel) {
    if (riskLevel === 'DANGER') return filters.danger;
    if (riskLevel === 'WARNING') return filters.warning;
    if (riskLevel === 'NORMAL') return filters.normal;
    return true;
}

function applyFilters() {
    updateMap(allPredictions);
}

// ===================================
// Event Listeners
// ===================================

function setupEventListeners() {
    // Filter checkboxes
    document.getElementById('showDanger').addEventListener('change', (e) => {
        filters.danger = e.target.checked;
        applyFilters();
    });

    document.getElementById('showWarning').addEventListener('change', (e) => {
        filters.warning = e.target.checked;
        applyFilters();
    });

    document.getElementById('showNormal').addEventListener('change', (e) => {
        filters.normal = e.target.checked;
        applyFilters();
    });

    // Search
    document.getElementById('searchBox').addEventListener('input', (e) => {
        handleSearch(e.target.value);
    });

    // Manual update button
    document.getElementById('manualUpdate').addEventListener('click', async () => {
        const btn = document.getElementById('manualUpdate');
        btn.disabled = true;
        btn.innerHTML = '<span class="btn-icon">⏳</span> Updating...';

        try {
            await fetch(`${API_BASE}/api/update`, { method: 'POST' });
            alert('Update started! This may take several minutes. The dashboard will refresh automatically.');

            // Reload after 30 seconds
            setTimeout(loadData, 30000);
        } catch (error) {
            alert('Failed to trigger update: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<span class="btn-icon">🔄</span> Manual Update';
        }
    });
}

// ===================================
// Search
// ===================================

function handleSearch(query) {
    if (!query || query.length < 2) {
        document.getElementById('searchResults').innerHTML = '';
        return;
    }

    const results = allPredictions.filter(pred => {
        const searchText = `${pred.district} ${pred.tambon} ${pred.invent_id}`.toLowerCase();
        return searchText.includes(query.toLowerCase());
    }).slice(0, 10);

    const resultsHtml = results.map(pred => `
        <div class="search-result-item" onclick="flyToLocation(${pred.latitude}, ${pred.longitude})">
            <strong>${pred.district}, ${pred.tambon}</strong><br>
            <small>${pred.status}</small>
        </div>
    `).join('');

    document.getElementById('searchResults').innerHTML = resultsHtml || '<p style="color: #94A3B8; font-size: 0.75rem;">No results found</p>';
}

function flyToLocation(lat, lon) {
    map.flyTo([lat, lon], 14, {
        duration: 1.5
    });
}

// ===================================
// Utilities
// ===================================

function formatDateTime(date) {
    const now = new Date();
    const diff = now - date;

    // Less than 1 hour ago
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes} min ago`;
    }

    // Less than 24 hours ago
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    }

    // Format as date
    return date.toLocaleString('th-TH', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Add CSS for search results
const style = document.createElement('style');
style.textContent = `
    .search-result-item {
        padding: 0.75rem;
        background: var(--color-bg-light);
        border-radius: var(--radius-sm);
        margin-bottom: 0.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .search-result-item:hover {
        background: var(--color-bg-lighter);
        transform: translateX(4px);
    }
    
    .search-result-item strong {
        color: var(--color-text);
        font-size: 0.875rem;
    }
    
    .search-result-item small {
        color: var(--color-text-muted);
        font-size: 0.75rem;
    }
`;
document.head.appendChild(style);
