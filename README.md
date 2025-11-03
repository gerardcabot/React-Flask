# ⚽ Stars of the Future - Football Talent Analysis Platform

**Live Demo:** [https://react-flask-psi.vercel.app/visualization](https://react-flask-psi.vercel.app/visualization)

A comprehensive web application for football player analysis and talent scouting, featuring machine learning-powered potential prediction and interactive data visualizations.

##  **Core Features**

###  **Player Analysis & Visualization**
- **Interactive position heatmaps** showing player movement patterns
- **Pass completion analysis** with field zone breakdowns  
- **Pressure resistance metrics** and defensive engagement visualization
- **Shot mapping** with accuracy and location analytics
- **Multi-language support** (English, Spanish, Catalan)

###  **AI-Powered Talent Prediction**
- **Machine Learning models** trained on football statistics data
- **Custom model builder** for personalized scouting criteria
- **Position-specific analysis** (Attackers, Midfielders, Defenders)
- **Age-adjusted predictions** for players under 21
- **Real-time model training** via GitHub Actions integration

###  **Technical Architecture**
- **Frontend**: React with Vite, Chart.js, Konva for interactive visualizations
- **Backend**: Flask API with pandas data processing and scikit-learn ML
- **Data Storage**: Cloudflare R2 for scalable model and asset storage
- **CI/CD**: GitHub Actions for automated model training and deployment
- **Deployment**: Frontend on Vercel, Backend on Render

##  **Live Application**

** Access the app:** [https://react-flask-psi.vercel.app/visualization](https://react-flask-psi.vercel.app/visualization)

### **Quick Start Guide:**
1. **Player Analysis**: Select any player to view comprehensive performance visualizations
2. **Talent Scouting**: Choose a young player (U21) to predict their future potential
3. **Custom Models**: Build your own ML model with personalized KPI weights
4. **Multi-language**: Switch between EN/ES/CA in the top navigation

##  **Machine Learning Pipeline**

### **Automated Training System**
- Custom models trained on-demand via GitHub Actions
- Transparent, publicly visible training process
- Models automatically deployed to Cloudflare R2 storage
- Support for position-specific feature engineering

### **Prediction Capabilities**
- **Default Model V14**: Pre-trained on comprehensive football statistics
- **Custom Models**: User-defined KPI weights and feature selection
- **Performance Metrics**: R², RMSE, and feature importance analysis
- **Scalable Architecture**: Handle thousands of predictions per minute

##  **Security & Performance**

### **Production-Ready Features**
- **Rate limiting** on all API endpoints
- **Input validation** with comprehensive schemas  
- **CORS configuration** for secure cross-origin requests
- **Error handling** with structured logging
- **Health monitoring** with automated uptime checks

### **Optimizations**
- **Model caching** to reduce loading times
- **CDN integration** for fast global asset delivery
- **Responsive design** optimized for all devices
- **Progressive loading** for large datasets
