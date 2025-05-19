import { useEffect, useState, useRef } from "react";
import axios from "axios";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  ArcElement,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import "./App.css";
import { FaUser, FaCalendarAlt, FaPlus } from "react-icons/fa";

ChartJS.register(
  CategoryScale, LinearScale, ArcElement, BarElement, PointElement, LineElement, Title, Tooltip, Legend
);

// Standard Components
import PassMap from "./components/PassMap";
import ShotMap from "./components/ShotMap";
import PositionHeatmap from "./components/PositionHeatmap";
import PressureHeatmap from "./components/PressureHeatmap";
import XGGoalTrend from "./components/XGGoalTrend";
import SeasonalStatsDashboard from "./components/SeasonalStatsDashboard";
import GoalkeeperStatsDashboard from "./components/GoalkeeperStatsDashboard";
import GoalkeeperStats from "./components/GoalkeeperStats";

// --- New: Goalkeeper Advanced Visualizations ---
import GoalkeeperShotSaveMap from "./components/GoalkeeperShotSaveMap";
import GoalkeeperDistributionMap from "./components/GoalkeeperDistributionMap";
import GoalkeeperHandlingMap from "./components/GoalkeeperHandlingMap";
import GoalkeeperSweeperMap from "./components/GoalkeeperSweeperMap";
import GoalkeeperPenaltyMap from "./components/GoalkeeperPenaltyMap";

function CustomVisualizationChart({ id, chartType, chartDataConfig, chartOptions, chartRefs }) {
  // Handles Chart.js rendering and cleanup
  useEffect(() => {
    const canvas = document.getElementById(`chart-${id}`);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    if (chartRefs.current[id]) {
      chartRefs.current[id].destroy();
    }
    chartRefs.current[id] = new ChartJS(ctx, { type: chartType, data: chartDataConfig, options: chartOptions });

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

function App() {
  const [seasons, setSeasons] = useState([]);
  const [players, setPlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [selectedSeason, setSelectedSeason] = useState("");
  const [events, setEvents] = useState([]);
  const [selectedStandardViz, setSelectedStandardViz] = useState("passmap");
  const [availableCustomVisualizations, setAvailableCustomVisualizations] = useState([]);
  const [activeCustomVisualizations, setActiveCustomVisualizations] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [loadingCustomViz, setLoadingCustomViz] = useState(false);
  const [showEventDetails, setShowEventDetails] = useState(false);
  const [passMapZonaStats, setPassMapZonaStats] = useState(null);
  const [goalkeeperStats, setGoalkeeperStats] = useState(null);
  const [goalkeeperStatsAllSeasons, setGoalkeeperStatsAllSeasons] = useState(null);
  const [selectedGKSubViz, setSelectedGKSubViz] = useState("shotSaveMap");
  const [modalImg, setModalImg] = useState(null);
  const chartRefs = useRef({});

  // Initial data fetch
  useEffect(() => {
    axios.get("http://localhost:5000/seasons").then(res => setSeasons(res.data)).catch(err => console.error("Error fetching seasons:", err));
    axios.get("http://localhost:5000/players").then(res => setPlayers(res.data)).catch(err => console.error("Error fetching players:", err));
    axios.get("http://localhost:5000/available_visualizations")
      .then(res => {
        // The backend now returns { visualizations: [...] }
        setAvailableCustomVisualizations(res.data.visualizations || []);
      })
      .catch(err => console.error("Error fetching available visualizations:", err));
  }, []);

  // Fetch events when player or season changes
  useEffect(() => {
    if (selectedPlayer && selectedSeason) {
      setLoadingEvents(true);
      axios.get(`http://localhost:5000/player_events`, {
        params: { player_id: selectedPlayer.player_id, season: selectedSeason }
      }).then(res => {
        setEvents(res.data);
        setLoadingEvents(false);
      }).catch(err => {
        console.error("Error fetching events:", err);
        setEvents([]);
        setLoadingEvents(false);
      });
    } else {
      setEvents([]);
    }
  }, [selectedPlayer, selectedSeason]);

  // Fetch pass map zona stats when passmap is selected
  useEffect(() => {
    if (
      selectedPlayer &&
      selectedSeason &&
      selectedStandardViz === "passmap"
    ) {
      axios
        .get("http://localhost:5000/pass_map_zona_stats", {
          params: {
            player_id: selectedPlayer.player_id,
            season: selectedSeason,
          },
        })
        .then((res) => setPassMapZonaStats(res.data))
        .catch(() => setPassMapZonaStats(null));
    } else {
      setPassMapZonaStats(null);
    }
  }, [selectedPlayer, selectedSeason, selectedStandardViz]);

  // Fetch goalkeeper stats for single season
  useEffect(() => {
    if (selectedPlayer && selectedSeason && selectedSeason !== "all") {
      axios
        .get("http://localhost:5000/goalkeeper_stats", {
          params: { player_id: selectedPlayer.player_id, season: selectedSeason },
        })
        .then((res) => setGoalkeeperStats(res.data.stats))
        .catch(() => setGoalkeeperStats(null));
    } else {
      setGoalkeeperStats(null);
    }
  }, [selectedPlayer, selectedSeason]);

  // Fetch goalkeeper stats for all seasons
  useEffect(() => {
    if (selectedPlayer && selectedSeason === "all") {
      axios
        .get("http://localhost:5000/goalkeeper_stats_all_seasons", {
          params: { player_id: selectedPlayer.player_id },
        })
        .then((res) => setGoalkeeperStatsAllSeasons(res.data.stats))
        .catch(() => setGoalkeeperStatsAllSeasons(null));
    } else {
      setGoalkeeperStatsAllSeasons(null);
    }
  }, [selectedPlayer, selectedSeason]);

  const buttonStyle = (isActive) => ({
    padding: "10px 15px", margin: "0 5px", border: "none", borderRadius: "5px",
    backgroundColor: isActive ? "#007bff" : "#e9ecef",
    color: isActive ? "white" : "#212529", cursor: "pointer", fontSize: "14px",
    fontWeight: "500", transition: "background-color 0.2s",
  });

  const addCustomVisualization = (vizOption) => {
    if (!selectedPlayer || !selectedSeason || !vizOption) {
      alert("Please select a player, season, and visualization option.");
      return;
    }
    // Prevent adding the exact same viz multiple times quickly
    if (activeCustomVisualizations.find(v => v.label === vizOption.label && v.metric === vizOption.metric)) {
        // Visualization already active; optionally prevent duplicates
        // return; // Uncomment to prevent adding duplicates
    }

    setLoadingCustomViz(true);

    // --- FIX: Flatten visualization config if grouped by category ---
    // Some availableCustomVisualizations are grouped by category, so flatten if needed
    // But in your code, you already use .map(vizOpt => ...) so vizOption is a single object

    // --- FIX: Only send params that are defined ---
    // Some visualizations do not have all params (e.g. filter, location_column, etc.)
    // Only send those that exist in vizOption

    // Build params object robustly
    const params = {
      player_id: selectedPlayer.player_id,
      season: selectedSeason,
      metric: vizOption.metric,
      metric_type: vizOption.metric_type,
      viz_type: vizOption.viz_type,
    };
    if (vizOption.location_column) params.location_column = vizOption.location_column;
    // If vizOption has a filter, add its keys as query params
    if (vizOption.filter) {
      Object.entries(vizOption.filter).forEach(([key, value]) => {
        if (key === "progressive") {
          params.progressive = value;
        } else {
          params[`filter_type`] = key;
          params[`filter_value`] = value;
        }
      });
    }

    axios.get("http://localhost:5000/custom_visualization", { params })
      .then(res => {
        const newVizData = { ...vizOption, vizDataBackend: res.data, id: `${vizOption.label}-${Date.now()}` };
        setActiveCustomVisualizations(prev => [...prev, newVizData]);
        setLoadingCustomViz(false);
      }).catch(err => {
        console.error("Error fetching custom visualization:", err);
        const errorMsg = err.response?.data?.error || "Unknown error loading visualization.";
        setActiveCustomVisualizations(prev => [...prev, { ...vizOption, vizDataBackend: { error: errorMsg }, id: `${vizOption.label}-error-${Date.now()}` }]);
        setLoadingCustomViz(false);
      });
  };

  const removeCustomVisualization = (idToRemove) => {
    setActiveCustomVisualizations(prev => prev.filter(viz => viz.id !== idToRemove));
    if (chartRefs.current[idToRemove]) {
      chartRefs.current[idToRemove].destroy();
      delete chartRefs.current[idToRemove];
    }
  };

  // Use the interface and classNames from App.css for the custom viz grid/cards
  function CustomVisualizationCard({ vizConfig, onRemove }) {
    const { id, label, vizDataBackend } = vizConfig;

    if (!vizDataBackend || vizDataBackend.error) {
      return (
        <div className="viz-card error">
          <h3>{label}</h3>
          <button className="viz-card-close" onClick={() => onRemove(id)}>×</button>
          <p className="error-message">{vizDataBackend?.error || "Error loading data"}</p>
        </div>
      );
    }

    if (vizDataBackend.type === "number") {
      return (
        <div className="viz-card number">
          <h3>{vizDataBackend.title}</h3>
          <button className="viz-card-close" onClick={() => onRemove(id)}>×</button>
          <div className="number-display">
            {typeof vizDataBackend.data === "number"
              ? vizDataBackend.data.toFixed(2) + (vizDataBackend.suffix || "")
              : vizDataBackend.data}
          </div>
        </div>
      );
    }

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: 'top' },
        title: { display: false }
      }
    };

    let chartType, chartData;

    switch (vizDataBackend.type) {
      case "scatter":
      case "heatmap":
        chartType = "scatter";
        chartData = {
          datasets: [{
            label: vizDataBackend.title,
            data: vizDataBackend.data,
            backgroundColor: "rgba(0, 123, 255, 0.5)",
            pointRadius: 5
          }]
        };
        chartOptions.scales = {
          x: { min: 0, max: 120, title: { display: true, text: 'Pitch X (0-120)' } },
          y: { min: 0, max: 80, title: { display: true, text: 'Pitch Y (0-80)' } }
        };
        break;
      case "line":
        chartType = "line";
        chartData = {
          labels: vizDataBackend.data.map(d => d.x || d.minute || d.category),
          datasets: [{
            label: vizDataBackend.title,
            data: vizDataBackend.data.map(d => d.y || d.value || d.count),
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1,
            fill: false
          }]
        };
        chartOptions.scales = {
          y: { beginAtZero: true },
          x: { title: { display: true, text: vizDataBackend.xLabel || '' } }
        };
        break;
      case "bar":
      case "bar_or_pie":
        chartType = vizDataBackend.viz_type === 'pie' ? 'pie' : 'bar';
        const colors = [
          'rgba(75, 192, 192, 0.6)',
          'rgba(255, 99, 132, 0.6)',
          'rgba(255, 205, 86, 0.6)',
          'rgba(54, 162, 235, 0.6)',
          'rgba(153, 102, 255, 0.6)'
        ];
        chartData = {
          labels: vizDataBackend.data.map(d => d.x),
          datasets: [{
            label: vizDataBackend.title,
            data: vizDataBackend.data.map(d => d.y),
            backgroundColor: chartType === 'pie' ? colors : colors[0],
            borderColor: chartType === 'pie' ? colors.map(c => c.replace('0.6', '1')) : colors[0].replace('0.6', '1'),
            borderWidth: 1
          }]
        };
        if (chartType === 'bar') {
          chartOptions.scales = {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: vizDataBackend.title.includes('%') ? 'Percentage (%)' : 'Count'
              }
            }
          };
        }
        break;
      default:
        return (
          <div className="viz-card error">
            <h3>{vizDataBackend.title || label}</h3>
            <button className="viz-card-close" onClick={() => onRemove(id)}>×</button>
            <p>Unsupported visualization type: {vizDataBackend.type}</p>
          </div>
        );
    }

    return (
      <div className="viz-card">
        <h3>{vizDataBackend.title || label}</h3>
        <button className="viz-card-close" onClick={() => onRemove(id)}>×</button>
        <div className="chart-container">
          <CustomVisualizationChart
            id={id}
            chartType={chartType}
            chartDataConfig={chartData}
            chartOptions={chartOptions}
            chartRefs={chartRefs}
          />
        </div>
      </div>
    );
  }

  const eventColumns = [
    "id", "index", "period", "timestamp", "minute", "second", "type", "possession",
    "possession_team", "play_pattern", "team", "player", "position", "location",
    "duration", "under_pressure", "off_camera", "out", "related_events", "counterpress",
    "50_50_outcome", "bad_behaviour_card", "ball_receipt_outcome",
    "ball_recovery_offensive", "ball_recovery_recovery_failure",
    "block_deflection", "block_offensive", "block_save_block", "carry_end_location",
    "clearance_aerial_won", "clearance_body_part", "dribble_outcome", "dribble_nutmeg",
    "dribble_overrun", "dribble_no_touch", "duel_type", "duel_outcome",
    "foul_committed_advantage", "foul_committed_offensive", "foul_committed_penalty",
    "foul_committed_card", "foul_committed_type", "foul_won_advantage",
    "foul_won_defensive", "foul_won_penalty", "goalkeeper_position",
    "goalkeeper_technique", "goalkeeper_body_part", "goalkeeper_type",
    "goalkeeper_outcome", "goalkeeper_end_location", "half_end_early_video_end",
    "half_end_match_suspended", "half_start_late_video_start", "injury_stoppage_in_chain",
    "interception_outcome", "miscontrol_aerial_won", "pass_recipient", "pass_length",
    "pass_angle", "pass_height", "pass_end_location", "pass_assisted_shot_id",
    "pass_backheel", "pass_deflected", "pass_miscommunication", "pass_cross",
    "pass_cut_back", "pass_switch", "pass_shot_assist", "pass_goal_assist",
    "pass_body_part", "pass_type", "pass_outcome", "pass_technique", "player_off_permanent",
    "shot_key_pass_id", "shot_end_location", "shot_aerial_won", "shot_follows_dribble",
    "shot_first_time", "shot_freeze_frame", "shot_open_goal", "shot_statsbomb_xg",
    "shot_deflected", "shot_technique", "shot_body_part", "shot_type", "shot_outcome",
    "shot_one_on_one", "substitution_replacement", "substitution_outcome", "tactics",
  ].filter((v, i, a) => a.indexOf(v) === i).sort();


  // Download events as CSV
  const downloadEvents = () => {
    if (!events.length) return;
    const cols = Object.keys(events[0]);
    const csvRows = [
      cols.join(","),
      ...events.map((row) =>
        cols
          .map((col) => {
            let val = row[col];
            if (typeof val === "object" && val !== null) val = JSON.stringify(val);
            if (typeof val === "string" && (val.includes(",") || val.includes('"')))
              val = `"${val.replace(/"/g, '""')}"`;
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

  // Responsive grid columns for custom viz
  const getVizGridColumns = () => {
    if (window.innerWidth < 700) return 1;
    if (window.innerWidth < 1100) return 2;
    return 3;
  };

  return (
    <div className="app-root improved-ui">
      <header className="app-header">
        <h1>⚽ La Liga Player Explorer</h1>
      </header>

      <section className="app-controls">
        <div className="control-group">
          <label>
            <FaUser style={{ marginRight: 4 }} />
            Player:
          </label>
          <select
            value={selectedPlayer ? selectedPlayer.name : ""}
            onChange={(e) => {
              const player = players.find((p) => p.name === e.target.value);
              setSelectedPlayer(player);
              setSelectedSeason("");
              setEvents([]);
              setActiveCustomVisualizations([]);
            }}
            style={{
              background: "#f8f9fa",
              color: "#212529",
              border: "1px solid #ced4da",
            }}
          >
            <option value="">--Select Player--</option>
            {players.map((p) => (
              <option key={p.player_id} value={p.name} style={{ color: "#212529", background: "#fff" }}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        {selectedPlayer && (
          <div className="control-group">
            <label>
              <FaCalendarAlt style={{ marginRight: 4 }} />
              Season:
            </label>
            <select
              value={selectedSeason}
              onChange={(e) => {
                setSelectedSeason(e.target.value);
                setActiveCustomVisualizations([]);
              }}
              style={{
                background: "#f8f9fa",
                color: "#212529",
                border: "1px solid #ced4da",
              }}
            >
              <option value="">--Select Season--</option>
              {selectedPlayer.seasons.map((s) => (
                <option key={s} value={s} style={{ color: "#212529", background: "#fff" }}>
                  {s}
                </option>
              ))}
              <option value="all" style={{ color: "#212529", background: "#fff" }}>
                All Seasons
              </option>
            </select>
          </div>
        )}
      </section>

      {selectedPlayer && selectedSeason && availableCustomVisualizations.length > 0 && (
        <section className="custom-viz-section">
          <h2>Add Custom Visualization</h2>
          <div className="custom-viz-controls">
            <select
              id="customVizSelect"
              defaultValue=""
              style={{
                background: "#f8f9fa",
                color: "#212529",
                border: "1px solid #ced4da",
              }}
            >
              <option value="" disabled>
                --Choose a Visualization--
              </option>
              {availableCustomVisualizations.map((vizOpt, index) => (
                <option
                  key={index}
                  value={index}
                  style={{ color: "#212529", background: "#fff" }}
                >
                  {vizOpt.category ? `[${vizOpt.category}] ` : ""}
                  {vizOpt.label}
                </option>
              ))}
            </select>
            <button
              className="add-viz-btn"
              onClick={() => {
                const selectEl = document.getElementById("customVizSelect");
                if (selectEl && selectEl.value !== "")
                  addCustomVisualization(
                    availableCustomVisualizations[parseInt(selectEl.value)]
                  );
                if (selectEl) selectEl.value = "";
              }}
              disabled={loadingCustomViz}
              style={{
                background: "#007bff",
                color: "#fff",
                border: "none",
                borderRadius: "5px",
                padding: "8px 14px",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              <FaPlus style={{ marginRight: 4 }} />
              {loadingCustomViz ? "Loading..." : "Add Visualization"}
            </button>
          </div>
          <div
            className="viz-grid"
            style={{
              gridTemplateColumns: `repeat(${getVizGridColumns()}, 1fr)`,
              gap: "1.5rem",
              marginTop: "1rem",
            }}
          >
            {activeCustomVisualizations.map((vizConfig) => (
              <CustomVisualizationCard
                key={vizConfig.id}
                vizConfig={vizConfig}
                onRemove={removeCustomVisualization}
              />
            ))}
          </div>
        </section>
      )}

      {loadingEvents && <p className="loading-message">Loading event data...</p>}

      {events.length > 0 && (
        <section className="event-section">
          <div className="event-summary-row">
            <p>
              <strong>Total Events:</strong> {events.length} &nbsp;
              <span className="player-season-label">
                {selectedPlayer?.name} &middot; {selectedSeason}
              </span>
            </p>
            <button
              className="toggle-details-btn"
              onClick={downloadEvents}
              style={{
                background: "#007bff",
                color: "#fff",
                border: "none",
                borderRadius: "5px",
                padding: "8px 14px",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Download Events CSV
            </button>
          </div>

          {selectedPlayer && selectedSeason && selectedSeason !== "all" && (
            <div className="standard-viz-section">
              <h3>Standard Visual Analytics for Season: {selectedSeason}</h3>
              <div className="standard-viz-btns">
                <button
                  className={selectedStandardViz === "passmap" ? "active" : ""}
                  onClick={() => setSelectedStandardViz("passmap")}
                >
                  Pass Map
                </button>
                <button
                  className={selectedStandardViz === "shotmap" ? "active" : ""}
                  onClick={() => setSelectedStandardViz("shotmap")}
                >
                  Shot Map
                </button>
                <button
                  className={selectedStandardViz === "heatmap" ? "active" : ""}
                  onClick={() => setSelectedStandardViz("heatmap")}
                >
                  Position Heatmap
                </button>
                <button
                  className={selectedStandardViz === "pressureHeatmap" ? "active" : ""}
                  onClick={() => setSelectedStandardViz("pressureHeatmap")}
                >
                  Pressure Heatmap
                </button>
                <button
                  className={selectedStandardViz === "shotsavemap" ? "active" : ""}
                  onClick={() => setSelectedStandardViz("shotsavemap")}
                >
                  Goalkeeper Analysis
                </button>
              </div>
              <div className="standard-viz-content" style={{ display: "flex", alignItems: "flex-start" }}>
                {selectedStandardViz === "passmap" && (
                  <>
                    <div style={{ flex: 1 }}>
                      <PassMap playerId={selectedPlayer.player_id} season={selectedSeason} setModalImg={setModalImg} />
                    </div>
                    {passMapZonaStats && (
                      <div
                        style={{
                          minWidth: 220,
                          marginLeft: 24,
                          background: "#f8f9fa",
                          border: "1px solid #dee2e6",
                          borderRadius: 8,
                          padding: 16,
                          color: "#212529",
                        }}
                      >
                        <h4 style={{ marginTop: 0, marginBottom: 12 }}>Pass Completion % by Zona</h4>
                        <table style={{ width: "100%", fontSize: 14 }}>
                          <thead>
                            <tr>
                              <th style={{ textAlign: "left" }}>Zona</th>
                              <th style={{ textAlign: "right" }}>Completion %</th>
                            </tr>
                          </thead>
                          <tbody>
                            {passMapZonaStats.zonas &&
                              passMapZonaStats.zonas.map((zona) => (
                                <tr key={zona.name}>
                                  <td>{zona.name}</td>
                                  <td style={{ textAlign: "right" }}>
                                    {zona.completion_pct !== null
                                      ? zona.completion_pct.toFixed(1) + "%"
                                      : "-"}
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </>
                )}
                {selectedStandardViz === "shotmap" && (
                  <ShotMap playerId={selectedPlayer.player_id} season={selectedSeason} setModalImg={setModalImg} />
                )}
                {selectedStandardViz === "heatmap" && (
                  <PositionHeatmap playerId={selectedPlayer.player_id} season={selectedSeason} setModalImg={setModalImg} />
                )}
                {selectedStandardViz === "pressureHeatmap" && (
                  <PressureHeatmap playerId={selectedPlayer.player_id} season={selectedSeason} setModalImg={setModalImg} />
                )}
                {selectedStandardViz === "shotsavemap" && (
                  <div style={{ flex: 1 }}>
                    {/* --- New: GK Sub-visualization Tabs --- */}
                    <div style={{ marginBottom: 16 }}>
                      <button
                        style={buttonStyle(selectedGKSubViz === "shotSaveMap")}
                        onClick={() => setSelectedGKSubViz("shotSaveMap")}
                      >
                        Shot/Save Map
                      </button>
                      <button
                        style={buttonStyle(selectedGKSubViz === "distribution")}
                        onClick={() => setSelectedGKSubViz("distribution")}
                      >
                        Distribution
                      </button>
                      <button
                        style={buttonStyle(selectedGKSubViz === "handling")}
                        onClick={() => setSelectedGKSubViz("handling")}
                      >
                        Handling
                      </button>
                      <button
                        style={buttonStyle(selectedGKSubViz === "sweeper")}
                        onClick={() => setSelectedGKSubViz("sweeper")}
                      >
                        Sweeper Actions
                      </button>
                      <button
                        style={buttonStyle(selectedGKSubViz === "penalties")}
                        onClick={() => setSelectedGKSubViz("penalties")}
                      >
                        Penalties Faced
                      </button>
                    </div>
                    {/* --- Render the selected GK sub-viz --- */}
                    {selectedGKSubViz === "shotSaveMap" && (
                      <GoalkeeperShotSaveMap
                        playerId={selectedPlayer.player_id}
                        season={selectedSeason}
                      />
                    )}
                    {selectedGKSubViz === "distribution" && (
                      <GoalkeeperDistributionMap
                        playerId={selectedPlayer.player_id}
                        season={selectedSeason}
                      />
                    )}
                    {selectedGKSubViz === "handling" && (
                      <GoalkeeperHandlingMap
                        playerId={selectedPlayer.player_id}
                        season={selectedSeason}
                      />
                    )}
                    {selectedGKSubViz === "sweeper" && (
                      <GoalkeeperSweeperMap
                        playerId={selectedPlayer.player_id}
                        season={selectedSeason}
                      />
                    )}
                    {selectedGKSubViz === "penalties" && (
                      <GoalkeeperPenaltyMap
                        playerId={selectedPlayer.player_id}
                        season={selectedSeason}
                      />
                    )}
                    {/* --- End GK sub-viz --- */}
                    {goalkeeperStats && (
                      <div
                        style={{
                          minWidth: 220,
                          marginLeft: 24,
                          background: "#f8f9fa",
                          border: "1px solid #dee2e6",
                          borderRadius: 8,
                          padding: 16,
                          color: "#212529",
                        }}
                      >
                        <h4 style={{ marginTop: 0, marginBottom: 12 }}>Goalkeeper Stats</h4>
                        <table style={{ width: "100%", fontSize: 14 }}>
                          <tbody>
                            <tr>
                              <td>Total GK Events</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.total_events}</td>
                            </tr>
                            <tr>
                              <td>Shots Faced</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.shot_faced}</td>
                            </tr>
                            <tr>
                              <td>Shots Saved</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.shot_saved}</td>
                            </tr>
                            <tr>
                              <td>Goals Conceded</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.goal_conceded}</td>
                            </tr>
                            <tr>
                              <td>Save %</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.save_pct}%</td>
                            </tr>
                            <tr>
                              <td>Punches</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.punches}</td>
                            </tr>
                            <tr>
                              <td>Claims</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.claims}</td>
                            </tr>
                            <tr>
                              <td>Collected</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.collected}</td>
                            </tr>
                            <tr>
                              <td>In Play Danger</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.in_play_danger}</td>
                            </tr>
                            <tr>
                              <td>Passes Attempted</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.passes_attempted}</td>
                            </tr>
                            <tr>
                              <td>Passes Completed</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.passes_completed}</td>
                            </tr>
                            <tr>
                              <td>Throws Attempted</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.throws_attempted}</td>
                            </tr>
                            <tr>
                              <td>Throws Completed</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.throws_completed}</td>
                            </tr>
                            <tr>
                              <td>Sweeper Actions</td>
                              <td style={{ textAlign: "right" }}>{goalkeeperStats.sweeper_actions}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {selectedPlayer && selectedSeason === "all" && (
            <div className="all-seasons-section">
              <h3>Aggregated "All Seasons" Dashboards</h3>
              <div className="all-seasons-grid large-dashboards">
                <div className="dashboard-card">
                  <SeasonalStatsDashboard playerId={selectedPlayer.player_id} />
                </div>
                <div className="dashboard-card">
                  <XGGoalTrend playerId={selectedPlayer.player_id} />
                </div>
                <div className="dashboard-card">
                  <GoalkeeperStatsDashboard playerId={selectedPlayer.player_id} />
                  {goalkeeperStatsAllSeasons && (
                    <div
                      style={{
                        marginTop: 16,
                        background: "#f8f9fa",
                        border: "1px solid #dee2e6",
                        borderRadius: 8,
                        padding: 16,
                        color: "#212529",
                      }}
                    >
                      <h4 style={{ marginTop: 0, marginBottom: 12 }}>Goalkeeper Stats (All Seasons)</h4>
                      <table style={{ width: "100%", fontSize: 14 }}>
                        <tbody>
                          <tr>
                            <td>Total GK Events</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.total_events}</td>
                          </tr>
                          <tr>
                            <td>Shots Faced</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.shot_faced}</td>
                          </tr>
                          <tr>
                            <td>Shots Saved</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.shot_saved}</td>
                          </tr>
                          <tr>
                            <td>Goals Conceded</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.goal_conceded}</td>
                          </tr>
                          <tr>
                            <td>Save %</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.save_pct}%</td>
                          </tr>
                          <tr>
                            <td>Punches</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.punches}</td>
                          </tr>
                          <tr>
                            <td>Claims</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.claims}</td>
                          </tr>
                          <tr>
                            <td>Collected</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.collected}</td>
                          </tr>
                          <tr>
                            <td>In Play Danger</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.in_play_danger}</td>
                          </tr>
                          <tr>
                            <td>Passes Attempted</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.passes_attempted}</td>
                          </tr>
                          <tr>
                            <td>Passes Completed</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.passes_completed}</td>
                          </tr>
                          <tr>
                            <td>Throws Attempted</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.throws_attempted}</td>
                          </tr>
                          <tr>
                            <td>Throws Completed</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.throws_completed}</td>
                          </tr>
                          <tr>
                            <td>Sweeper Actions</td>
                            <td style={{ textAlign: "right" }}>{goalkeeperStatsAllSeasons.sweeper_actions}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {!loadingEvents && !selectedPlayer && (
        <p className="info-message">Please select a player to begin.</p>
      )}
      {!loadingEvents && selectedPlayer && !selectedSeason && (
        <p className="info-message">
          Please select a season for {selectedPlayer.name}.
        </p>
      )}
      {!loadingEvents &&
        selectedPlayer &&
        selectedSeason &&
        events.length === 0 && (
          <p className="info-message">
            No event data found for {selectedPlayer.name} in {selectedSeason}.
          </p>
        )}

      <ImageModal src={modalImg} alt="Visualization" onClose={() => setModalImg(null)} />
    </div>
  );
}

export default App;