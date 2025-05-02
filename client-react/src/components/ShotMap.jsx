import { useState, useEffect } from 'react';

const ShotMap = ({ playerId, season }) => {
  const [shotMapImage, setShotMapImage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId || !season) return;

    fetch(`http://localhost:5000/shot_map?player_id=${playerId}&season=${season}`)
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          setError(data.error);
          setShotMapImage(null);
        } else {
          setShotMapImage(data.image);
          setError(null);
        }
      })
      .catch(err => {
        setError('Error loading shot map');
        setShotMapImage(null);
        console.error(err);
      });
  }, [playerId, season]);

  return (
    <div>
      <h3>Shot Map</h3>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {shotMapImage ? (
        <img src={shotMapImage} alt="Shot Map" style={{ maxWidth: '100%' }} />
      ) : (
        !error && <p>Loading shot map...</p>
      )}
    </div>
  );
};

export default ShotMap;