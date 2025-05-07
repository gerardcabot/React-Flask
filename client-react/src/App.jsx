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
import RadarChart from "./components/RadarChart";


function App() {
  const [seasons, setSeasons] = useState([]);
  const [players, setPlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [selectedSeason, setSelectedSeason] = useState("");
  const [events, setEvents] = useState([]);

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

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <h1>⚽ La Liga Player Explorer</h1>

      <div style={{ marginBottom: "1rem" }}>
        <label>Player:</label>
        <select onChange={e => {
          const selected = players.find(p => p.name === e.target.value);
          setSelectedPlayer(selected);
          setSelectedSeason("");  // reset season on player change
          setEvents([]);
        }}>
          <option value="">--Select--</option>
          {players.map(p => (
            <option key={p.player_id} value={p.name}>{p.name}</option>
          ))}
        </select>
      </div>

      {selectedPlayer && (
        <div style={{ marginBottom: "1rem" }}>
          <label>Season:</label>
          <select onChange={e => setSelectedSeason(e.target.value)}>
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
            {/* <EventTypeChart events={events} /> */}
            {/* <PassMap events={events} /> */}
            <PassMap playerId={selectedPlayer?.player_id} season={selectedSeason} />
            {/* <DuelAnd5050Chart events={events} /> */}
            {/* <EventTimelineChart events={events} /> */}
            {/* <DribbleCarrySuccessChart events={events} /> */}
            {/* <GoalkeeperPerformanceChart events={events} /> */}
            {<PositionHeatmap playerId={selectedPlayer?.player_id} season={selectedSeason} />}
            { <RadarChart playerId={selectedPlayer?.player_id} season={selectedSeason} /> }
          </div>
        </>
      )}
    </div>
  );
}

export default App;
