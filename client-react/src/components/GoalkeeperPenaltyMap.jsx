import React, { useEffect, useState } from "react";
import axios from "axios";

function GoalkeeperPenaltyMap({ playerId, season }) {
  const [penalties, setPenalties] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId || !season) return;
    setPenalties([]);
    setError(null);
    axios
      .get("http://localhost:5000/goalkeeper_penalty_map", {
        params: { player_id: playerId, season },
      })
      .then((res) => {
        setPenalties(res.data.penalties || []);
      })
      .catch((err) => {
        setError(
          err.response?.data?.error || "Failed to load penalties faced."
        );
      });
  }, [playerId, season]);

  // Simple fallback pitch SVG (goal area only)
  const GoalSVG = ({ children }) => (
    <svg viewBox="0 0 12 8" width="100%" height="160" style={{ background: "#22312b", borderRadius: 8 }}>
      {/* Goal mouth */}
      <rect x="11.5" y="3" width="0.5" height="2" fill="#fff" />
      {/* Penalty spot */}
      <circle cx="9" cy="4" r="0.1" fill="#fff" />
      {/* 6-yard box */}
      <rect x="10" y="2" width="2" height="4" fill="none" stroke="#fff" strokeWidth="0.08" />
      {/* Penalty area */}
      <rect x="8" y="1" width="4" height="6" fill="none" stroke="#fff" strokeWidth="0.12" />
      {children}
    </svg>
  );

  // Color by outcome
  const outcomeColor = (outcome) => {
    if (!outcome) return "#ccc";
    if (outcome === "Goal") return "#dc3545";
    if (outcome.toLowerCase().includes("save")) return "#28a745";
    if (outcome.toLowerCase().includes("post")) return "#ffc107";
    return "#17a2b8";
  };

  return (
    <div style={{ width: "100%", maxWidth: 320 }}>
      <h4 style={{ margin: "0 0 8px 0" }}>Penalties Faced</h4>
      {error && <div style={{ color: "red", marginBottom: 8 }}>{error}</div>}
      <GoalSVG>
        {penalties.map((pen, i) =>
          pen.end_location ? (
            <circle
              key={i}
              cx={pen.end_location[0] / 10}
              cy={pen.end_location[1] / 10}
              r={0.18}
              fill={outcomeColor(pen.outcome)}
              stroke="#fff"
              strokeWidth="0.05"
            >
              <title>
                {pen.outcome || "No outcome"}
                {pen.minute !== undefined ? ` - ${pen.minute}'` : ""}
              </title>
            </circle>
          ) : null
        )}
      </GoalSVG>
      <div style={{ fontSize: 13, marginTop: 8 }}>
        <span style={{ color: "#dc3545" }}>●</span> Goal&nbsp;
        <span style={{ color: "#28a745" }}>●</span> Save&nbsp;
        <span style={{ color: "#ffc107" }}>●</span> Post
      </div>
    </div>
  );
}

export default GoalkeeperPenaltyMap;
