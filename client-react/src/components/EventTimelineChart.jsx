import { Line } from 'react-chartjs-2';

export default function EventTimelineChart({ events }) {
  const timeline = Array(91).fill(0);
  events.forEach(e => {
    const min = parseInt(e.minute);
    if (!isNaN(min)) timeline[min] += 1;
  });

  const data = {
    labels: timeline.map((_, i) => i),
    datasets: [{
      label: "Events over Time",
      data: timeline,
      fill: false,
      borderColor: 'rgba(75,192,192,1)',
    }]
  };

  return <Line data={data} />;
}
