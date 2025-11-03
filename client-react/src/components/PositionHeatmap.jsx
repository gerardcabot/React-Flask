import React from 'react';
import { useTranslation } from 'react-i18next';

const R2_PUBLIC_URL = import.meta.env.VITE_R2_PUBLIC_URL;

export default function PositionHeatmap({ playerId, season }) {
  const { t } = useTranslation();
  
  if (!playerId || !season || !R2_PUBLIC_URL) {
    return <p>{t('visualization.positionHeatmap.selectPlayerSeason')}</p>;
  }

  const imageUrl = `${R2_PUBLIC_URL}/${playerId}_${season}_position_heatmap.png`;

  return (
    <div>
      <img
        key={imageUrl}
        src={imageUrl}
        alt={t('visualization.positionHeatmap.altText', { player: playerId, season: season })}
        style={{ maxWidth: "100%", border: "1px solid #ccc", minHeight: '100px', display: 'block' }}
        onError={(e) => {
          e.target.style.display = 'none';
          if (e.target.nextSibling) e.target.nextSibling.style.display = 'block';
        }}
      />
      <p style={{ display: 'none', color: 'red' }}>{t('visualization.positionHeatmap.errorLoading')}</p>
    </div>
  );
}