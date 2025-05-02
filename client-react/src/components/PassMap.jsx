import { useEffect, useRef } from 'react';

// Dimensió del camp segons StatsBomb (en unitats)
const PITCH_LENGTH = 120;
const PITCH_WIDTH = 80;

const PassMap = ({ events }) => {
  const canvasRef = useRef(null);

  // Funció per parsejar coordenades de string a array
  const parseCoordinates = (coordString) => {
    if (!coordString || typeof coordString !== 'string') return null;
    try {
      // Eliminar claudàtors i convertir a array de números
      const cleaned = coordString.replace(/\[|\]/g, '').split(',').map(Number);
      if (cleaned.length === 2 && !isNaN(cleaned[0]) && !isNaN(cleaned[1])) {
        return cleaned;
      }
      return null;
    } catch (e) {
      console.error('Error parsejant coordenades:', coordString, e);
      return null;
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    // Ajustar la mida del canvas
    const scale = Math.min(canvas.width / PITCH_LENGTH, canvas.height / PITCH_WIDTH);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Dibuixar el camp
    drawPitch(ctx, canvas.width, canvas.height);

    // Filtrar esdeveniments de tipus "Pass"
    const passes = events.filter(event => event.type === 'Pass');
    console.log(`Nombre total de passades trobades: ${passes.length}`);

    // Dibuixar les passades
    passes.forEach((pass, index) => {
      const startCoords = parseCoordinates(pass.location);
      const endCoords = parseCoordinates(pass.pass_end_location);

      if (startCoords && endCoords) {
        const [startX, startY] = startCoords;
        const [endX, endY] = endCoords;

        // Escalar coordenades al canvas
        const canvasStartX = startX * scale;
        const canvasStartY = (PITCH_WIDTH - startY) * scale; // Invertir Y
        const canvasEndX = endX * scale;
        const canvasEndY = (PITCH_WIDTH - endY) * scale;

        // Determinar si la passada és completada
        const isCompleted = !pass.pass_outcome;

        // Dibuixar la línia de la passada
        ctx.beginPath();
        ctx.moveTo(canvasStartX, canvasStartY);
        ctx.lineTo(canvasEndX, canvasEndY);
        ctx.strokeStyle = isCompleted ? 'green' : 'red';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Dibuixar un cercle al punt inicial
        ctx.beginPath();
        ctx.arc(canvasStartX, canvasStartY, 3, 0, 2 * Math.PI);
        ctx.fillStyle = isCompleted ? 'green' : 'red';
        ctx.fill();
      } else {
        console.warn(`Passada ${index} saltada per coordenades invàlides:`, {
          location: pass.location,
          pass_end_location: pass.pass_end_location,
        });
      }
    });
  }, [events]);

  // Funció per dibuixar el camp de futbol
  const drawPitch = (ctx, width, height) => {
    const scale = Math.min(width / PITCH_LENGTH, height / PITCH_WIDTH);
    const pitchWidth = PITCH_WIDTH * scale;
    const pitchLength = PITCH_LENGTH * scale;
    const offsetX = (width - pitchLength) / 2;
    const offsetY = (height - pitchWidth) / 2;

    // Fons verd
    ctx.fillStyle = '#4CAF50';
    ctx.fillRect(offsetX, offsetY, pitchLength, pitchWidth);

    // Línies blanques
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 2;

    // Línia de banda i línia de fons
    ctx.strokeRect(offsetX, offsetY, pitchLength, pitchWidth);

    // Línia central
    ctx.beginPath();
    ctx.moveTo(offsetX + pitchLength / 2, offsetY);
    ctx.lineTo(offsetX + pitchLength / 2, offsetY + pitchWidth);
    ctx.stroke();

    // Cercle central
    ctx.beginPath();
    ctx.arc(offsetX + pitchLength / 2, offsetY + pitchWidth / 2, 9.15 * scale, 0, 2 * Math.PI);
    ctx.stroke();

    // Àrea de penal (esquerra)
    const penaltyAreaWidth = 40.3 * scale;
    const penaltyAreaLength = 16.5 * scale;
    ctx.strokeRect(offsetX, offsetY + (pitchWidth - penaltyAreaWidth) / 2, penaltyAreaLength, penaltyAreaWidth);

    // Àrea de penal (dreta)
    ctx.strokeRect(offsetX + pitchLength - penaltyAreaLength, offsetY + (pitchWidth - penaltyAreaWidth) / 2, penaltyAreaLength, penaltyAreaWidth);

    // Àrea de meta (esquerra)
    const goalAreaWidth = 18.3 * scale;
    const goalAreaLength = 5.5 * scale;
    ctx.strokeRect(offsetX, offsetY + (pitchWidth - goalAreaWidth) / 2, goalAreaLength, goalAreaWidth);

    // Àrea de meta (dreta)
    ctx.strokeRect(offsetX + pitchLength - goalAreaLength, offsetY + (pitchWidth - goalAreaWidth) / 2, goalAreaLength, goalAreaWidth);

    // Punt de penal (esquerra)
    ctx.beginPath();
    ctx.arc(offsetX + 11 * scale, offsetY + pitchWidth / 2, 0.3 * scale, 0, 2 * Math.PI);
    ctx.fillStyle = 'white';
    ctx.fill();

    // Punt de penal (dreta)
    ctx.beginPath();
    ctx.arc(offsetX + pitchLength - 11 * scale, offsetY + pitchWidth / 2, 0.3 * scale, 0, 2 * Math.PI);
    ctx.fill();
  };

  return (
    <div>
      <h3>Pass Map</h3>
      <canvas ref={canvasRef} width={600} height={400} style={{ border: '1px solid black' }} />
    </div>
  );
};

export default PassMap;