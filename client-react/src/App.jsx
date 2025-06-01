import { BrowserRouter as Router, Routes, Route, Link, Navigate } from "react-router-dom";
import "./App.css"; // Keep your global styles
import VisualizationPage from "./VisualizationPage"; // Import the page component
import ScoutingPage from "./ScoutingPage"; // Import the scouting page component

function App() {
  return (
    <Router>
      <nav style={{
        background: "#343a40", // Darker background for better contrast
        padding: "1rem 1.5rem", // Increased padding
        borderBottom: "2px solid #495057", // Slightly thicker border
        marginBottom: 0, // Remove bottom margin if pages handle their own top padding
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)" // Subtle shadow
      }}>
        <div style={{
          display: "flex",
          justifyContent: "center", // Center links
          alignItems: "center",   // Vertically align items
          gap: "30px",          // Increased gap
          maxWidth: "1200px",    // Max width for content within nav
          margin: "0 auto"       // Center nav content
        }}>
          <Link 
            to="/visualization" 
            style={{ 
              fontWeight: 600, 
              color: "#adb5bd", // Lighter gray for inactive
              textDecoration: "none", 
              fontSize: "1.1rem", // Slightly larger font
              padding: "8px 12px", // Padding for better click area
              borderRadius: "4px",
              transition: "color 0.2s ease, background-color 0.2s ease"
            }}
            // Example active style (you might need NavLink for this or manage active state)
            onMouseOver={e => e.currentTarget.style.color = '#ffffff'}
            onMouseOut={e => e.currentTarget.style.color = '#adb5bd'}
          >
            Player Analysis
          </Link>
          <Link 
            to="/scouting" 
            style={{ 
              fontWeight: 600, 
              color: "#adb5bd", 
              textDecoration: "none", 
              fontSize: "1.1rem",
              padding: "8px 12px",
              borderRadius: "4px",
              transition: "color 0.2s ease, background-color 0.2s ease"
            }}
            onMouseOver={e => e.currentTarget.style.color = '#ffffff'}
            onMouseOut={e => e.currentTarget.style.color = '#adb5bd'}
          >
            Scouting & Potential
          </Link>
        </div>
      </nav>
      
      <div className="app-content-container"> {/* Optional: for consistent padding below nav */}
        <Routes>
          <Route path="/" element={<Navigate to="/visualization" replace />} />
          <Route path="/visualization" element={<VisualizationPage />} />
          <Route path="/scouting" element={<ScoutingPage />} />
          {/* Add other top-level routes here if needed */}
        </Routes>
      </div>
    </Router>
  );
}

export default App;