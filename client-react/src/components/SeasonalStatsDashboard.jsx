import { useEffect, useState } from "react";
import axios from "axios";
import { Bar } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function SeasonalStatsDashboard({ playerId }) {
  const [statsData, setStatsData] = useState([]);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState("bar"); // 'bar' or 'table'

  useEffect(() => {
    if (!playerId) return;

    setError(null);
    axios.get("http://localhost:5000/seasonal_stats", {
      params: { player_id: playerId }
    })
    .then(res => {
      setStatsData(res.data.stats_data || []);
    })
    .catch(err => {
      setError("Error fetching seasonal stats");
      console.error(err);
    });
  }, [playerId]);

  if (error) {
    return <p style={{ color: "red" }}>{error}</p>;
  }

  if (!statsData.length) {
    return <p>No seasonal stats available.</p>;
  }

  // Use all seasons' data
  const displayData = statsData;

  // Prepare data for bar chart
  const chartData = {
    labels: displayData.map(d => d.season),
    datasets: [
      {
        label: "Total xG",
        data: displayData.map(d => d.total_xg),
        backgroundColor: "rgba(75, 192, 192, 0.6)",
      },
      {
        label: "Pass Completion %",
        data: displayData.map(d => d.pass_completion_pct),
        backgroundColor: "rgba(255, 99, 132, 0.6)",
      },
      {
        label: "Progressive Passes",
        data: displayData.map(d => d.progressive_passes),
        backgroundColor: "rgba(54, 162, 235, 0.6)",
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { position: "top" },
      title: {
        display: true,
        text: "Seasonal Stats Across All Seasons",
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: "Value" },
      },
    },
  };

  // Table view
  const tableRows = displayData.map((data, index) => (
    <tr key={index}>
      <td>{data.season}</td>
      <td>{data.total_xg}</td>
      <td>{data.pass_completion_pct}%</td>
      <td>{data.progressive_passes}</td>
    </tr>
  ));

  return (
    <div style={{ marginTop: "20px" }}>
      <div style={{ marginBottom: "10px" }}>
        <button
          onClick={() => setViewMode("bar")}
          style={{ marginRight: "10px", padding: "5px 10px", backgroundColor: viewMode === "bar" ? "#007bff" : "#e0e0e0", color: viewMode === "bar" ? "white" : "black" }}
        >
          Bar Chart
        </button>
        <button
          onClick={() => setViewMode("table")}
          style={{ padding: "5px 10px", backgroundColor: viewMode === "table" ? "#007bff" : "#e0e0e0", color: viewMode === "table" ? "white" : "black" }}
        >
          Table
        </button>
      </div>
      {viewMode === "bar" ? (
        <Bar data={chartData} options={chartOptions} />
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "10px" }}>
          <thead>
            <tr>
              <th style={{ border: "1px solid #ddd", padding: "8px", backgroundColor: "#f2f2f2" }}>Season</th>
              <th style={{ border: "1px solid #ddd", padding: "8px", backgroundColor: "#f2f2f2" }}>Total xG</th>
              <th style={{ border: "1px solid #ddd", padding: "8px", backgroundColor: "#f2f2f2" }}>Pass Completion %</th>
              <th style={{ border: "1px solid #ddd", padding: "8px", backgroundColor: "#f2f2f2" }}>Progressive Passes</th>
            </tr>
          </thead>
          <tbody>{tableRows}</tbody>
        </table>
      )}
    </div>
  );
}