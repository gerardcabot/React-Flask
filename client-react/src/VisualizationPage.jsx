import { useEffect, useState, useRef } from "react";
import axios from "axios";
import {
    Chart, 
    CategoryScale,
    LinearScale,
    ArcElement,
    BarElement,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { FaUser, FaCalendarAlt, FaChartBar } from "react-icons/fa"; 

Chart.register(CategoryScale, LinearScale, ArcElement, BarElement, PointElement, LineElement, Title, Tooltip, Legend, Filler);

import PassMap from "./components/PassMap";
import ShotMap from "./components/ShotMap";
import PositionHeatmap from "./components/PositionHeatmap";
import PressureHeatmap from "./components/PressureHeatmap";

function InfoTooltip({ text }) {
return (
<span style={{ marginLeft: '8px', cursor: 'pointer', color: '#1070CA' }} title={text}>
ℹ️
</span>
);
}

function CustomVisualizationChart({ id, chartType, chartDataConfig, chartOptions, chartRefs }) {
useEffect(() => {
const canvas = document.getElementById(`chart-${id}`);
if (!canvas) return;
const ctx = canvas.getContext("2d");

if (chartRefs.current[id]) {
  chartRefs.current[id].destroy();
}
chartRefs.current[id] = new Chart(ctx, { type: chartType, data: chartDataConfig, options: chartOptions });

return () => {
  if (chartRefs.current[id]) {
    chartRefs.current[id].destroy();
    delete chartRefs.current[id]; 
  }
};
}, [id, chartType, chartDataConfig, chartOptions, chartRefs]);

return <canvas id={`chart-${id}`}></canvas>;
}

function ImageModal({ src, alt, onClose }) {
if (!src) return null;
return (
<div
style={{
position: "fixed",
zIndex: 1000,
left: 0,
top: 0,
width: "100vw",
height: "100vh",
background: "rgba(0,0,0,0.7)",
display: "flex",
alignItems: "center",
justifyContent: "center",
}}
onClick={onClose}
>
<img
src={src}
alt={alt}
style={{
maxWidth: "90vw",
maxHeight: "90vh",
border: "4px solid #fff",
borderRadius: 8,
boxShadow: "0 0 24px #000",
background: "#fff",
}}
onClick={e => e.stopPropagation()}
/>
</div>
);
}

function VisualizationPage() {
const [players, setPlayers] = useState([]);
const [selectedPlayer, setSelectedPlayer] = useState(null);
const [selectedSeason, setSelectedSeason] = useState("");
const [events, setEvents] = useState([]);
const [selectedStandardViz, setSelectedStandardViz] = useState("passmap");
const [loadingEvents, setLoadingEvents] = useState(false);
const [selectedGKSubViz, setSelectedGKSubViz] = useState("summaryAndCharts");
const [modalImg, setModalImg] = useState(null);
const [gkAnalysisData, setGkAnalysisData] = useState(null);
const [loadingGkAnalysis, setLoadingGkAnalysis] = useState(false);
const [availableEventTypes, setAvailableEventTypes] = useState([]);
const [availableAggregatedMetrics, setAvailableAggregatedMetrics] = useState([]);
const [selectedAggregatedMetric, setSelectedAggregatedMetric] = useState('');
const [aggregatedMetricData, setAggregatedMetricData] = useState(null);
const [loadingAggregatedMetric, setLoadingAggregatedMetric] = useState(false);
const chartRefs = useRef({});

useEffect(() => {
axios.get("http://localhost:5000/players").then(res => setPlayers(res.data)).catch(err => console.error("Error fetching players:", err));
}, []);

useEffect(() => {
if (selectedPlayer && selectedSeason) {
  setLoadingEvents(true);
  setAvailableEventTypes([]);

  axios.get(`http://localhost:5000/player_events`, {
    params: { player_id: selectedPlayer.player_id, season: selectedSeason }
  }).then(res => {
    setEvents(res.data || []);
    if (Array.isArray(res.data) && res.data.length > 0) {
      const types = new Set();
      res.data.forEach(event => {
        if (event.type) {
          if (typeof event.type === 'object' && event.type.name) {
            types.add(event.type.name);
          } else if (typeof event.type === 'string') {
            types.add(event.type);
          }
        }
      });
      setAvailableEventTypes(Array.from(types).sort());
    }
    setLoadingEvents(false);
  }).catch(err => {
    console.error("Error fetching events:", err);
    setEvents([]);
    setLoadingEvents(false);
  });

} else {
  setEvents([]);
  setAvailableEventTypes([]);
}

}, [selectedPlayer, selectedSeason]);

useEffect(() => {
if (selectedPlayer && selectedSeason && selectedSeason !== "all" && selectedStandardViz === "shotsavemap") {
setLoadingGkAnalysis(true);
setGkAnalysisData(null);
axios.get(`http://localhost:5000/api/player/${selectedPlayer.player_id}/goalkeeper/analysis/${selectedSeason}`)
.then(res => { setGkAnalysisData(res.data); setLoadingGkAnalysis(false); })
.catch(err => { console.error("Error fetching goalkeeper analysis:", err); setGkAnalysisData({ error: "No s'ha pogut carregar l'anàlisi" }); setLoadingGkAnalysis(false); });
} else {
setGkAnalysisData(null);
}
}, [selectedPlayer, selectedSeason, selectedStandardViz]);

useEffect(() => {
if (availableAggregatedMetrics.length === 0) {
axios.get("http://localhost:5000/available_aggregated_metrics")
.then(res => setAvailableAggregatedMetrics(res.data.available_metrics || []))
.catch(err => console.error("Error fetching available aggregated metrics:", err));
}
}, [availableAggregatedMetrics.length]);

useEffect(() => {
  if (selectedPlayer && selectedAggregatedMetric && selectedSeason !== "") {
    setLoadingAggregatedMetric(true);
    setAggregatedMetricData(null);

    if (selectedSeason === "all") {
      axios.get("http://localhost:5000/player_seasonal_metric_trend", {
        params: {
          player_id: selectedPlayer.player_id,
          metric: selectedAggregatedMetric,
        }
      })
      .then(res => {
        setAggregatedMetricData(res.data);
        setLoadingAggregatedMetric(false);
      })
      .catch(err => {
        console.error(`Error fetching trend for metric ${selectedAggregatedMetric}:`, err);
        setAggregatedMetricData({ error: `Failed to load trend data for ${selectedAggregatedMetric}` });
        setLoadingAggregatedMetric(false);
      });
    } else {
      axios.get("http://localhost:5000/player_single_season_aggregated_metric", {
        params: {
          player_id: selectedPlayer.player_id,
          season: selectedSeason,
          metric: selectedAggregatedMetric,
        }
      })
      .then(res => {
        setAggregatedMetricData(res.data);
        setLoadingAggregatedMetric(false);
      })
      .catch(err => {
        console.error(`Error fetching single season metric ${selectedAggregatedMetric} for season ${selectedSeason}:`, err);
        setAggregatedMetricData({ error: `Failed to load data for ${selectedAggregatedMetric} in ${selectedSeason.replace('_','-')}` });
        setLoadingAggregatedMetric(false);
      });
    }
  } else {
    setAggregatedMetricData(null);
  }
}, [selectedPlayer, selectedSeason, selectedAggregatedMetric]);


const buttonStyle = (isActive) => ({
padding: "10px 15px",
margin: "0 5px",
border: "none",
borderRadius: "5px",
backgroundColor: isActive ? "#1d4ed8" : "#e5e7eb",
color: isActive ? "white" : "#1f2937",
cursor: "pointer",
fontSize: "14px",
fontWeight: "500",
transition: "background-color 0.2s",
});

const sectionStyle = {
  width: "100%",
  margin: "2rem 0",
  background: "#fff",
  padding: "2rem 0", 
  borderRadius: "12px",
  boxSizing: "border-box"
};

const sectionTitleStyle = (color, borderColor) => ({
fontSize: "1.6rem",
marginBottom: "25px",
color,
borderBottom: `2px solid ${borderColor}`,
paddingBottom: "10px",
display: 'flex',
alignItems: 'center'
});

const labelStyle = {
display: "block",
marginBottom: "8px",
fontWeight: 600,
color: "#1f2937",
fontSize: "1.1rem"
};

const selectStyle = {
width: "100%",
padding: "10px",
borderRadius: "6px",
border: "1px solid #d1d5db",
fontSize: "1rem",
background: "#fff",
color: "#1f2937",
boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
};


const downloadEvents = () => {
if (!events || events.length === 0) return;
const cols = Object.keys(events[0]);
const csvRows = [
cols.join(","),
...events.map((row) =>
cols
.map((col) => {
let val = row[col];
if (typeof val === "object" && val !== null) val = JSON.stringify(val);
if (typeof val === "string" && (val.includes(",") || val.includes('"'))) {
val = `"${val.replace(/"/g, '""')}"`;
}
return val !== undefined && val !== null ? val : "";
})
.join(",")
),
];
const blob = new Blob([csvRows.join("\n")], { type: "text/csv" });
const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url;
a.download = `${selectedPlayer.name}_${selectedSeason}_events.csv`;
document.body.appendChild(a);
a.click();
document.body.removeChild(a);
URL.revokeObjectURL(url);
};


const renderChart = (chartId, type, dataForChart, title) => {
if (!dataForChart || dataForChart.length === 0) return <p>No hi ha dades disponibles per a {title}.</p>;
const chartConfig = {
labels: dataForChart.map(d => d.name),
datasets: [{
label: title,
data: dataForChart.map(d => d.value),
backgroundColor: [
'rgba(75, 192, 192, 0.6)', 'rgba(255, 99, 132, 0.6)',
'rgba(255, 205, 86, 0.6)', 'rgba(54, 162, 235, 0.6)',
'rgba(153, 102, 255, 0.6)', 'rgba(255, 159, 64, 0.6)'
],
borderColor: [
'rgba(75, 192, 192, 1)', 'rgba(255, 99, 132, 1)',
'rgba(255, 205, 86, 1)', 'rgba(54, 162, 235, 1)',
'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)'
],
borderWidth: 1
}]
};
const options = {
responsive: true,
maintainAspectRatio: false,
plugins: {
legend: { display: type === 'pie' || type === 'doughnut' },
title: { display: true, text: title, color: '#1f2937', font: { size: 16, weight: '600' } }
}
};
if (type === 'bar') {
    options.scales = { y: { beginAtZero: true } };
}
return (
<div style={{ height: '350px', marginBottom: '25px', padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#fff' }}>
<CustomVisualizationChart id={chartId} chartType={type} chartDataConfig={chartConfig} chartOptions={options} chartRefs={chartRefs} />
</div>
);
};

const formatStat = (value) => (value !== undefined && value !== null ? Number(value).toFixed(2) : 'N/A');

const renderAggregatedMetricDisplay = () => {
  if (!selectedAggregatedMetric || !aggregatedMetricData) {
    if (selectedAggregatedMetric && !loadingAggregatedMetric && (!aggregatedMetricData || aggregatedMetricData.error)) {
         return <p style={{ textAlign: 'center', color: aggregatedMetricData?.error ? 'red' : '#555' }}>{aggregatedMetricData?.error || `No data for ${selectedAggregatedMetric}.`}</p>;
    }
    return (
        <p style={{ textAlign: 'center', color: '#555', padding: '20px', fontSize: '1.1rem' }}>
          Si us plau, seleccioneu una mètrica de dalt per veure el seu rendiment.        </p>
    );
  }
  if (loadingAggregatedMetric) {
    return <p style={{ textAlign: 'center', color: '#1d4ed8', fontSize: '1.1rem', padding: '20px' }}>S'estan carregant les dades...</p>;
  }
  if (aggregatedMetricData.error) {
    return <p style={{color: 'red', textAlign: 'center', padding: '20px', fontWeight: 'bold'}}>{aggregatedMetricData.error}</p>;
  }

  if (selectedSeason === "all" && aggregatedMetricData.trend_data && aggregatedMetricData.trend_data.length > 0) {
    const chartData = {
      labels: aggregatedMetricData.trend_data.map(d => String(d.season).replace('_', '-')),
      datasets: [
        {
          label: aggregatedMetricData.metric_label || selectedAggregatedMetric,
          data: aggregatedMetricData.trend_data.map(d => d.value),
          borderColor: "#1d4ed8",
          backgroundColor: "rgba(29, 78, 216, 0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointBackgroundColor: "#1d4ed8",
        }
      ],
    };
    const options = {
        responsive: true, maintainAspectRatio: false,
        plugins: {
            legend: { position: "top", labels: {color: '#333', font: {size: 12}} },
            title: { display: true, text: `${aggregatedMetricData.metric_label || selectedAggregatedMetric} Trend for ${selectedPlayer?.name || ''}`, color: '#2c3e50', font: { size: 18, weight: '600' }, padding: {top: 10, bottom: 20} },
            tooltip: { callbacks: { label: function(context) { return (context.dataset.label || '') + ': ' + (context.parsed.y !== null ? context.parsed.y.toFixed(2) : 'N/A'); } } }
        },
        scales: {
            x: { title: { display: true, text: "Season", color: '#333', font: {size: 14}}, ticks: {color: '#555', font: {size: 11}} },
            y: { title: { display: true, text: "Value", color: '#333', font: {size: 14}}, beginAtZero: true, ticks: {color: '#555', font: {size: 11}} }
        },
    };
    return (
      <div style={{ height: '450px', padding: '20px', background: '#fff', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.07)' }}>
        <Line data={chartData} options={options} />
      </div>
    );
  }
  else if (selectedSeason !== "all" && typeof aggregatedMetricData.value !== 'undefined') {
    return (
      <div style={{
        background: '#fff',
        padding: '25px',
        borderRadius: '12px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.07)',
        textAlign: 'center',
        maxWidth: '400px',
        margin: '20px auto'
      }}>
        <h3 style={{ color: '#1f2937', margin: '0 0 10px 0', fontSize: '1.4rem' }}>
          {aggregatedMetricData.metric_label || selectedAggregatedMetric}
        </h3>
        <p style={{ color: '#4b5563', margin: '0 0 15px 0', fontSize: '1rem' }}>
          Per {selectedPlayer?.name} en la temporada {aggregatedMetricData.season.replace('_', '-')}
        </p>
        <div style={{ fontSize: '2.8rem', fontWeight: 'bold', color: '#1d4ed8', margin: '10px 0' }}>
          {Number(aggregatedMetricData.value).toFixed(2)}
        </div>
      </div>
    );
  }
  return <p style={{ textAlign: 'center', color: '#555', padding: '20px', fontSize: '1.05rem' }}>No data available for {aggregatedMetricData?.metric_label || selectedAggregatedMetric}.</p>;
};


return (
<div className="app-root" style={{
  minHeight: "100vh",
  background: "#fff",
  padding: "0",
  margin: "0",
  boxSizing: "border-box",
  fontFamily: "'Inter', sans-serif",
  color: "#1f2937",
  width: "100vw",
  overflowX: "hidden"
}}>
  <section style={{
    width: "100%",
    maxWidth: "1100px",
    margin: "2rem auto",
    background: "#fff",
    padding: "2rem 0",
    borderRadius: "12px",
    boxSizing: "border-box"
  }}>
    <div style={{
      display: "flex",
      gap: "1.5rem"
    }}>
      <div style={{ flex: "1 1 300px" }}>
        <label htmlFor="player-select" style={labelStyle}>
          <FaUser style={{ marginRight: "0.5rem" }} />
          Selecciona jugador:
        </label>
        <select
          id="player-select"
          value={selectedPlayer ? selectedPlayer.name : ""}
          onChange={(e) => {
            const player = players.find((p) => p.name === e.target.value);
            setSelectedPlayer(player);
            setSelectedSeason("");
            setEvents([]);
            setGkAnalysisData(null);
            setAggregatedMetricData(null);
            setSelectedAggregatedMetric('');
          }}
          style={selectStyle}
        >
          <option value="">-- Selecciona jugador --</option>
          {players.map((p) => (
            <option key={p.player_id} value={p.name} style={{ color: "#1f2937" }}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <div style={{ flex: "1 1 300px" }}>
        <label htmlFor="season-select" style={labelStyle}>
          <FaCalendarAlt style={{ marginRight: "0.5rem" }} />
          Selecciona temporada:
        </label>
        <select
          id="season-select"
          value={selectedSeason}
          onChange={(e) => {
            setSelectedSeason(e.target.value);
            setGkAnalysisData(null);
          }}
          style={selectStyle}
          disabled={!selectedPlayer}
        >
          <option value="">
            {selectedPlayer ? "-- Selecciona temporada --" : "-- Selecciona primer un jugador --"}
          </option>
          {selectedPlayer && selectedPlayer.seasons && selectedPlayer.seasons.map((s) => (
            <option key={s} value={s} style={{ color: "#1f2937" }}>
              {s}
            </option>
          ))}
          {selectedPlayer && (
            <option value="all" style={{ color: "#1f2937" }}>
              Totes les temporades
            </option>
          )}
        </select>
      </div>
    </div>
  </section>

  <section style={{
    width: "100%",
    maxWidth: "1100px",
    margin: "2rem auto",
    background: "#fff",
    padding: "2rem 0",
    borderRadius: "12px",
    boxSizing: "border-box"
  }}>
    {loadingEvents && (
      <p style={{ textAlign: 'center', color: '#1d4ed8', fontSize: '1.2rem', padding: '2rem 0' }}>
        S'estan carregant les dades de l'esdeveniment...
      </p>
    )}

    {!loadingEvents && !selectedPlayer && (
      <div>
        <h2 style={{ fontSize: '1.6rem', color: '#1f2937', marginBottom: '20px', textAlign: 'center' }}>
         Us donem la benvinguda a l'anàlisi del jugador
        </h2>
        <p style={{ fontSize: '1.1rem', color: '#4b5563', textAlign: 'center', padding: '1.5rem 0' }}>
          Si us plau, seleccioneu un jugador del desplegable de dalt per començar a analitzar el seu rendiment.
        </p>
      </div>
    )}

    {!loadingEvents && selectedPlayer && selectedSeason && (
      <>
        {selectedPlayer && selectedSeason !== "" && (
            <div className="aggregated-metrics-section" style={{marginBottom: '2rem'}}>
              <h2 style={sectionTitleStyle("#1070CA", "#1070CA")}>
                <FaChartBar style={{ marginRight: '1rem', fontSize: '1.8rem' }} />
                {selectedSeason === "all"
                  ? `Tendències per temporades agregades per ${selectedPlayer?.name}`
                  : `Mètriques agregades per ${selectedPlayer?.name} (${selectedSeason.replace('_', '-')})`
                }
                <InfoTooltip text="Explore aggregated player metrics. For 'All Seasons', see trends. For a specific season, see the calculated value." />
              </h2>
              <div style={{ marginBottom: '25px', maxWidth: '500px', margin: '0 auto 25px auto' }}>
                <label htmlFor="aggregated-metric-select" style={{ ...labelStyle, marginBottom: '10px', fontSize: '1.1rem' }}>
                  Selecciona la mètrica:
                </label>
                <select
                  id="aggregated-metric-select"
                  value={selectedAggregatedMetric}
                  onChange={e => setSelectedAggregatedMetric(e.target.value)}
                  style={{ ...selectStyle, fontSize: '1rem' }}
                  disabled={!availableAggregatedMetrics || availableAggregatedMetrics.length === 0}
                >
                  <option value="">-- Tria una mètrica --</option>
                  {availableAggregatedMetrics
                    .filter(metric => !/sqrt/i.test(metric.id)) 
                    .map((metric) => (
                      <option key={metric.id} value={metric.id}>
                        {(metric.label || metric.id)
                          .replace(/kpi/gi, '')
                          .replace(/inv[\s_]*base/gi, '') 
                          .replace(/\s{2,}/g, ' ')
                          .trim()}
                      </option>
                    ))}
                </select>
              </div>
              {renderAggregatedMetricDisplay()}
            </div>
          )}

        {selectedSeason !== "all" && (
            <div style={{ marginBottom: '2rem' }}>
            <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "1.5rem",
                flexWrap: "wrap",
                gap: "1rem"
            }}>
                <p style={{ margin: 0, fontWeight: 600, color: "#1f2937" }}>
                <strong>Events totals:</strong> {events.length} 
                <span style={{ color: "#4b5563", marginLeft: '1rem' }}>
                    {selectedPlayer?.name} · {selectedSeason.replace('_','-')}
                </span>
                </p>
                {events.length > 0 && (
                    <button
                    onClick={downloadEvents}
                    style={{
                        background: "#1d4ed8",
                        color: "#fff",
                        border: 'none',
                        borderRadius: "6px",
                        padding: "0.75rem 1rem",
                        fontWeight: '600',
                        cursor: 'pointer',
                        fontSize: "1rem"
                    }}
                    >
                    Baixa tots els esdeveniments en format CSV
                    </button>
                )}
            </div>
            {events.length === 0 && (
                <p style={{ textAlign: 'center', color: '#555' }}>No events found for {selectedPlayer.name} in {selectedSeason.replace('_','-')}.</p>
            )}
            </div>
        )}

        {selectedSeason !== "all" && (
          <div className="standard-viz-section">
            <h2 style={sectionTitleStyle("#1f2937", "#1d4ed8")}>
              Visualitzacions estàndard per {selectedPlayer.name} ({selectedSeason.replace('_','-')})
            </h2>
            <div style={{ display: "flex", gap: '0.75rem', marginBottom: '1.5rem', flexWrap: "wrap", justifyContent: 'center' }}>
              <button
                style={buttonStyle(selectedStandardViz === "passmap")}
                onClick={() => setSelectedStandardViz("passmap")}
              >
                Mapa de passades
              </button>
              <button
                style={buttonStyle(selectedStandardViz === "shotmap")}
                onClick={() => setSelectedStandardViz("shotmap")}
              >
                Mapa de xuts
              </button>
              <button
                style={buttonStyle(selectedStandardViz === "heatmaps")}
                onClick={() => setSelectedStandardViz("heatmaps")}
                >
                Mapes de calor
              </button>
              <button
                style={buttonStyle(selectedStandardViz === "shotsavemap")}
                onClick={() => setSelectedStandardViz("shotsavemap")}
                >
                Anàlisi del porter
              </button>
            </div>
            <div className="standard-viz-content-wrapper" style={{ background: '#fff', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', marginTop: '1rem' }}>
              {selectedStandardViz === "passmap" && (
                <>
                  <h4 style={{ fontSize: '1.25rem', color: '#1f2937', fontWeight: 'bold', marginBottom: '1rem' }}>
                    Mapa de passades
                  </h4>
                  <p style={{ color: '#4b5563', marginBottom: '1rem' }}>
                    Aquesta visualització mostra els punts d'inici i final dels passis realitzats pel jugador seleccionat durant la temporada.
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: "2rem" }}>
                    <div style={{ flex: '1 1 600px', minWidth: '300px' }}>
                      <PassMap playerId={selectedPlayer.player_id} season={selectedSeason} setModalImg={setModalImg} />
                    </div>
                  </div>
                </>
              )}
              {selectedStandardViz === "shotmap" && (
                  <>
                  <h4 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem'}}>Mapa de xuts</h4>
                  <p style={{ color: '#4b5563', marginBottom: '1rem' }}>
                   Aquest mapa mostra les ubicacions dels xuts pel jugador, amb marcadors que indiquen el resultat d'aquests.
                   La mida dels marcadors representa el valor dels gols esperats (xG).
                  </p>
                  <ShotMap playerId={selectedPlayer.player_id} season={selectedSeason} setModalImg={setModalImg} />
                  </>
              )}
              {selectedStandardViz === "heatmaps" && (
                  <>
                  <h4 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem' }}>
                    Mapes de calor
                  </h4>
                  <p style={{ color: '#4b5563', marginBottom: '1rem' }}>
                    Aquests mapes de calor il·lustren el posicionament i l'activitat del jugador al camp. El mapa de posició mostra on el jugador era més actiu.
                    Mentre que el mapa de pressió de calor destaca les àrees on el jugador va aplicar pressió defensiva.
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}>
                    <div>
                      <h5 style={{ fontSize: '1.1rem', fontWeight: '600', color: '#1f2937', marginBottom: '0.5rem'}}>Mapa de posicions</h5>
                      <p style={{ color: '#4b5563', fontSize: '0.875rem', marginBottom: '1rem' }}>
                        Mostra el posicionament mitjà del jugador entre partits, amb àrees més fosques que indiquen una activitat més alta.                      </p>
                      <PositionHeatmap playerId={selectedPlayer.player_id} season={selectedSeason} setModalImg={setModalImg} />
                    </div>
                    <div>
                      <h5 style={{ fontSize: '1.1rem', fontWeight: '600', color: '#1f2937', marginBottom: '0.5rem'}}>Mapa de pressions</h5>
                      <p style={{ color: '#4b5563', fontSize: '0.875rem', marginBottom: '1rem' }}>
                        Mostra les zones on el jugador va aplicar pressió defensiva, amb intensitat indicada per degradats de color.
                      </p>
                      <PressureHeatmap playerId={selectedPlayer.player_id} season={selectedSeason} setModalImg={setModalImg} />
                    </div>
                  </div>
                </>
              )}
              {selectedStandardViz === "shotsavemap" && (
                <>
                  <p style={{ color: '#4b5563', marginBottom: '1rem' }}>
                    Aquesta secció proporciona una anàlisi detallada del rendiment del porter, incloent mètriques de tir, estadístiques de pas i altres accions clau
                  </p>
                  {loadingGkAnalysis && <p style={{ color: '#1f2937', textAlign: 'center' }}>S'està carregant l'anàlisi del porter...</p>}
                  {gkAnalysisData && gkAnalysisData.error && <p style={{ color: '#dc2626', textAlign: 'center' }}>{gkAnalysisData.error}</p>}
                  {gkAnalysisData && !gkAnalysisData.error && (
                    <div>
                      {selectedGKSubViz === 'summaryAndCharts' && (
                        <div>
                          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#1f2937', borderBottom: '1px solid #e5e7eb', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>
                            Anàlisi del porter: {selectedPlayer.name} ({selectedSeason.replace('_','-')})
                          </h3>
                          <h4 style={{ fontSize: '1.1rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem' }}>
                            Rendiment d'aturades
                          </h4>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                            <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px' }}>
                              <strong>Tirs a porteria rebuts:</strong> {gkAnalysisData.summary_text_stats?.total_shots_faced_on_target_direct ?? 'N/A'}
                            </div>
                            <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px' }}>
                              <strong>Aturades:</strong> {gkAnalysisData.summary_text_stats?.saves_direct_involvement ?? 'N/A'}
                            </div>
                            <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px' }}>
                              <strong>Gols rebuts:</strong> {gkAnalysisData.summary_text_stats?.goals_conceded_direct_involvement ?? 'N/A'}
                            </div>
                            <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px' }}>
                              <strong>Percentatge d'aturades:</strong> {typeof gkAnalysisData.summary_text_stats?.save_percentage_direct_involvement === 'number' ? formatStat(gkAnalysisData.summary_text_stats?.save_percentage_direct_involvement) + "%" : 'N/A'}
                            </div>
                          </div>
                          <h4 style={{ fontSize: '1.1rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem' }}>
                            Resum de passades
                          </h4>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                            <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px' }}>
                              <strong>Passades totals:</strong> {gkAnalysisData?.summary_text_stats?.total_passes ?? 'N/A'}
                            </div>
                            <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px' }}>
                              <strong>Passades completades:</strong> {gkAnalysisData?.summary_text_stats?.passes_completed ?? 'N/A'}
                            </div>
                            <div style={{ background: '#f9fafb', padding: '1rem', borderRadius: '8px' }}>
                              <strong>Precisió de passada:</strong> {typeof gkAnalysisData?.summary_text_stats?.pass_accuracy_percentage === 'number' ? formatStat(gkAnalysisData?.summary_text_stats?.pass_accuracy_percentage) + "%" : 'N/A'}
                            </div>
                          </div>
                          <div style={{ marginTop: '2rem' }}>
                            {renderChart("gkOverallActionsChart", "bar", gkAnalysisData?.charts_data?.overall_action_type_distribution, "Accions totals per tipus")}
                            {renderChart("gkPassHeightChart", "bar", gkAnalysisData?.charts_data?.pass_height_distribution, "Alçada de les passades")}
                            {renderChart("gkSpecificActionTypeChart", "bar", gkAnalysisData?.charts_data?.gk_event_type_distribution, "Tipus d'esdeveniments del porter")}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}

      </>
    )}
  </section>

  <ImageModal src={modalImg} alt="Visualization" onClose={() => setModalImg(null)} />
  </div>
);
}

export default VisualizationPage;
