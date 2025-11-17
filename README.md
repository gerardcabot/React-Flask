# ⚽ Stars of the Future - Football Talent Analysis Platform

> **A full-stack Football Analytics Platform powered by Machine Learning**  
> Predict career potential for U-21 talents, explore player performance data, and build custom scouting models – all in one place.

**🌐 Live Demo:** [https://react-flask-psi.vercel.app/](https://react-flask-psi.vercel.app/)


---

## 🎯 Overview

**Stars of the Future** is a comprehensive web application that combines **interactive data visualizations**, **machine learning predictions**, and **customizable scouting models** to help identify and analyze football talent. Built with modern web technologies and deployed on serverless infrastructure.

### Key Highlights
- 🎨 **Interactive Visualizations**: Position heatmaps, pass maps, xG-based shot analysis, pressure-resistant metrics
- 🤖 **AI Predictions**: XGBoost model trained on 15+ years of LaLiga data to forecast peak career potential (U-21 focus)
- 🛠️ **Custom Model Builder**: Choose your own KPIs and weights → the platform automatically trains and deploys a brand-new model for you in the background using GitHub Actions + Cloudflare R2 (no server timeouts!)
- 🌍 **Multi-language**: English, Spanish & Catalan support
- ⚡ **Real-time Training**: Automated ML model training via GitHub Actions (45-90 minutes)

---

## ✨ Features

### 📊 Player Analysis & Visualization
- **Position Heatmaps**: Visualize player movement patterns and activity zones on the pitch
- **Pass Maps**: Interactive pass completion analysis with field zone breakdowns and final third filtering
- **Shot Maps**: xG-based shot analysis with accuracy metrics and goal probability visualization
- **Pressure Heatmaps**: Defensive engagement and pressure resistance visualization
- **Aggregated Metrics**: Season-by-season performance trends with customizable metric selection
- **Goalkeeper Analysis**: Specialized metrics and charts for goalkeeper performance

### 🎯 AI-Powered Talent Scouting
- **Default Model V14**: Pre-trained XGBoost regressor for peak career potential prediction (0-200 scale)
- **Custom Model Builder**: 
  - Choose your own KPIs and weights for impact and target metrics
  - Position-specific analysis (Attackers, Midfielders, Defenders)
  - Automatic training and deployment via GitHub Actions
  - Models stored in Cloudflare R2 for instant access
  - No server timeouts - training happens asynchronously
- **U-21 Focus**: Age-adjusted predictions for young talents
- **Real-time Predictions**: Get instant potential scores based on historical data patterns

### 🛠️ Custom Model Training Pipeline
1. **Select KPIs**: Choose impact and target KPIs for your scouting criteria
2. **Configure Features**: Customize ML features or use intelligent defaults
3. **Trigger Training**: GitHub Actions automatically trains your model (no server load!)
4. **Monitor Progress**: Track training status (45-90 minutes)
5. **Deploy & Use**: Model automatically available for predictions once training completes

---

## 🏗️ Tech Stack

### Frontend
- React 18 + Vite
- Chart.js + react-chartjs-2
- Konva.js + react-konva (interactive pitch)
- react-i18next (EN / ES / CA)
- react-hot-toast
- Deployed on Vercel

### Backend
- Flask (Python)
- pandas, numpy, scikit-learn, XGBoost
- boto3 (Cloudflare R2)
- Flask-Limiter, Pydantic
- Deployed on Render (free tier)

### Infrastructure & DevOps
- Cloudflare R2 (model & asset storage)
- GitHub Actions (custom model training + keep-alive)
- Rate limiting & CORS
- Automatic cold-start handling with retry logic

---

## 📈 Data Source

This project uses **StatsBomb Open Data** – Men's Spanish LaLiga:
- Seasons 2004/05 – 2020/21 (17 seasons)
- Event-level data (passes, shots, pressures, GK actions, etc.)
- License: CC BY-SA 4.0

**Huge thanks** to [@StatsBomb](https://twitter.com/StatsBomb) and [@Hudl](https://twitter.com/Hudl) for making high-quality open football data available.

---

## 🚀 Getting Started

### For Users
Just visit → [https://react-flask-psi.vercel.app/](https://react-flask-psi.vercel.app/)

---

## 🎓 How It Works

### Default ML Model
XGBoost regressor trained on 17 seasons of LaLiga data to predict a player’s **peak career potential** (0–200 scale) based on U-21 performance.

### Custom Model Builder
1. You pick KPIs & weights via the web UI  
2. Backend triggers a GitHub Actions workflow  
3. Workflow trains the model (45–90 min)  
4. Model is uploaded to Cloudflare R2  
5. Instantly available for predictions

No server timeouts – everything runs asynchronously!

---

## 🔒 Security & Performance

- Rate limiting (1000 req/day, 200/hour per IP)
- Full input validation with Pydantic
- Secure CORS
- Structured error handling
- Automatic Render keep-alive (every 2h)
- Frontend retry logic for cold starts

---

## 📝 Project Structure

```
React-Flask/
├── client-react/          # React + Vite frontend
│   ├── src/
│   │   ├── components/
│   │   ├── i18n/          # EN, ES, CA translations
│   │   └── utils/
│   └── vite.config.ts
├── server-flask/          # Flask API
│   ├── main.py
│   ├── model_trainer/
│   └── requirements.txt
├── .github/workflows/
│   ├── train_model.yml    # Custom model training
│   └── keep-alive.yml     # Render wake-up
└── README.md
```

---

## 🤝 Contributing

We welcome contributions! Feel free to:

- Open an issue
- Submit a pull request
- Suggest new features or report bugs
- Improve translations

Just fork the repo and send a PR – all help is appreciated!

---

## 📄 License

The **code** in this repository is provided under the MIT License.  
The football data used is **StatsBomb Open Data** licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

---

## 🙏 Acknowledgments

- StatsBomb & Hudl for the amazing open data
- All the open-source libraries and tools that made this possible
- Everyone who has tested, given feedback, or starred the project ❤️

---

**Built with ❤️ for the football analytics community**

🌐 **Try it now:** [https://react-flask-psi.vercel.app/](https://react-flask-psi.vercel.app/)

---

*This started as a weekend passion project combining football + data science and turned into the most challenging (and rewarding) thing I’ve ever built. Any feedback – positive, negative, bugs, ideas – is hugely appreciated!*
