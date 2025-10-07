import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import ca from './translations/ca.json';
import es from './translations/es.json';
import en from './translations/en.json';

i18n
  // Detect user language
  .use(LanguageDetector)
  // Pass the i18n instance to react-i18next
  .use(initReactI18next)
  // Init i18next
  .init({
    resources: {
      ca: { translation: ca },
      es: { translation: es },
      en: { translation: en }
    },
    fallbackLng: 'ca', // Default language
    lng: localStorage.getItem('language') || 'ca', // Load from localStorage or default
    debug: false,
    interpolation: {
      escapeValue: false // React already escapes by default
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage']
    }
  });

// Save language preference whenever it changes
i18n.on('languageChanged', (lng) => {
  localStorage.setItem('language', lng);
});

export default i18n;
