import React from 'react';
import { useTranslation } from 'react-i18next';

const LanguageSelector = ({ isScouting }) => {
  const { i18n } = useTranslation();
  
  const languages = [
    { code: 'ca', name: 'CAT'},
    { code: 'es', name: 'ESP'},
    { code: 'en', name: 'ENG'}
  ];

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng);
  };

  const primaryColor = isScouting ? '#dc2626' : '#1d4ed8';
  const lightColor = isScouting ? 'rgba(220,38,38,0.1)' : 'rgba(29,78,216,0.1)';

  return (
    <div style={{
      display: 'flex',
      gap: '0.5rem',
      alignItems: 'center',
      background: lightColor,
      padding: '0.4rem 0.6rem',
      borderRadius: '8px',
      border: `1px solid ${primaryColor}20`
    }}>
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => changeLanguage(lang.code)}
          style={{
            padding: '0.3rem 0.7rem',
            border: 'none',
            borderRadius: '6px',
            background: i18n.language === lang.code ? primaryColor : 'transparent',
            color: i18n.language === lang.code ? '#fff' : primaryColor,
            fontWeight: i18n.language === lang.code ? '700' : '500',
            fontSize: '0.85rem',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem'
          }}
          onMouseEnter={(e) => {
            if (i18n.language !== lang.code) {
              e.target.style.background = `${primaryColor}10`;
            }
          }}
          onMouseLeave={(e) => {
            if (i18n.language !== lang.code) {
              e.target.style.background = 'transparent';
            }
          }}
        >
          <span style={{ fontSize: '1rem' }}>{lang.flag}</span>
          {lang.name}
        </button>
      ))}
    </div>
  );
};

export default LanguageSelector;
