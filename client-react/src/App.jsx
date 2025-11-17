import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from "react-router-dom";
import "./App.css"; 
import VisualizationPage from "./VisualizationPage"; 
import ScoutingPage from "./ScoutingPage"; 
import React, { useEffect } from "react";
import { Toaster } from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import LanguageSelector from './components/LanguageSelector';

function HeaderBrand() {
  const location = useLocation();
  const isScouting = location.pathname === "/scouting";
  const { t } = useTranslation();
  
  
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      gap: '1.5rem',
      flexWrap: 'wrap'
    }}>
      <span
        style={{
          background: isScouting ? "rgba(220,38,38,0.07)" : "rgba(29,78,216,0.07)",
          borderRadius: "12px",
          padding: "0.25em 1.2em",
          boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
          display: "inline-block",
          fontSize: "1.1em",
          letterSpacing: "0.09em",
          fontWeight: 900,
          border: `2px solid ${isScouting ? "#dc2626" : "#1d4ed8"}`,
          textTransform: "uppercase",
          lineHeight: 1.1,
          marginBottom: "0.1em",
          color: isScouting ? "#dc2626" : "#1d4ed8"
        }}
      >
        {t('app.title')}
      </span>
      <LanguageSelector isScouting={isScouting} />
    </div>
  );
}

function StatsBombInfo() {
  const location = useLocation();
  const isScouting = location.pathname === "/scouting";
  const { t } = useTranslation();
  
  // Color scheme based on page
  const colors = isScouting ? {
    background: '#fef2f2',
    border: '#fca5a5',
    text: '#991b1b',
    icon: '#dc2626'
  } : {
    background: '#e0f2fe',
    border: '#0ea5e9',
    text: '#0c4a6e',
    icon: '#1d4ed8'
  };
  
  return (
    <div style={{
      background: colors.background,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '12px 16px',
      margin: '1rem auto',
      maxWidth: '1100px',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      fontSize: '0.95rem',
      color: colors.text
    }}>
      <span style={{ fontSize: '1.2rem' }}>ℹ️</span>
      <span>
        {t('visualization.statsbombInfo')}
      </span>
    </div>
  );
}

function App() {
  const location = useLocation();
  const isVisualization = location.pathname === "/visualization";
  const isScouting = location.pathname === "/scouting";
  const { t } = useTranslation();

  useEffect(() => {
    const API_URL = import.meta.env.VITE_API_URL || 'https://football-api-r0f2.onrender.com';
    fetch(`${API_URL}/health`, {
      method: 'GET',
      mode: 'cors',
      cache: 'no-cache',
    }).catch(() => {
    });
  }, []);
  
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#fff',
            color: '#1f2937',
            fontWeight: 500,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            borderRadius: '8px',
            padding: '12px 16px',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
      <header
        style={{
          width: "100%",
          background: "#fff",
          color: "#1f2937",
          padding: "2.5rem 0 1.2rem 0",
          textAlign: "center",
          fontWeight: 900,
          fontSize: "2.7rem",
          letterSpacing: "0.08em",
          boxShadow: "none",
          marginBottom: "0.5rem",
          borderBottomLeftRadius: "18px",
          borderBottomRightRadius: "18px",
          position: "relative",
          zIndex: 10,
          fontFamily: "'Inter', 'Montserrat', 'Segoe UI', Arial, sans-serif",
          textShadow: "0 2px 8px rgba(0,0,0,0.03)"
        }}
      >
        <HeaderBrand />
      </header>
      <nav style={{
        background: "#343a40",
        padding: "1rem 1.5rem",
        borderBottom: "2px solid #495057",
        marginBottom: 0,
        boxShadow: "none"
      }}>
        <div style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: "30px",
          maxWidth: "1200px",
          margin: "0 auto"
        }}>
          <Link 
            to="/visualization" 
            style={{ 
              fontWeight: 600, 
              color: isVisualization ? "#fff" : "#adb5bd", 
              background: isVisualization ? "#1d4ed8" : "transparent",
              textDecoration: "none", 
              fontSize: "1.1rem",
              padding: "8px 12px",
              borderRadius: "4px",
              border: isVisualization ? "2px solid #1d4ed8" : "2px solid transparent",
              transition: "color 0.2s, background 0.2s, border 0.2s",
              outline: "none"
            }}
          >
            {t('nav.visualization')}
          </Link>
          <Link 
            to="/scouting" 
            style={{ 
              fontWeight: 600, 
              color: isScouting ? "#fff" : "#adb5bd", 
              background: isScouting ? "#dc2626" : "transparent", 
              textDecoration: "none", 
              fontSize: "1.1rem",
              padding: "8px 12px",
              borderRadius: "4px",
              border: isScouting ? "2px solid #dc2626" : "2px solid transparent",
              transition: "color 0.2s, background 0.2s, border 0.2s",
              outline: "none"
            }}
          >
            {t('nav.scouting')}
          </Link>
        </div>
      </nav>
      <div className="app-content-container">
        <StatsBombInfo />
        <Routes>
          <Route path="/" element={<Navigate to="/visualization" replace />} />
          <Route path="/visualization" element={<VisualizationPage />} />
          <Route path="/scouting" element={<ScoutingPage />} />
        </Routes>
      </div>
    </>
  );
}

export default function AppWithLocation() {
  return (
    <Router>
      <Routes>
        <Route path="*" element={<App />} />
      </Routes>
    </Router>
  );
}