import React, { useEffect, useState } from "react";
import axios from "axios";

function GoalkeeperSweeperMap({ playerId, season }) {
  const [actions, setActions] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId || !season) return;
    setActions([]);
    setError(null);
    axios
      .get("http://localhost:5000/goalkeeper_sweeper_map", {
        params: { player_id: playerId, season },
      })
      .then((res) => {
        setActions(res.data.actions || []);
      })
      .catch((err) => {
        setError(
          err.response?.data?.error || "Failed to load sweeper actions."
        );
      });
  }, [playerId, season]);

  // Simple fallback pitch SVG
  const PitchSVG = ({ children }) => (
    <svg viewBox="0 0 120 80" width="100%" height="320" style={{ background: "#22312b", borderRadius: 8 }}>
      {/* Pitch outline */}
      <rect x="0" y="0" width="120" height="80" fill="#22312b" stroke="#fff" strokeWidth="1.5" />
      {/* Penalty area */}
      <rect x="0" y="18" width="18" height="44" fill="none" stroke="#fff" strokeWidth="1" />
      {/* 6-yard box */}
      <rect x="0" y="30" width="6" height="20" fill="none" stroke="#fff" strokeWidth="0.8" />
      {/* Goal */}
      <rect x="-2" y="36" width="2" height="8" fill="#fff" />
      {/* Center line */}
      <line x1="60" y1="0" x2="60" y2="80" stroke="#fff" strokeWidth="1" />
      {/* Center circle */}
      <circle cx="60" cy="40" r="10" fill="none" stroke="#fff" strokeWidth="1" />
      {children}
    </svg>
  );

  return (
    <div style={{ width: "100%", maxWidth: 420 }}>
      <h4 style={{ margin: "0 0 8px 0" }}>Sweeper Actions</h4>
      {error && <div style={{ color: "red", marginBottom: 8 }}>{error}</div>}
      <PitchSVG>
        {actions.map((action, i) => (
          <circle
            key={i}
            cx={action.location[0]}
            cy={action.location[1]}
            r={3}
            fill="#17a2b8"
            stroke="#fff"
            strokeWidth="0.7"
          >
            <title>
              {action.outcome || "No outcome"}
              {action.minute !== undefined ? ` - ${action.minute}'` : ""}
            </title>
          </circle>
        ))}
      </PitchSVG>
      <div style={{ fontSize: 13, marginTop: 8 }}>
        <span style={{ color: "#17a2b8" }}>●</span> Sweeper Actions
      </div>
    </div>
  );
}

export default GoalkeeperSweeperMap;
