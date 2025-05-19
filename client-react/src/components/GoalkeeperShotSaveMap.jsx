import React, { useEffect, useState } from "react";
import axios from "axios";

/**
 * Displays a map of all shots faced by the goalkeeper for a given player and season.
 * Shows shot origins, outcomes, and xG.
 */
function GoalkeeperShotSaveMap({ playerId, season }) {
  const [shots, setShots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!playerId || !season) return;
    setLoading(true);
    setError("");
    axios
      .get("http://localhost:5000/goalkeeper_shot_map", {
        params: { player_id: playerId, season },
      })
      .then((res) => {
        setShots(res.data.shots || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(
          err.response?.data?.error ||
            "Failed to load goalkeeper shot/save map."
        );
        setLoading(false);
      });
  }, [playerId, season]);

  // Pitch dimensions for StatsBomb: 120x80
  const width = 360;
  const height = 240;

  // Color by outcome
  const outcomeColor = (outcome) => {
    if (outcome === "Goal") return "#dc3545";
    if (outcome && outcome.toLowerCase().includes("save")) return "#007bff";
    if (outcome && outcome.toLowerCase().includes("post")) return "#ffc107";
    if (outcome && outcome.toLowerCase().includes("off t")) return "#6c757d";
    return "#adb5bd";
  };

  return (
    <div style={{ width: "100%", maxWidth: 420 }}>
      <h4 style={{ marginBottom: 8 }}>Shots Faced Map</h4>
      {loading && <div>Loading...</div>}
      {error && <div style={{ color: "#dc3545" }}>{error}</div>}
      {!loading && !error && (
        <svg
          viewBox="0 0 120 80"
          width={width}
          height={height}
          style={{
            background: "#22312b",
            borderRadius: 8,
            width: "100%",
            height: "auto",
            boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
          }}
        >
          {/* Pitch outline */}
          <rect
            x={0}
            y={0}
            width={120}
            height={80}
            fill="#22312b"
            stroke="#fff"
            strokeWidth={1}
            rx={2}
          />
          {/* Goal area */}
          <rect
            x={120 - 6}
            y={30}
            width={6}
            height={20}
            fill="none"
            stroke="#fff"
            strokeWidth={0.7}
          />
          {/* Penalty area */}
          <rect
            x={120 - 18}
            y={18}
            width={18}
            height={44}
            fill="none"
            stroke="#fff"
            strokeWidth={0.7}
          />
          {/* Shots */}
          {shots.map((shot, i) => (
            <g key={i}>
              {/* Origin point */}
              <circle
                cx={shot.origin?.[0]}
                cy={shot.origin?.[1]}
                r={1.7}
                fill={outcomeColor(shot.outcome)}
                stroke="#fff"
                strokeWidth={0.3}
                opacity={0.85}
              />
              {/* xG label */}
              {shot.xg !== undefined && (
                <text
                  x={shot.origin?.[0] + 2.5}
                  y={shot.origin?.[1] - 1.5}
                  fontSize={2.7}
                  fill="#fff"
                  opacity={0.8}
                >
                  {shot.xg.toFixed(2)}
                </text>
              )}
              {/* Outcome marker */}
              {shot.outcome === "Goal" && (
                <text
                  x={shot.origin?.[0]}
                  y={shot.origin?.[1] + 4}
                  fontSize={3.5}
                  fill="#dc3545"
                  fontWeight="bold"
                  textAnchor="middle"
                >
                  ●
                </text>
              )}
            </g>
          ))}
        </svg>
      )}
      {!loading && !error && shots.length === 0 && (
        <div style={{ color: "#888", marginTop: 8 }}>No shots faced found.</div>
      )}
      <div style={{ fontSize: 13, color: "#666", marginTop: 8 }}>
        <span style={{ color: "#dc3545" }}>●</span> Goal &nbsp;
        <span style={{ color: "#007bff" }}>●</span> Save &nbsp;
        <span style={{ color: "#ffc107" }}>●</span> Post &nbsp;
        <span style={{ color: "#6c757d" }}>●</span> Off Target
      </div>
    </div>
  );
}

export default GoalkeeperShotSaveMap;
