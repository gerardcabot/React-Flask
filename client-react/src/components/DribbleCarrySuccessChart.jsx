import { Bar } from 'react-chartjs-2';

export default function DribbleCarrySuccessChart({ events }) {
  const dribbles = events.filter(e => e.type?.name === "Dribble");
  const carries = events.filter(e => e.type?.name === "Carry");

  const complete = dribbles.filter(d => d.dribble_outcome?.name === "Complete").length;
  const incomplete = dribbles.length - complete;

  const data = {
    labels: ["Dribble Success", "Dribble Fail", "Carries"],
    datasets: [{
      label: "Count",
      data: [complete, incomplete, carries.length],
      backgroundColor: ["green", "red", "blue"]
    }]
  };

  return <Bar data={data} />;
}
