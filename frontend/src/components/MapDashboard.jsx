import React, { useState, useCallback, useEffect, useRef, useContext } from 'react';
import Map from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import { PolygonLayer, ScatterplotLayer } from '@deck.gl/layers';

const MAP_STYLES = {
    dark: { label: '🌑 Dark', url: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json' },
    light: { label: '☀️ Light', url: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json' },
    streets: { label: '🗺️ Streets', url: 'https://tiles.openfreemap.org/styles/liberty' },
    terrain: {
        label: '🏔️ Terrain', url: {
            version: 8, name: 'OpenTopoMap',
            sources: { 'otm': { type: 'raster', tiles: ['https://tile.opentopomap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OpenTopoMap contributors' } },
            layers: [{ id: 'otm-tiles', type: 'raster', source: 'otm', minzoom: 0, maxzoom: 17 }]
        }
    },
    satellite: {
        label: '🛰️ Satellite', url: {
            version: 8, name: 'Esri World Imagery',
            sources: { 'esri': { type: 'raster', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'], tileSize: 256, attribution: '© Esri' } },
            layers: [{ id: 'esri-tiles', type: 'raster', source: 'esri', minzoom: 0, maxzoom: 19 }]
        }
    },
};
const API = 'http://localhost:8000';
const INITIAL_VIEW = { longitude: 100.85, latitude: 18.8, zoom: 9, pitch: 0, bearing: 0 };
const RISK_COLORS = { High: [255, 40, 40, 210], Medium: [255, 165, 0, 200], Low: [100, 120, 130, 80] };

// Tambon (sub-district) data for reverse geocoding
const NAN_TAMBONS = [
    { n: 'ในเวียง', a: 'Mueang Nan', c: [100.773, 18.783] }, { n: 'บ่อ', a: 'Mueang Nan', c: [100.75, 18.76] },
    { n: 'ผาสิงห์', a: 'Mueang Nan', c: [100.80, 18.80] }, { n: 'ไชยสถาน', a: 'Mueang Nan', c: [100.78, 18.75] },
    { n: 'ถืมตอง', a: 'Mueang Nan', c: [100.76, 18.77] }, { n: 'เรือง', a: 'Mueang Nan', c: [100.72, 18.82] },
    { n: 'นาซาว', a: 'Mueang Nan', c: [100.70, 18.68] }, { n: 'ดู่ใต้', a: 'Mueang Nan', c: [100.83, 18.73] },
    { n: 'กองควาย', a: 'Mueang Nan', c: [100.85, 18.81] }, { n: 'สวก', a: 'Mueang Nan', c: [100.88, 18.87] },
    { n: 'หนองแดง', a: 'Mae Charim', c: [100.83, 18.58] }, { n: 'หมอเมือง', a: 'Mae Charim', c: [100.87, 18.53] },
    { n: 'น้ำพาง', a: 'Mae Charim', c: [100.90, 18.48] }, { n: 'แม่จริม', a: 'Mae Charim', c: [100.85, 18.55] },
    { n: 'บ้านฟ้า', a: 'Ban Luang', c: [100.61, 18.92] }, { n: 'ป่าคาหลวง', a: 'Ban Luang', c: [100.58, 18.88] },
    { n: 'สวด', a: 'Ban Luang', c: [100.63, 18.95] }, { n: 'บ้านพี้', a: 'Ban Luang', c: [100.56, 18.85] },
    { n: 'นาน้อย', a: 'Na Noi', c: [100.72, 18.38] }, { n: 'เชียงของ', a: 'Na Noi', c: [100.68, 18.30] },
    { n: 'ศรีษะเกษ', a: 'Na Noi', c: [100.75, 18.42] }, { n: 'สถาน', a: 'Na Noi', c: [100.78, 18.35] },
    { n: 'สันทะ', a: 'Na Noi', c: [100.65, 18.25] }, { n: 'บัวใหญ่', a: 'Na Noi', c: [100.75, 18.32] },
    { n: 'น้ำตก', a: 'Na Noi', c: [100.80, 18.28] },
    { n: 'ปัว', a: 'Pua', c: [101.08, 19.17] }, { n: 'แงง', a: 'Pua', c: [101.05, 19.20] },
    { n: 'สกาด', a: 'Pua', c: [101.12, 19.22] }, { n: 'ศิลาเพชร', a: 'Pua', c: [101.00, 19.15] },
    { n: 'ศิลาแลง', a: 'Pua', c: [101.15, 19.25] }, { n: 'อวน', a: 'Pua', c: [101.02, 19.10] },
    { n: 'ไชยวัฒนา', a: 'Pua', c: [101.10, 19.12] }, { n: 'เจดีย์ชัย', a: 'Pua', c: [101.06, 19.05] },
    { n: 'ภูคา', a: 'Pua', c: [101.18, 19.30] }, { n: 'สวนขวัญ', a: 'Pua', c: [101.03, 19.18] },
    { n: 'วรนคร', a: 'Pua', c: [101.07, 19.15] },
    { n: 'ริม', a: 'Tha Wang Pha', c: [100.75, 19.12] }, { n: 'ป่าคา', a: 'Tha Wang Pha', c: [100.72, 19.08] },
    { n: 'ผาตอ', a: 'Tha Wang Pha', c: [100.80, 19.18] }, { n: 'ยม', a: 'Tha Wang Pha', c: [100.68, 19.05] },
    { n: 'ตาลี่', a: 'Tha Wang Pha', c: [100.78, 19.15] }, { n: 'ศรีภูมิ', a: 'Tha Wang Pha', c: [100.70, 19.10] },
    { n: 'จอมพระ', a: 'Tha Wang Pha', c: [100.73, 19.20] }, { n: 'แสนทอง', a: 'Tha Wang Pha', c: [100.82, 19.22] },
    { n: 'กลางเวียง', a: 'Wiang Sa', c: [100.70, 18.55] }, { n: 'ขึ่ง', a: 'Wiang Sa', c: [100.65, 18.50] },
    { n: 'ไหล่น่าน', a: 'Wiang Sa', c: [100.72, 18.62] }, { n: 'ตาลชุม', a: 'Wiang Sa', c: [100.60, 18.45] },
    { n: 'นาเหลือง', a: 'Wiang Sa', c: [100.75, 18.58] }, { n: 'ส้าน', a: 'Wiang Sa', c: [100.58, 18.40] },
    { n: 'น้ำมวบ', a: 'Wiang Sa', c: [100.82, 18.65] }, { n: 'น้ำปั้ว', a: 'Wiang Sa', c: [100.78, 18.68] },
    { n: 'ยาบหัวนา', a: 'Wiang Sa', c: [100.68, 18.52] }, { n: 'ปงสนุก', a: 'Wiang Sa', c: [100.73, 18.48] },
    { n: 'ทุ่งช้าง', a: 'Thung Chang', c: [101.05, 19.40] }, { n: 'งอบ', a: 'Thung Chang', c: [101.00, 19.38] },
    { n: 'และ', a: 'Thung Chang', c: [101.10, 19.45] }, { n: 'ปอน', a: 'Thung Chang', c: [101.08, 19.35] },
    { n: 'เชียงกลาง', a: 'Chiang Klang', c: [100.87, 19.28] }, { n: 'เปือ', a: 'Chiang Klang', c: [100.82, 19.25] },
    { n: 'เชียงคาน', a: 'Chiang Klang', c: [100.90, 19.32] }, { n: 'พระธาตุ', a: 'Chiang Klang', c: [100.85, 19.30] },
    { n: 'พญาแก้ว', a: 'Chiang Klang', c: [100.93, 19.35] },
    { n: 'นาทะนุง', a: 'Na Muen', c: [100.65, 18.22] }, { n: 'บ่อแก้ว', a: 'Na Muen', c: [100.60, 18.18] },
    { n: 'เมืองลี', a: 'Na Muen', c: [100.70, 18.25] }, { n: 'ปิงหลวง', a: 'Na Muen', c: [100.63, 18.15] },
    { n: 'ดู่พงษ์', a: 'Santi Suk', c: [100.85, 18.92] }, { n: 'ป่าแลวหลวง', a: 'Santi Suk', c: [100.88, 18.88] },
    { n: 'พงษ์', a: 'Santi Suk', c: [100.82, 18.95] },
    { n: 'บ่อเกลือเหนือ', a: 'Bo Kluea', c: [101.15, 19.30] }, { n: 'บ่อเกลือใต้', a: 'Bo Kluea', c: [101.12, 19.22] },
    { n: 'ภูฟ้า', a: 'Bo Kluea', c: [101.20, 19.35] }, { n: 'ดงพญา', a: 'Bo Kluea', c: [101.18, 19.18] },
    { n: 'นาไร่หลวง', a: 'Song Khwae', c: [100.98, 19.38] }, { n: 'ชนแดน', a: 'Song Khwae', c: [100.95, 19.32] },
    { n: 'ยอด', a: 'Song Khwae', c: [101.02, 19.42] },
    { n: 'ม่วงตึ๊ด', a: 'Phu Phiang', c: [100.80, 18.72] }, { n: 'นาปัง', a: 'Phu Phiang', c: [100.77, 18.68] },
    { n: 'น้ำแก่น', a: 'Phu Phiang', c: [100.83, 18.75] }, { n: 'ท่าน้าว', a: 'Phu Phiang', c: [100.85, 18.78] },
    { n: 'เมืองจัง', a: 'Phu Phiang', c: [100.75, 18.65] }, { n: 'ฝายแก้ว', a: 'Phu Phiang', c: [100.88, 18.82] },
    { n: 'สองแคว', a: 'Phu Phiang', c: [100.78, 18.70] },
    { n: 'ห้วยโก๋น', a: 'Chaloem Phra Kiat', c: [101.15, 19.52] }, { n: 'ขุนน่าน', a: 'Chaloem Phra Kiat', c: [101.18, 19.48] },
];

import { AuthContext } from '../contexts/AuthContext';

export default function MapDashboard() {
    const { token, logout, user } = useContext(AuthContext);
    const [gridData, setGridData] = useState([]);
    const [layers, setLayers] = useState([]);
    const [viewState, setViewState] = useState(INITIAL_VIEW);
    const [status, setStatus] = useState('Ready');
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState([]);
    const [filters, setFilters] = useState({ High: true, Medium: true, Low: true });
    const [tab, setTab] = useState('map');
    const [mapStyle, setMapStyle] = useState('dark');
    const [styleMenuOpen, setStyleMenuOpen] = useState(false);
    const [alerts, setAlerts] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [districts, setDistricts] = useState([]);

    // Other states...
    const [whatIfMode, setWhatIfMode] = useState(false);
    const [whatIfRainDays, setWhatIfRainDays] = useState(Array(10).fill(0));
    const [whatIfResult, setWhatIfResult] = useState(null);
    const [whatIfPin, setWhatIfPin] = useState(null);
    const [predicting, setPredicting] = useState(false);

    // History states
    const [historyAlerts, setHistoryAlerts] = useState([]);
    const [historyStart, setHistoryStart] = useState('');
    const [historyEnd, setHistoryEnd] = useState('');
    const [historyLoading, setHistoryLoading] = useState(false);

    // Historical landslide points overlay
    const [historicalPoints, setHistoricalPoints] = useState([]);
    const [showHistorical, setShowHistorical] = useState(false);

    // Mapped Alerts based on predictions — all risk levels, top 100 by probability
    const MAPPED_ALERTS = React.useMemo(() => {
        let alerts = [...gridData];
        // Sort from highest probability to lowest
        alerts.sort((a, b) => (b.probability || 0) - (a.probability || 0));
        // Top 100 only
        return alerts.slice(0, 100);
    }, [gridData]);

    // Match historical points to existing grid cells (spatial hash for fast lookup)
    const historicalGridCells = React.useMemo(() => {
        try {
            if (!historicalPoints || !gridData || historicalPoints.length === 0 || gridData.length === 0) return [];

            // Build spatial hash from grid cells (~0.01° buckets)
            const gridMap = new globalThis.Map();
            for (const cell of gridData) {
                const poly = cell.polygon;
                if (!poly || !Array.isArray(poly) || poly.length < 4) continue;
                if (!Array.isArray(poly[0]) || !Array.isArray(poly[2])) continue;
                const cx = cell.longitude || ((poly[0][0] + poly[2][0]) / 2);
                const cy = cell.latitude || ((poly[0][1] + poly[2][1]) / 2);
                if (isNaN(cx) || isNaN(cy)) continue;
                const key = `${Math.round(cx * 111)}_${Math.round(cy * 111)}`;
                if (!gridMap.has(key)) gridMap.set(key, []);
                gridMap.get(key).push({ polygon: poly, cx, cy });
            }

            // Match each historical point to nearest grid cell
            const matched = new globalThis.Map();
            for (const pt of historicalPoints) {
                if (!pt.longitude || !pt.latitude) continue;
                let bestCell = null, bestDist = Infinity;
                for (let dx = -1; dx <= 1; dx++) {
                    for (let dy = -1; dy <= 1; dy++) {
                        const sk = `${Math.round(pt.longitude * 111) + dx}_${Math.round(pt.latitude * 111) + dy}`;
                        const bucket = gridMap.get(sk);
                        if (!bucket) continue;
                        for (const c of bucket) {
                            const dist = (c.cx - pt.longitude) ** 2 + (c.cy - pt.latitude) ** 2;
                            if (dist < bestDist) { bestDist = dist; bestCell = c; }
                        }
                    }
                }
                if (bestCell) {
                    const ck = `${bestCell.cx.toFixed(6)}_${bestCell.cy.toFixed(6)}`;
                    if (!matched.has(ck)) matched.set(ck, { polygon: bestCell.polygon, count: 0, tambons: new Set(), districts: new Set() });
                    const e = matched.get(ck);
                    e.count++;
                    if (pt.tambon) e.tambons.add(pt.tambon);
                    if (pt.district) e.districts.add(pt.district);
                }
            }

            return Array.from(matched.values()).map(e => ({
                polygon: e.polygon, count: e.count, isHistorical: true,
                tambons: Array.from(e.tambons).join(', '),
                districts: Array.from(e.districts).join(', '),
            }));
        } catch (err) {
            console.error('historicalGridCells error:', err);
            return [];
        }
    }, [historicalPoints, gridData]);
    const [selectedAlert, setSelectedAlert] = useState(null);
    // Chat state
    const [chatMessages, setChatMessages] = useState([
        { role: 'bot', text: 'สวัสดีครับ! ผมเป็นระบบ AI วิเคราะห์ความเสี่ยงดินถล่มจังหวัดน่าน\n\nลองถาม: **สรุป**, **พื้นที่เสี่ยงสูง**, **อ.ปัว**, **slope**, **ndvi**, **ฝน** หรือ **help**' }
    ]);
    const [chatInput, setChatInput] = useState('');
    const [chatLoading, setChatLoading] = useState(false);
    const logRef = useRef(null);
    const chatRef = useRef(null);

    const addLog = (msg) => {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
        setTimeout(() => logRef.current?.scrollTo(0, logRef.current.scrollHeight), 100);
    };

    useEffect(() => {
        fetch(`${API}/api/districts`).then(r => r.json()).then(setDistricts).catch(() => { });

        // ลองดึงข้อมูลทํานายล่าสุดมาก่อน ถ้ามีก็สบายเลย ไม่ต้องรอ predict ใหม่
        fetch(`${API}/api/predicted_data`).then(r => r.json()).then(data => {
            if (data && data.length > 0) {
                setGridData(data);
                setStatus(`Loaded ${data.length} predicted cells`);
                addLog(`Auto-loaded ${data.length} predicted cells`);
            } else {
                // ถ้ายังไม่มี predicted ให้ดึง grid เปล่าๆ มาก่อน
                fetch(`${API}/api/grid_data`).then(r => r.json()).then(grid => {
                    if (grid.length > 0) {
                        setGridData(grid);
                        setStatus(`${grid.length} raw cells loaded`);
                        addLog(`Auto-loaded ${grid.length} raw cells`);
                    }
                }).catch(() => { });
            }
        }).catch(() => { });

        fetchAlerts();

        // Fetch historical landslide points
        fetch(`${API}/api/historical_points`).then(r => r.json()).then(data => {
            if (Array.isArray(data)) { setHistoricalPoints(data); }
        }).catch(() => { });
    }, []);

    const buildLayers = useCallback((data, f, pin, histGridCells, showHist) => {
        const arr = [];
        arr.push(new PolygonLayer({
            id: 'risk-grid',
            data: data.filter(d => !d.risk || f[d.risk]),
            pickable: true, stroked: false,
            filled: true, extruded: false,
            getPolygon: d => d.polygon,
            getFillColor: d => RISK_COLORS[d.risk] || [128, 128, 128, 150],
            updateTriggers: { getFillColor: [f] }
        }));
        if (showHist && histGridCells.length > 0) {
            arr.push(new PolygonLayer({
                id: 'historical-grid',
                data: histGridCells,
                pickable: true,
                stroked: true,
                filled: true,
                extruded: false,
                getPolygon: d => d.polygon,
                getFillColor: [255, 180, 50, 160],
                getLineColor: [200, 130, 20, 255],
                getLineWidth: 2,
                lineWidthMinPixels: 1,
            }));
        }
        if (pin) {
            arr.push(new ScatterplotLayer({
                id: 'whatif-pin', data: [pin], pickable: false,
                getPosition: d => d, getFillColor: [255, 255, 255, 255],
                getRadius: 400, radiusMinPixels: 6, stroked: true,
                getLineColor: [0, 0, 0, 200], lineWidthMinPixels: 2,
            }));
        }
        return arr;
    }, []);

    useEffect(() => { setLayers(buildLayers(gridData, filters, whatIfPin, historicalGridCells, showHistorical)); }, [gridData, filters, whatIfPin, historicalGridCells, showHistorical, buildLayers]);

    const pollStatus = async () => {
        for (let i = 0; i < 200; i++) {
            await new Promise(r => setTimeout(r, 3000));
            try {
                const d = await (await fetch(`${API}/api/status`)).json();
                setStatus(d.message);
                if (d.status === 'done' || d.status === 'error') return d.status;
            } catch { }
        }
        return 'timeout';
    };

    const handleExtract = async () => {
        setLoading(true); setStatus('Starting...'); addLog('POST /api/extract_grid');
        try {
            await fetch(`${API}/api/extract_grid`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const fin = await pollStatus();
            if (fin === 'done') {
                const grid = await (await fetch(`${API}/api/grid_data`)).json();
                setGridData(grid); setStatus(`${grid.length} cells`); addLog(`Rendered ${grid.length} cells`); fetchAlerts();
            }
        } catch (e) { setStatus('Error'); addLog(`Error: ${e.message}`); }
        finally { setLoading(false); }
    };

    const handlePredictNow = async () => {
        setPredicting(true); setStatus('Fetching rainfall & predicting...'); addLog('POST /api/predict_now');
        try {
            const data = await (await fetch(`${API}/api/predict_now`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            })).json();
            if (data.summary) {
                addLog(`Done. Rain=${data.summary.rainfall_mm}mm High=${data.summary.high}`);
                setStatus(`Predicted. Rain=${data.summary.rainfall_mm}mm`);
                const pred = await (await fetch(`${API}/api/predicted_data`)).json();
                if (pred.length > 0) { setGridData(pred); addLog(`Updated map with ${pred.length} cells`); }
                fetchAlerts();
            }
        } catch (e) { addLog(`Error: ${e.message}`); }
        finally { setPredicting(false); }
    };

    const handleMapClick = (info) => {
        if (!whatIfMode || !info.coordinate) return;
        setWhatIfPin(info.coordinate); setWhatIfResult(null);
        addLog(`Pin: ${info.coordinate[0].toFixed(4)}, ${info.coordinate[1].toFixed(4)}`);
    };

    const runWhatIf = async () => {
        if (!whatIfPin) return;
        setPredicting(true); addLog(`What-If: rain 10 days array`);
        try {
            const data = await (await fetch(`${API}/api/whatif`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat: whatIfPin[1], lon: whatIfPin[0], rainfall_days: whatIfRainDays })
            })).json();
            setWhatIfResult(data); addLog(`Result: ${data.prediction?.risk || data.error}`);
        } catch (e) { addLog(`Error: ${e.message}`); }
        finally { setPredicting(false); }
    };

    // Auto-search logic
    useEffect(() => {
        const timeoutId = setTimeout(async () => {
            if (searchQuery.trim().length > 0) {
                try {
                    const res = await (await fetch(`${API}/api/search?q=${encodeURIComponent(searchQuery)}`)).json();
                    setSearchResults(Array.isArray(res) ? res : []);
                } catch {
                    setSearchResults([]);
                }
            } else {
                setSearchResults([]);
            }
        }, 300);
        return () => clearTimeout(timeoutId);
    }, [searchQuery]);

    const handleSearch = async () => {
        if (!searchQuery.trim()) return;
        const results = await (await fetch(`${API}/api/search?q=${encodeURIComponent(searchQuery)}`)).json();
        if (results && results.length > 0) {
            const d = results[0];
            setViewState(v => ({ ...v, longitude: d.center[0], latitude: d.center[1], zoom: 11, transitionDuration: 800 }));
            addLog(`Zoomed to ${d.name_en}`);
            setSearchResults([]);
        } else addLog(`No results`);
    };

    const handleSelectSearch = (d) => {
        setViewState(v => ({ ...v, longitude: d.center[0], latitude: d.center[1], zoom: 13, transitionDuration: 1000 }));
        addLog(`Zoomed to ${d.name_en}`);
        setSearchQuery(d.name_th);
        setSearchResults([]);
    };

    const fetchAlerts = async () => { try { setAlerts(await (await fetch(`${API}/api/alerts`)).json()); } catch { } };

    const fetchHistory = async () => {
        setHistoryLoading(true);
        try {
            let url = `${API}/api/alert_history?`;
            if (historyStart) url += `start_date=${historyStart}&`;
            if (historyEnd) url += `end_date=${historyEnd}`;
            const res = await fetch(url);
            if (!res.ok) {
                console.error("Backend returned error:", res.status);
                setHistoryAlerts([]);
                return;
            }
            const data = await res.json();
            setHistoryAlerts(Array.isArray(data) ? data : []);
        } catch (e) {
            console.error("Failed to fetch history:", e);
            setHistoryAlerts([]);
        }
        finally { setHistoryLoading(false); }
    };

    const toggleFilter = (l) => setFilters(p => ({ ...p, [l]: !p[l] }));

    // Chat
    const sendChat = async () => {
        if (!chatInput.trim()) return;
        const msg = chatInput.trim();
        setChatInput('');
        setChatMessages(prev => [...prev, { role: 'user', text: msg }]);
        setChatLoading(true);
        try {
            const data = await (await fetch(`${API}/api/chat`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            })).json();
            setChatMessages(prev => [...prev, { role: 'bot', text: data.answer }]);
        } catch (e) {
            setChatMessages(prev => [...prev, { role: 'bot', text: `Error: ${e.message}` }]);
        }
        finally { setChatLoading(false); }
        setTimeout(() => chatRef.current?.scrollTo(0, chatRef.current.scrollHeight), 100);
    };

    const stats = {
        total: gridData.length, high: gridData.filter(d => d.risk === 'High').length,
        med: gridData.filter(d => d.risk === 'Medium').length, low: gridData.filter(d => d.risk === 'Low').length,
    };

    const S = {
        sidebar: {
            position: 'absolute', top: 0, left: 0, bottom: 0, zIndex: 10, width: 360,
            background: 'linear-gradient(180deg, #0f0f1a 0%, #111827 100%)',
            color: '#fff', display: 'flex', flexDirection: 'column',
            fontFamily: "'Inter','Segoe UI',sans-serif",
            borderRight: '1px solid rgba(255,255,255,0.06)',
            boxShadow: '4px 0 24px rgba(0,0,0,0.4)',
        },
        tab: (a) => ({
            flex: 1, padding: '7px 0', border: 'none', cursor: 'pointer',
            background: a ? 'rgba(59,130,246,0.15)' : 'transparent',
            color: a ? '#60a5fa' : '#6b7280',
            borderBottom: a ? '2px solid #3b82f6' : '2px solid transparent',
            fontSize: 10, fontWeight: 600
        }),
        input: {
            width: '100%', padding: '7px 10px', borderRadius: 6,
            border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)',
            color: '#fff', fontSize: 12, outline: 'none', boxSizing: 'border-box'
        },
        label: { fontSize: 10, color: '#6b7280', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 },
        btn: (bg) => ({
            width: '100%', padding: '9px 0', marginBottom: 10, borderRadius: 6,
            border: 'none', cursor: 'pointer', background: bg, color: '#fff',
            fontSize: 12, fontWeight: 600, transition: 'all 0.2s'
        }),
    };

    const riskColor = (r) => r === 'High' ? '#ef4444' : r === 'Medium' ? '#f97316' : '#71717a';

    return (
        <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
            <DeckGL viewState={viewState} onViewStateChange={({ viewState: v }) => setViewState(v)}
                onClick={handleMapClick} controller={true} layers={layers}
                getCursor={() => whatIfMode ? 'crosshair' : 'grab'}
                getTooltip={({ object }) => {
                    if (!object) return null;

                    // Historical grid cell tooltip
                    if (object.isHistorical) {
                        let html = `<div style="font:11px monospace;line-height:1.6;max-width:220px;">`;
                        html += `<b style="color:#fbbf24;font-size:13px;">📍 จุดดินถล่มในอดีต</b><br/>`;
                        html += `<span style="color:#aaa;">จำนวนเหตุการณ์:</span> <b>${object.count}</b><br/>`;
                        if (object.tambons) html += `<span style="color:#aaa;">ตำบล:</span> ${object.tambons}<br/>`;
                        if (object.districts) html += `<span style="color:#aaa;">อำเภอ:</span> ${object.districts}`;
                        html += `</div>`;
                        return { html, style: { background: 'rgba(20,20,30,0.95)', color: '#eee', borderRadius: 8, padding: 10, border: '1px solid #b45309', backdropFilter: 'blur(4px)' } };
                    }

                    const props = object.properties || {};
                    let tooltipHtml = `<div style="font:11px monospace;line-height:1.5;max-width:250px;">`;
                    if (object.risk) {
                        tooltipHtml += `<b style="color:${riskColor(object.risk)};font-size:13px;">● ${object.risk} Risk</b>`;
                        if (object.probability !== undefined) {
                            tooltipHtml += ` <span style="color:#aaa;">(${(object.probability * 100).toFixed(1)}%)</span><br/>`;
                        } else {
                            tooltipHtml += `<br/>`;
                        }
                    } else {
                        tooltipHtml += `<b style="color:#aaa;font-size:13px;">● Unknown Risk</b><br/>`;
                    }
                    tooltipHtml += `<div style="margin-top:4px;border-top:1px solid #333;padding-top:4px;display:grid;grid-template-columns:1fr 1fr;gap:4px;">`;

                    for (const [key, value] of Object.entries(props)) {
                        let displayValue = value;
                        if (typeof value === 'number') {
                            displayValue = value % 1 === 0 ? value : value.toFixed(2);
                        }
                        tooltipHtml += `<div><span style="color:#888;">${key}:</span> ${displayValue}</div>`;
                    }
                    tooltipHtml += `</div></div>`;

                    return {
                        html: tooltipHtml,
                        style: { background: 'rgba(20,20,30,0.95)', color: '#eee', borderRadius: 8, padding: 10, border: '1px solid #444', backdropFilter: 'blur(4px)' }
                    };
                }}>
                <Map mapStyle={MAP_STYLES[mapStyle].url} />
            </DeckGL>

            {/* ──── MAP STYLE SELECTOR ──── */}
            <div style={{
                position: 'absolute', bottom: 24, right: 24, zIndex: 20,
                fontFamily: "'Inter','Segoe UI',sans-serif",
            }}>
                {/* Collapsed button */}
                {!styleMenuOpen && (
                    <button
                        onClick={() => setStyleMenuOpen(true)}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '10px 16px', borderRadius: 12,
                            border: '1px solid rgba(255,255,255,0.15)',
                            background: 'rgba(15,15,26,0.85)', backdropFilter: 'blur(12px)',
                            color: '#e5e7eb', cursor: 'pointer', fontSize: 13, fontWeight: 600,
                            boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
                            transition: 'all 0.2s',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(59,130,246,0.2)'; e.currentTarget.style.borderColor = 'rgba(59,130,246,0.4)'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'rgba(15,15,26,0.85)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'; }}
                    >
                        🗺️ {MAP_STYLES[mapStyle].label.split(' ').slice(1).join(' ')}
                    </button>
                )}

                {/* Expanded panel */}
                {styleMenuOpen && (
                    <div style={{
                        background: 'rgba(15,15,26,0.92)', backdropFilter: 'blur(16px)',
                        borderRadius: 16, padding: 16,
                        border: '1px solid rgba(255,255,255,0.1)',
                        boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                        minWidth: 280,
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                            <span style={{ fontSize: 13, fontWeight: 700, color: '#e5e7eb' }}>🗺️ Map Style</span>
                            <button
                                onClick={() => setStyleMenuOpen(false)}
                                style={{
                                    background: 'rgba(255,255,255,0.08)', border: 'none',
                                    color: '#9ca3af', cursor: 'pointer', borderRadius: 6,
                                    width: 28, height: 28, fontSize: 14, display: 'flex',
                                    alignItems: 'center', justifyContent: 'center',
                                    transition: 'all 0.2s',
                                }}
                                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.2)'; e.currentTarget.style.color = '#ef4444'; }}
                                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#9ca3af'; }}
                            >
                                ✕
                            </button>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                            {Object.entries(MAP_STYLES).map(([key, style]) => {
                                const isActive = mapStyle === key;
                                const colors = {
                                    dark: ['#1a1a2e', '#16213e', '#0f3460'],
                                    light: ['#f8f9fa', '#e9ecef', '#dee2e6'],
                                    streets: ['#e8d5b7', '#b8d4e3', '#a8c686'],
                                    terrain: ['#c8d6a0', '#a3b87c', '#8fae6b'],
                                    satellite: ['#2d4a2d', '#3a5f3a', '#1a3a1a'],
                                };
                                const c = colors[key] || colors.dark;
                                return (
                                    <button
                                        key={key}
                                        onClick={() => { setMapStyle(key); setStyleMenuOpen(false); }}
                                        style={{
                                            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                                            padding: 10, borderRadius: 12, cursor: 'pointer',
                                            border: isActive ? '2px solid #3b82f6' : '2px solid rgba(255,255,255,0.08)',
                                            background: isActive ? 'rgba(59,130,246,0.1)' : 'rgba(255,255,255,0.03)',
                                            transition: 'all 0.2s',
                                        }}
                                        onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; } }}
                                        onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; } }}
                                    >
                                        {/* Mini preview */}
                                        <div style={{
                                            width: '100%', height: 52, borderRadius: 8,
                                            background: `linear-gradient(135deg, ${c[0]}, ${c[1]}, ${c[2]})`,
                                            position: 'relative', overflow: 'hidden',
                                            boxShadow: isActive ? '0 0 12px rgba(59,130,246,0.3)' : 'none',
                                        }}>
                                            {/* Decorative lines to mimic map features */}
                                            <svg width="100%" height="100%" viewBox="0 0 100 52" style={{ position: 'absolute', opacity: 0.35 }}>
                                                <path d="M10 35 Q30 15 50 25 T90 20" fill="none" stroke={key === 'light' ? '#666' : '#fff'} strokeWidth="1.5" />
                                                <path d="M5 45 Q25 30 45 40 T95 35" fill="none" stroke={key === 'light' ? '#666' : '#fff'} strokeWidth="1" />
                                                <circle cx="70" cy="15" r="3" fill={key === 'light' ? '#666' : '#fff'} opacity="0.5" />
                                                <circle cx="30" cy="38" r="2" fill={key === 'light' ? '#666' : '#fff'} opacity="0.4" />
                                            </svg>
                                        </div>
                                        <span style={{
                                            fontSize: 11, fontWeight: isActive ? 700 : 500,
                                            color: isActive ? '#60a5fa' : '#9ca3af',
                                        }}>
                                            {style.label}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>

            <div style={S.sidebar}>
                {/* Header */}
                <div style={{ padding: '14px 20px 10px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>🛡️ Landslide Early Warning</h1>
                        <p style={{ margin: '2px 0 0', fontSize: 10, color: '#6b7280' }}>Nan Province Dashboard {user ? `(Officer: ${user.username})` : ''}</p>
                    </div>
                    <button onClick={logout} style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 4, padding: '4px 8px', fontSize: 10, cursor: 'pointer', transition: 'all 0.2s' }}>
                        Logout
                    </button>
                </div>

                {/* Tabs */}
                <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {[['map', '🗺️ Map'], ['whatif', '🎯 What-If'], ['alerts', '🔔 Alerts'], ['history', '📅 History']].map(([k, l]) => (
                        <button key={k} style={S.tab(tab === k)} onClick={() => { setTab(k); if (k === 'alerts') fetchAlerts(); if (k === 'history') fetchHistory(); }}>
                            {l}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div style={{ padding: '12px 20px', flex: 1, overflowY: 'auto' }}>

                    {/* ──── MAP TAB ──── */}
                    {tab === 'map' && (<>
                        <div style={{ fontSize: 12, marginBottom: 10, color: '#9ca3af' }}>
                            Status: <span style={{ color: loading ? '#facc15' : '#4ade80', fontWeight: 600 }}>{status}</span>
                        </div>
                        <button onClick={handleExtract} disabled={loading} style={S.btn(loading ? '#374151' : 'linear-gradient(135deg,#3b82f6,#6366f1)')}>
                            {loading ? '⏳ Extracting...' : '🚀 Extract GEE'}
                        </button>
                        <button onClick={handlePredictNow} disabled={predicting} style={S.btn(predicting ? '#374151' : 'linear-gradient(135deg,#f59e0b,#ef4444)')}>
                            {predicting ? '⏳ Predicting...' : '⚡ Fetch Rainfall & Predict Now'}
                        </button>

                        {stats.total > 0 && (
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 4, marginBottom: 12 }}>
                                {[['Total', stats.total, '#1e293b'], ['High', stats.high, 'rgba(255,40,40,0.12)'],
                                ['Med', stats.med, 'rgba(255,165,0,0.1)'], ['Low', stats.low, 'rgba(113,113,122,0.1)']].map(([l, v, bg]) => (
                                    <div key={l} style={{ background: bg, borderRadius: 6, padding: '5px 0', textAlign: 'center', fontSize: 10 }}>
                                        <div style={{ fontWeight: 700, fontSize: 14 }}>{v.toLocaleString()}</div>
                                        <div style={{ color: '#6b7280' }}>{l}</div>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div style={S.label}>Risk Filters</div>
                        <div style={{ marginBottom: 10 }}>
                            {['High', 'Medium', 'Low'].map(l => (
                                <label key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, marginBottom: 2, cursor: 'pointer', color: '#ccc' }}>
                                    <input type="checkbox" checked={filters[l]} onChange={() => toggleFilter(l)} />
                                    <span style={{ width: 10, height: 10, borderRadius: 2, background: `rgba(${RISK_COLORS[l].join(',')})` }} />{l}
                                </label>
                            ))}
                        </div>

                        <div style={S.label}>Overlay Layers</div>
                        <div style={{ marginBottom: 10 }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, cursor: 'pointer', color: '#ccc' }}>
                                <input type="checkbox" checked={showHistorical} onChange={() => setShowHistorical(v => !v)} />
                                <span style={{ width: 10, height: 10, borderRadius: 2, background: 'rgba(255,180,50,0.85)' }} />
                                📍 จุดดินถล่มในอดีต ({historicalGridCells.length} กริด)
                            </label>
                        </div>

                        <div style={S.label}>Search District / Sub-district</div>
                        <div style={{ display: 'flex', gap: 4, marginBottom: 6, position: 'relative' }}>
                            <input style={{ ...S.input, flex: 1 }} placeholder="ค้นหาอำเภอ หรือ ตำบล..." value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()} />
                            <button onClick={handleSearch} style={{ padding: '0 10px', borderRadius: 6, border: 'none', background: '#3b82f6', color: '#fff', cursor: 'pointer', fontSize: 11 }}>🔍</button>

                            {/* Search Results Dropdown */}
                            {searchResults.length > 0 && (
                                <div style={{
                                    position: 'absolute', top: 34, left: 0, right: 40,
                                    background: '#1f2937', borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                                    zIndex: 50, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)'
                                }}>
                                    {searchResults.map((res, idx) => (
                                        <div key={idx}
                                            onClick={() => handleSelectSearch(res)}
                                            style={{
                                                padding: '8px 12px', cursor: 'pointer', fontSize: 12,
                                                borderBottom: idx < searchResults.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                                                display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                                            }}
                                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(59,130,246,0.15)'}
                                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                        >
                                            <div>
                                                <div style={{ color: 'white' }}>{res.name_th}</div>
                                                <div style={{ color: '#9ca3af', fontSize: 10 }}>{res.name_en}</div>
                                            </div>
                                            <div style={{
                                                fontSize: 10, padding: '2px 6px', borderRadius: 10,
                                                background: res.type === 'tambon' ? '#10b981' : '#3b82f6',
                                                color: 'white', fontWeight: 'bold'
                                            }}>
                                                {res.type === 'tambon' ? 'ตำบล' : 'อำเภอ'}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div style={{ maxHeight: 80, overflowY: 'auto', marginBottom: 10 }}>
                            {districts.map(d => (
                                <div key={d.name_en} onClick={() => { setViewState(v => ({ ...v, longitude: d.center[0], latitude: d.center[1], zoom: 11, transitionDuration: 800 })); addLog(`→ ${d.name_en}`); }}
                                    style={{ padding: '3px 6px', borderRadius: 3, cursor: 'pointer', fontSize: 10, color: '#9ca3af', display: 'flex', justifyContent: 'space-between' }}
                                    onMouseEnter={e => { e.currentTarget.style.background = 'rgba(59,130,246,0.1)'; e.currentTarget.style.color = '#60a5fa'; }}
                                    onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#9ca3af'; }}>
                                    <span>{d.name_th}</span><span>{d.name_en}</span>
                                </div>
                            ))}
                        </div>

                        <div style={S.label}>Console</div>
                        <div ref={logRef} style={{ background: 'rgba(0,0,0,0.4)', borderRadius: 6, padding: 6, fontSize: 9, fontFamily: 'monospace', height: 70, overflowY: 'auto', color: '#6b7280' }}>
                            {logs.length === 0 ? <span>Waiting...</span> : logs.map((l, i) => <div key={i} style={{ marginBottom: 1 }}>{`> ${l}`}</div>)}
                        </div>
                    </>)}

                    {/* ──── WHAT-IF TAB ──── */}
                    {tab === 'whatif' && (<>
                        <div style={S.label}>What-If Simulation</div>
                        <p style={{ fontSize: 11, color: '#9ca3af', margin: '0 0 12px' }}>Click map → set rainfall → predict risk</p>
                        <button onClick={() => setWhatIfMode(!whatIfMode)}
                            style={{ ...S.btn(whatIfMode ? '#ef4444' : 'linear-gradient(135deg,#8b5cf6,#6366f1)'), marginBottom: 14 }}>
                            {whatIfMode ? '❌ Cancel Pin Mode' : '📌 Click Map to Set Point'}
                        </button>
                        {whatIfPin && (
                            <div style={{ marginBottom: 12 }}>
                                <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 6 }}>📍 {whatIfPin[0].toFixed(5)}, {whatIfPin[1].toFixed(5)}</div>
                                <div style={S.label}>Rainfall (mm) - Past 10 Days</div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px', marginBottom: 12 }}>
                                    {whatIfRainDays.map((val, idx) => (
                                        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                            <span style={{ fontSize: 10, color: '#9ca3af', width: 35 }}>Day {10 - idx}:</span>
                                            <input
                                                type="number"
                                                value={val === 0 ? '' : val}
                                                placeholder="0"
                                                onChange={e => {
                                                    const newArr = [...whatIfRainDays];
                                                    newArr[idx] = Number(e.target.value);
                                                    setWhatIfRainDays(newArr);
                                                }}
                                                style={{ ...S.input, padding: '4px 6px', marginBottom: 0 }}
                                            />
                                        </div>
                                    ))}
                                </div>
                                <button onClick={runWhatIf} disabled={predicting} style={S.btn(predicting ? '#374151' : 'linear-gradient(135deg,#f59e0b,#ef4444)')}>
                                    {predicting ? '⏳...' : '⚡ Predict This Point'}
                                </button>
                            </div>
                        )}
                        {whatIfResult?.prediction && (
                            <div style={{
                                padding: 14, borderRadius: 8, background: `rgba(${RISK_COLORS[whatIfResult.prediction.risk]?.join(',')?.replace(/,\d+$/, ',0.08')})`,
                                border: `1px solid ${riskColor(whatIfResult.prediction.risk)}`
                            }}>
                                <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8, color: riskColor(whatIfResult.prediction.risk) }}>
                                    ● {whatIfResult.prediction.risk} Risk
                                </div>
                                <div style={{ fontSize: 11, color: '#9ca3af', lineHeight: 1.8 }}>
                                    Probability: {(whatIfResult.prediction.probability * 100).toFixed(1)}%<br />
                                    Total 10D Rain: {whatIfResult.rainfall_total?.toFixed(1)} mm<br />
                                    Slope: {whatIfResult.features?.Slope?.toFixed(1)}°<br />
                                    Elevation: {whatIfResult.features?.Elevation?.toFixed(0)}m
                                </div>
                            </div>
                        )}
                        {whatIfResult?.error && <div style={{ padding: 10, borderRadius: 6, background: 'rgba(239,68,68,0.1)', color: '#ef4444', fontSize: 12 }}>Error: {whatIfResult.error}</div>}
                    </>)}

                    {/* ──── CHAT BLOCK MOVED TO BOTTOM ──── */}

                    {/* ──── ALERTS TAB ──── */}
                    {tab === 'alerts' && (<>
                        <div style={S.label}>Critical Area Alerts ({MAPPED_ALERTS.length})</div>
                        {MAPPED_ALERTS.length === 0 ? <p style={{ fontSize: 12, color: '#4b5563' }}>No alerts yet.</p> :
                            MAPPED_ALERTS.map((a, idx) => {
                                // Reverse geocode: find nearest tambon and inherit its amphoe to avoid mismatch
                                const lat = a.latitude || 0;
                                const lon = a.longitude || 0;
                                let alertTitle = "ไม่ทราบตำแหน่ง";
                                let alertSubtitle = "จ.น่าน (Nan Province)";

                                if (lat && lon) {
                                    let bestDist = Infinity;
                                    let bestTambon = null;
                                    for (const t of NAN_TAMBONS) {
                                        const dist = (lon - t.c[0]) ** 2 + (lat - t.c[1]) ** 2;
                                        if (dist < bestDist) { bestDist = dist; bestTambon = t; }
                                    }

                                    // Bounding box for Nan province approx (Lat 18.0-19.7, Lon 100.3-101.4)
                                    const isOutsideBounds = (lat < 18.0 || lat > 19.7 || lon < 100.3 || lon > 101.4);

                                    // Check distance threshold (0.05 deg^2 is roughly 15-20km)
                                    if (bestTambon && !isOutsideBounds && bestDist < 0.05) {
                                        // Translate English Amphoe back to Thai if possible
                                        let amphoeTh = bestTambon.a;
                                        const dMatch = districts.find(d => d.name_en === bestTambon.a);
                                        if (dMatch) amphoeTh = dMatch.name_th;
                                        alertTitle = `ต.${bestTambon.n} อ.${amphoeTh}`;
                                    } else {
                                        alertTitle = "นอกเขตจังหวัดน่าน / ประเทศเพื่อนบ้าน";
                                        alertSubtitle = "Outside Nan / Laos";
                                    }
                                }

                                // Risk-based colors
                                const bgColor = a.risk === 'High' ? 'rgba(239,68,68,0.15)'
                                    : a.risk === 'Medium' ? 'rgba(250,204,21,0.12)' : 'rgba(120,120,130,0.10)';
                                const borderColor = a.risk === 'High' ? '#ef4444'
                                    : a.risk === 'Medium' ? '#facc15' : '#6b7280';
                                const titleColor = a.risk === 'High' ? '#fca5a5'
                                    : a.risk === 'Medium' ? '#fde047' : '#a1a1aa';

                                return (
                                    <div key={idx}
                                        onClick={() => {
                                            if (lat && lon) {
                                                setViewState(v => ({ ...v, longitude: lon, latitude: lat, zoom: 14, transitionDuration: 1000 }));
                                                setSelectedAlert(a);
                                            }
                                        }}
                                        style={{
                                            padding: '8px 10px', marginBottom: 6, borderRadius: 6, fontSize: 11,
                                            background: bgColor, borderLeft: `3px solid ${borderColor}`,
                                            cursor: 'pointer', transition: 'all 0.15s',
                                        }}
                                        onMouseEnter={e => e.currentTarget.style.opacity = '0.8'}
                                        onMouseLeave={e => e.currentTarget.style.opacity = '1'}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                                            <b style={{ color: titleColor }}>{alertTitle}</b>
                                            <span style={{
                                                fontSize: 10, fontWeight: 700, color: titleColor,
                                                background: `${borderColor}22`, padding: '1px 6px', borderRadius: 4
                                            }}>{Math.round((a.probability || 0) * 100)}%</span>
                                        </div>
                                        <div style={{ color: '#d1d5db', fontSize: 10 }}>
                                            Lat: {lat ? lat.toFixed(5) : 'N/A'}, Lon: {lon ? lon.toFixed(5) : 'N/A'}
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#6b7280', marginTop: 4 }}>
                                            <span>{a.risk} Risk - {alertSubtitle}</span>
                                        </div>
                                    </div>
                                );
                            })
                        }
                    </>)}

                    {/* ──── HISTORY TAB ──── */}
                    {tab === 'history' && (<>
                        <div style={S.label}>📅 Alert History (Top 200)</div>
                        <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
                            <div style={{ display: 'flex', gap: 6, flex: '1 1 auto' }}>
                                <input
                                    type="date"
                                    value={historyStart}
                                    onChange={e => setHistoryStart(e.target.value)}
                                    style={{
                                        flex: 1, padding: '7px 8px', fontSize: 11,
                                        background: 'rgba(15,15,26,0.6)', color: '#e5e7eb',
                                        border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8,
                                        outline: 'none', transition: 'all 0.2s', fontFamily: 'inherit',
                                        colorScheme: 'dark', minWidth: 0
                                    }}
                                    onFocus={e => e.currentTarget.style.borderColor = '#3b82f6'}
                                    onBlur={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'}
                                />
                                <span style={{ color: '#6b7280', alignSelf: 'center', fontWeight: 'bold' }}>-</span>
                                <input
                                    type="date"
                                    value={historyEnd}
                                    onChange={e => setHistoryEnd(e.target.value)}
                                    style={{
                                        flex: 1, padding: '7px 8px', fontSize: 11,
                                        background: 'rgba(15,15,26,0.6)', color: '#e5e7eb',
                                        border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8,
                                        outline: 'none', transition: 'all 0.2s', fontFamily: 'inherit',
                                        colorScheme: 'dark', minWidth: 0
                                    }}
                                    onFocus={e => e.currentTarget.style.borderColor = '#3b82f6'}
                                    onBlur={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'}
                                />
                            </div>
                            <button onClick={fetchHistory} disabled={historyLoading}
                                style={{
                                    background: historyLoading ? '#374151' : 'linear-gradient(135deg, #3b82f6, #6366f1)',
                                    color: 'white', border: 'none', borderRadius: 8, padding: '7px 14px',
                                    fontSize: 11, fontWeight: 600, cursor: historyLoading ? 'not-allowed' : 'pointer',
                                    boxShadow: '0 2px 8px rgba(59,130,246,0.25)', transition: 'all 0.2s',
                                    flex: '0 0 auto'
                                }}
                                onMouseEnter={e => { if (!historyLoading) e.currentTarget.style.filter = 'brightness(1.1)'; }}
                                onMouseLeave={e => { if (!historyLoading) e.currentTarget.style.filter = 'brightness(1)'; }}
                            >
                                {historyLoading ? '...' : 'Filter'}
                            </button>
                        </div>

                        {historyAlerts.length === 0 && !historyLoading ? <p style={{ fontSize: 12, color: '#4b5563' }}>No historical alerts found.</p> :
                            historyAlerts.slice(0, 200).map((a, idx) => {
                                // Logic to get Tambon/Amphoe
                                const lat = a.latitude || 0;
                                const lon = a.longitude || 0;
                                let alertTitle = "ไม่ทราบตำแหน่ง";
                                let alertSubtitle = "จ.น่าน (Nan Province)";

                                if (lat && lon) {
                                    let bestDist = Infinity;
                                    let bestTambon = null;
                                    for (const t of NAN_TAMBONS) {
                                        const dist = (lon - t.c[0]) ** 2 + (lat - t.c[1]) ** 2;
                                        if (dist < bestDist) { bestDist = dist; bestTambon = t; }
                                    }

                                    const isOutsideBounds = (lat < 18.0 || lat > 19.7 || lon < 100.3 || lon > 101.4);
                                    if (bestTambon && !isOutsideBounds && bestDist < 0.05) {
                                        let amphoeTh = bestTambon.a;
                                        const dMatch = districts.find(d => d.name_en === bestTambon.a);
                                        if (dMatch) amphoeTh = dMatch.name_th;
                                        alertTitle = `ต.${bestTambon.n} อ.${amphoeTh}`;
                                    } else {
                                        alertTitle = "นอกเขตจังหวัดน่าน / ประเทศเพื่อนบ้าน";
                                        alertSubtitle = "Outside Nan / Laos";
                                    }
                                }

                                // Risk-based colors
                                const bgColor = a.risk === 'High' ? 'rgba(239,68,68,0.15)'
                                    : a.risk === 'Medium' ? 'rgba(250,204,21,0.12)' : 'rgba(120,120,130,0.10)';
                                const borderColor = a.risk === 'High' ? '#ef4444'
                                    : a.risk === 'Medium' ? '#facc15' : '#6b7280';
                                const titleColor = a.risk === 'High' ? '#fca5a5'
                                    : a.risk === 'Medium' ? '#fde047' : '#a1a1aa';

                                return (
                                    <div key={idx}
                                        onClick={() => {
                                            if (lat && lon) {
                                                setViewState(v => ({ ...v, longitude: lon, latitude: lat, zoom: 14, transitionDuration: 1000 }));
                                                setSelectedAlert(a);
                                            }
                                        }}
                                        style={{
                                            padding: '8px 10px', marginBottom: 6, borderRadius: 6, fontSize: 11,
                                            background: bgColor, borderLeft: `3px solid ${borderColor}`,
                                            cursor: 'pointer', transition: 'all 0.15s',
                                        }}
                                        onMouseEnter={e => e.currentTarget.style.opacity = '0.8'}
                                        onMouseLeave={e => e.currentTarget.style.opacity = '1'}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                                            <b style={{ color: titleColor }}>{alertTitle}</b>
                                            <span style={{
                                                fontSize: 10, fontWeight: 700, color: titleColor,
                                                background: `${borderColor}22`, padding: '1px 6px', borderRadius: 4
                                            }}>{Math.round((a.probability || 0) * 100)}%</span>
                                        </div>
                                        <div style={{ color: '#d1d5db', fontSize: 10 }}>
                                            Lat: {lat ? lat.toFixed(5) : 'N/A'}, Lon: {lon ? lon.toFixed(5) : 'N/A'}
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#6b7280', marginTop: 4 }}>
                                            <span>{a.risk} Risk - {alertSubtitle}</span>
                                            <span style={{ color: '#9ca3af', background: 'rgba(255,255,255,0.1)', padding: '1px 4px', borderRadius: 3 }}>🕒 {new Date(a.timestamp).toLocaleString('th-TH', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                                        </div>
                                    </div>
                                );
                            })
                        }
                    </>)}

                </div>

                {/* ──── PERSISTENT CHAT ──── */}
                <div style={{ padding: '12px 20px', borderTop: '1px solid rgba(255,255,255,0.06)', background: 'rgba(0,0,0,0.2)' }}>
                    <div style={{ ...S.label, marginBottom: 8 }}>💬 AI Assistant</div>
                    <div ref={chatRef} style={{
                        height: 200, overflowY: 'auto', marginBottom: 10,
                        background: 'rgba(0,0,0,0.3)', borderRadius: 8, padding: 10
                    }}>
                        {chatMessages.map((m, i) => (
                            <div key={i} style={{
                                marginBottom: 10, display: 'flex',
                                justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start'
                            }}>
                                <div style={{
                                    maxWidth: '85%', padding: '8px 12px', borderRadius: 10,
                                    background: m.role === 'user' ? 'rgba(59,130,246,0.25)' : 'rgba(255,255,255,0.06)',
                                    color: m.role === 'user' ? '#93c5fd' : '#d1d5db',
                                    fontSize: 12, lineHeight: 1.6,
                                    borderBottomRightRadius: m.role === 'user' ? 2 : 10,
                                    borderBottomLeftRadius: m.role === 'bot' ? 2 : 10,
                                    whiteSpace: 'pre-wrap'
                                }}>
                                    {m.text.split('**').map((part, j) =>
                                        j % 2 === 0 ? part : <b key={j}>{part}</b>
                                    )}
                                </div>
                            </div>
                        ))}
                        {chatLoading && (
                            <div style={{ fontSize: 11, color: '#6b7280', padding: '4px 8px' }}>🤖 กำลังคิด...</div>
                        )}
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                        <input style={{ ...S.input, flex: 1 }} placeholder="ถามอะไรก็ได้..."
                            value={chatInput} onChange={e => setChatInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && sendChat()} />
                        <button onClick={sendChat} disabled={chatLoading} style={{
                            padding: '0 14px', borderRadius: 6, border: 'none',
                            background: chatLoading ? '#374151' : '#3b82f6',
                            color: '#fff', cursor: 'pointer', fontSize: 12
                        }}>➤</button>
                    </div>
                </div>

            </div>
        </div>
    );
}
