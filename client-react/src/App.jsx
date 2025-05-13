import { useEffect, useState } from "react";
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

ChartJS.register(
  CategoryScale,
  LinearScale,
  ArcElement,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

import EventTypeChart from "./components/EventTypeChart";
import PassMap from "./components/PassMap";
import ShotMap from "./components/ShotMap";
import DuelAnd5050Chart from "./components/DuelAnd5050Chart";
import EventTimelineChart from "./components/EventTimelineChart";
import DribbleCarrySuccessChart from "./components/DribbleCarrySuccessChart";
import GoalkeeperPerformanceChart from "./components/GoalkeeperPerformanceChart";
import PositionHeatmap from "./components/PositionHeatmap";
import PressureHeatmap from "./components/PressureHeatmap";
// import ExpectedThreat from "./components/ExpectedThreat";
import RadarChart from "./components/RadarChart";

function App() {
  const [seasons, setSeasons] = useState([]);
  const [players, setPlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [selectedSeason, setSelectedSeason] = useState("");
  const [events, setEvents] = useState([]);
  const [selectedViz, setSelectedViz] = useState("passmap");

  useEffect(() => {
    axios.get("http://localhost:5000/seasons").then(res => setSeasons(res.data));
    axios.get("http://localhost:5000/all_players").then(res => setPlayers(res.data));
  }, []);

  useEffect(() => {
    if (selectedPlayer && selectedSeason) {
      axios.get(`http://localhost:5000/player_events`, {
        params: {
          player_id: selectedPlayer.player_id,
          season: selectedSeason
        }
      }).then(res => setEvents(res.data));
    }
  }, [selectedPlayer, selectedSeason]);

  const buttonStyle = (isActive) => ({
    padding: "10px 20px",
    margin: "0 5px",
    border: "none",
    borderRadius: "5px",
    backgroundColor: isActive ? "#007bff" : "#e0e0e0",
    color: isActive ? "white" : "black",
    cursor: "pointer",
    fontSize: "16px",
    fontWeight: "bold",
    transition: "background-color 0.3s, transform 0.1s",
    boxShadow: isActive ? "0 2px 5px rgba(0,0,0,0.2)" : "none",
  });

  const buttonHoverStyle = {
    ":hover": {
      backgroundColor: "#0056b3",
      transform: "scale(1.05)",
    }
  };

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <h1>⚽ La Liga Player Explorer</h1>

      <div style={{ marginBottom: "1rem" }}>
        <label style={{ marginRight: "10px", fontWeight: "bold" }}>Player:</label>
        <select
          onChange={e => {
            const selected = players.find(p => p.name === e.target.value);
            setSelectedPlayer(selected);
            setSelectedSeason("");
            setEvents([]);
          }}
          style={{
            padding: "5px",
            borderRadius: "5px",
            border: "1px solid #ccc",
            fontSize: "16px",
          }}
        >
          <option value="">--Select--</option>
          {players.map(p => (
            <option key={p.player_id} value={p.name}>{p.name}</option>
          ))}
        </select>
      </div>

      {selectedPlayer && (
        <div style={{ marginBottom: "1rem" }}>
          <label style={{ marginRight: "10px", fontWeight: "bold" }}>Season:</label>
          <select
            onChange={e => setSelectedSeason(e.target.value)}
            style={{
              padding: "5px",
              borderRadius: "5px",
              border: "1px solid #ccc",
              fontSize: "16px",
            }}
          >
            <option value="">--Select--</option>
            {selectedPlayer.seasons.map(s => <option key={s} value={s}>{s}</option>)}
            <option value="all">All Seasons</option>
          </select>
        </div>
      )}

      {events.length > 0 && (
        <>
          <div style={{ marginBottom: "1rem" }}>
            <h2>Event Summary</h2>
            <p>Total Events: {events.length}</p>
            <ul>
              {Object.entries(events.reduce((acc, e) => {
                const type = e?.type?.name;
                if (type) acc[type] = (acc[type] || 0) + 1;
                return acc;
              }, {})).map(([type, count]) => (
                <li key={type}>{type}: {count}</li>
              ))}
            </ul>
          </div>

          <div>
            <h2>Visual Analytics</h2>
            <div style={{ marginBottom: "20px" }}>
              <button
                style={{ ...buttonStyle(selectedViz === "passmap") }}
                onMouseOver={e => e.currentTarget.style.backgroundColor = "#0056b3"}
                onMouseOut={e => e.currentTarget.style.backgroundColor = selectedViz === "passmap" ? "#007bff" : "#e0e0e0"}
                onClick={() => setSelectedViz("passmap")}
              >
                Pass Map
              </button>
              <button
                style={{ ...buttonStyle(selectedViz === "shotmap") }}
                onMouseOver={e => e.currentTarget.style.backgroundColor = "#0056b3"}
                onMouseOut={e => e.currentTarget.style.backgroundColor = selectedViz === "shotmap" ? "#007bff" : "#e0e0e0"}
                onClick={() => setSelectedViz("shotmap")}
              >
                Shot Map
              </button>
              <button
                style={{ ...buttonStyle(selectedViz === "heatmap") }}
                onMouseOver={e => e.currentTarget.style.backgroundColor = "#0056b3"}
                onMouseOut={e => e.currentTarget.style.backgroundColor = selectedViz === "heatmap" ? "#007bff" : "#e0e0e0"}
                onClick={() => setSelectedViz("heatmap")}
              >
                Heatmap
              </button>
              <button
                style={{ ...buttonStyle(selectedViz === "pressureHeatmap") }}
                onMouseOver={e => e.currentTarget.style.backgroundColor = "#0056b3"}
                onMouseOut={e => e.currentTarget.style.backgroundColor = selectedViz === "pressureHeatmap" ? "#007bff" : "#e0e0e0"}
                onClick={() => setSelectedViz("pressureHeatmap")}
              >
                Pressure Heatmap
              </button>
              {/* <button
                style={{ ...buttonStyle(selectedViz === "xtHeatmap") }}
                onMouseOver={e => e.currentTarget.style.backgroundColor = "#0056b3"}
                onMouseOut={e => e.currentTarget.style.backgroundColor = selectedViz === "xtHeatmap" ? "#007bff" : "#e0e0e0"}
                onClick={() => setSelectedViz("xtHeatmap")}
              >
                Expected Threat (xT)
              </button> */}
            </div>

            {selectedViz === "passmap" && (
              <PassMap playerId={selectedPlayer?.player_id} season={selectedSeason} />
            )}
            {selectedViz === "shotmap" && (
              <ShotMap playerId={selectedPlayer?.player_id} season={selectedSeason} />
            )}
            {selectedViz === "heatmap" && (
              <PositionHeatmap playerId={selectedPlayer?.player_id} season={selectedSeason} />
            )}
            {selectedViz === "pressureHeatmap" && (
              <PressureHeatmap playerId={selectedPlayer?.player_id} season={selectedSeason} />
            )}
            {/* {selectedViz === "xtHeatmap" && (
              <ExpectedThreat playerId={selectedPlayer?.player_id} season={selectedSeason} />
            )} */}
          </div>
        </>
      )}
    </div>
  );
}

export default App;