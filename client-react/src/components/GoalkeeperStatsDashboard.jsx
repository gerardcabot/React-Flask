import { useEffect, useState } from "react";
import axios from "axios";

export default function GoalkeeperStatsDashboard({ playerId, season }) {
  const [stats, setStats] = useState(null);
  const [allStats, setAllStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId || !season) return;
    setError(null);
    setStats(null);
    axios
      .get("http://localhost:5000/goalkeeper_stats", {
        params: { player_id: playerId, season },
      })
      .then((res) => setStats(res.data.stats))
      .catch((err) => {
        setError("No goalkeeper stats for this season.");
        setStats(null);
      });
  }, [playerId, season]);

  useEffect(() => {
    if (!playerId) return;
    setAllStats(null);
    axios
      .get("http://localhost:5000/goalkeeper_stats_all_seasons", {
        params: { player_id: playerId },
      })
      .then((res) => setAllStats(res.data.stats))
      .catch(() => setAllStats(null));
  }, [playerId]);

  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!stats && !allStats) return <p>Loading goalkeeper stats...</p>;

  return (
    <div style={{ marginTop: "20px" }}>
      <h3>Goalkeeper Stats</h3>
      {stats && (
        <div>
          <h4>This Season</h4>
          <ul style={{ fontSize: 16, lineHeight: 1.7 }}>
            <li>Total GK Events: {stats.total_events}</li>
            <li>Shots Faced: {stats.shot_faced}</li>
            <li>Shots Saved: {stats.shot_saved}</li>
            <li>Goals Conceded: {stats.goal_conceded}</li>
            <li>Punches: {stats.punches}</li>
            <li>Claims: {stats.claims}</li>
            <li>Collected: {stats.collected}</li>
            <li>In Play Danger: {stats.in_play_danger}</li>
          </ul>
        </div>
      )}
      {allStats && (
        <div>
          <h4>All Seasons</h4>
          <ul style={{ fontSize: 16, lineHeight: 1.7 }}>
            <li>Total GK Events: {allStats.total_events}</li>
            <li>Shots Faced: {allStats.shot_faced}</li>
            <li>Shots Saved: {allStats.shot_saved}</li>
            <li>Goals Conceded: {allStats.goal_conceded}</li>
            <li>Punches: {allStats.punches}</li>
            <li>Claims: {allStats.claims}</li>
            <li>Collected: {allStats.collected}</li>
            <li>In Play Danger: {allStats.in_play_danger}</li>
          </ul>
        </div>
      )}
      {!stats && !allStats && <p>No goalkeeper stats available.</p>}
    </div>
  );
}