import { Bar } from 'react-chartjs-2';

export default function EventTypeChart({ events }) {
  const counts = {};
  events.forEach(e => {
    const name = e?.type?.name;
    if (name) counts[name] = (counts[name] || 0) + 1;
  });

  const data = {
    labels: Object.keys(counts),
    datasets: [{
      label: 'Event Count',
      data: Object.values(counts),
      backgroundColor: 'rgba(54, 162, 235, 0.6)'
    }]
  };

  return <Bar data={data} />;
}
