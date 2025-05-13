import { useEffect, useState } from "react";
import axios from "axios";
import { Stage, Layer, Rect, Line, Text } from "react-konva";

export default function PassMap({ playerId, season }) {
  const [passes, setPasses] = useState([]);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    completed: true,
    incomplete: true,
    assists: true,
    finalThird: false
  });
  const [stats, setStats] = useState({
    completionRate: 0,
    finalThirdCompletionRate: 0,
    totalAssists: 0,
  });
  const [heatmapUrl, setHeatmapUrl] = useState(null);
  const [heatmapError, setHeatmapError] = useState(null);

  const pitchWidth = 120;
  const pitchHeight = 80;
  const canvasWidth = 600;
  const canvasHeight = 400;
  const scaleX = canvasWidth / pitchWidth;
  const scaleY = canvasHeight / pitchHeight;

  useEffect(() => {
    if (!playerId || !season) return;
    setPasses([]);
    setError(null);
    setHeatmapUrl(null);
    setHeatmapError(null);

    // Fetch Pass Map data
    axios
      .get("http://localhost:5000/pass_map_plot", {
        params: { player_id: playerId, season }
      })
      .then(res => {
        if (res.data.passes) {
          const passData = res.data.passes;
          setPasses(passData);

          // Calculate overall statistics
          const totalPasses = passData.length;
          const completedPasses = passData.filter(p => p.completed).length;
          const finalThirdPasses = passData.filter(p => p.final_third).length;
          const completedFinalThirdPasses = passData.filter(p => p.completed && p.final_third).length;
          const assists = passData.filter(p => p.assist).length;

          setStats({
            completionRate: totalPasses > 0 ? (completedPasses / totalPasses * 100).toFixed(2) : 0,
            finalThirdCompletionRate: finalThirdPasses > 0 ? (completedFinalThirdPasses / finalThirdPasses * 100).toFixed(2) : 0,
            totalAssists: assists,
          });
        } else {
          setError("No pass data returned");
        }
      })
      .catch(err => {
        setError("Error fetching pass map");
        console.error(err);
      });

    // Fetch Pass Completion Heatmap
    axios
      .get("http://localhost:5000/pass_completion_heatmap", {
        params: { player_id: playerId, season }
      })
      .then(res => {
        if (res.data.image_url) {
          const fullUrl = `http://localhost:5000${res.data.image_url}?t=${Date.now()}`;
          setHeatmapUrl(fullUrl);
        } else {
          setHeatmapError("No heatmap image URL returned");
        }
      })
      .catch(err => {
        setHeatmapError("Error fetching pass completion heatmap");
        console.error(err);
      });
  }, [playerId, season]);

  const handleFilterChange = (filterKey) => {
    setFilters(prev => ({
      ...prev,
      [filterKey]: !prev[filterKey]
    }));
  };

  const drawPitch = () => {
    const goalCenterY = pitchHeight / 2;
    const penaltyAreaWidth = 16.5;
    const penaltyAreaHeight = 33;
    const goalAreaWidth = 5.5;
    const goalAreaHeight = 11;
    const goalHeight = 7.32;

    return (
      <>
        <Rect
          x={0}
          y={0}
          width={canvasWidth}
          height={canvasHeight}
          fill="white"
        />
        <Line
          points={[0, 0, canvasWidth, 0, canvasWidth, canvasHeight, 0, canvasHeight, 0, 0]}
          stroke="black"
          strokeWidth={2}
          closed
        />
        <Line
          points={[
            (pitchWidth - penaltyAreaWidth) * scaleX, (goalCenterY - penaltyAreaHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY - penaltyAreaHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY + penaltyAreaHeight / 2) * scaleY,
            (pitchWidth - penaltyAreaWidth) * scaleX, (goalCenterY + penaltyAreaHeight / 2) * scaleY,
            (pitchWidth - penaltyAreaWidth) * scaleX, (goalCenterY - penaltyAreaHeight / 2) * scaleY
          ]}
          stroke="black"
          strokeWidth={2}
          closed
        />
        <Line
          points={[
            (pitchWidth - goalAreaWidth) * scaleX, (goalCenterY - goalAreaHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY - goalAreaHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY + goalAreaHeight / 2) * scaleY,
            (pitchWidth - goalAreaWidth) * scaleX, (goalCenterY + goalAreaHeight / 2) * scaleY,
            (pitchWidth - goalAreaWidth) * scaleX, (goalCenterY - goalAreaHeight / 2) * scaleY
          ]}
          stroke="black"
          strokeWidth={2}
          closed
        />
        <Line
          points={[
            pitchWidth * scaleX, (goalCenterY - goalHeight / 2) * scaleY,
            pitchWidth * scaleX, (goalCenterY + goalHeight / 2) * scaleY
          ]}
          stroke="black"
          strokeWidth={4}
        />
        <Rect x={10} y={10} width={15} height={15} fill="green" />
        <Text x={30} y={10} text="Completed Pass" fontSize={12} />
        <Rect x={10} y={30} width={15} height={15} fill="red" />
        <Text x={30} y={30} text="Incomplete Pass" fontSize={12} />
        <Rect x={10} y={50} width={15} height={15} fill="blue" />
        <Text x={30} y={50} text="Assist" fontSize={12} />
        <Rect x={10} y={70} width={15} height={15} fill="purple" />
        <Text x={30} y={70} text="Final Third Pass (if applicable)" fontSize={12} />
      </>
    );
  };

  const filteredPasses = passes.filter(pass => {
    const matchesCompleted = filters.completed && pass.completed;
    const matchesIncomplete = filters.incomplete && !pass.completed;
    const matchesAssist = filters.assists && pass.assist;
    const matchesFinalThird = !filters.finalThird || (filters.finalThird && pass.final_third);

    return (matchesCompleted || matchesIncomplete || matchesAssist) && matchesFinalThird;
  });

  return (
    <div>
      <h3>PASSING</h3>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <div style={{ marginBottom: "10px" }}>
        <label>
          <input
            type="checkbox"
            checked={filters.completed}
            onChange={() => handleFilterChange("completed")}
          />
          Completed Passes
        </label>
        <label style={{ marginLeft: "10px" }}>
          <input
            type="checkbox"
            checked={filters.incomplete}
            onChange={() => handleFilterChange("incomplete")}
          />
          Incomplete Passes
        </label>
        <label style={{ marginLeft: "10px" }}>
          <input
            type="checkbox"
            checked={filters.assists}
            onChange={() => handleFilterChange("assists")}
          />
          Assists
        </label>
        <label style={{ marginLeft: "10px" }}>
          <input
            type="checkbox"
            checked={filters.finalThird}
            onChange={() => handleFilterChange("finalThird")}
          />
          Passes to Final Third
        </label>
      </div>
      <Stage width={canvasWidth} height={canvasHeight}>
        <Layer>
          {drawPitch()}
          {filteredPasses.map((pass, index) => {
            const startX = pass.start_x * scaleX;
            const startY = pass.start_y * scaleY;
            const endX = pass.end_x * scaleX;
            const endY = pass.end_y * scaleY;
            let color = pass.assist ? "blue" : pass.completed ? "green" : "red";
            if (filters.finalThird && pass.final_third) {
              color = pass.assist ? "blue" : "purple";
            }
            return (
              <Line
                key={index}
                points={[startX, startY, endX, endY]}
                stroke={color}
                strokeWidth={2}
                lineCap="round"
                lineJoin="round"
                opacity={0.5}
              />
            );
          })}
        </Layer>
      </Stage>
      <div style={{ marginTop: "10px" }}>
        <p>Pass Completion Rate: {stats.completionRate}%</p>
        <p>Final Third Pass Completion Rate: {stats.finalThirdCompletionRate}%</p>
        <p>Total Assists: {stats.totalAssists}</p>
      </div>
      <div style={{ marginTop: "20px" }}>
        <h4>Pass Completion Percentage by Zone</h4>
        {heatmapError && <p style={{ color: "red" }}>{heatmapError}</p>}
        {heatmapUrl ? (
          <img
            key={heatmapUrl}
            src={heatmapUrl}
            alt="Pass Completion Heatmap"
            style={{ maxWidth: "100%", border: "1px solid #ccc" }}
          />
        ) : (
          !heatmapError && <p>Loading pass completion heatmap...</p>
        )}
      </div>
    </div>
  );
}