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

### **Project Structure**





# Estrelles del Futur
Eina d'anàlisi i scouting de futbolistes amb models de potencial personalitzables.

## 🎓 Arquitectura i Transparència del Projecte

Aquest projecte implementa un sistema de Machine Learning amb les següents característiques tècniques:

### 🚀 GitHub Actions per Entrenament de Models
- Els models customitzats s'entrenen automàticament amb **GitHub Actions**
- El procés complet és transparent i visible públicament
- Permet monitoritzar l'entrenament en temps real
- Evita limitacions de temps en servidors gratuïts (Render)

### 📦 Cloudflare R2 per Emmagatzematge
- Models entrenats a **Cloudflare R2** (compatible amb S3)
- Accés ràpid i global a models i dades
- Integració nativa amb el sistema de prediccions

### 🔍 Per Què És Públic?
Aquest repositori és públic intencionalment per demostrar:
- ✅ **Bones pràctiques de CI/CD** per Machine Learning
- ✅ **Arquitectura escalable** amb cloud storage
- ✅ **Codi net i ben documentat**
- ✅ **Transparència** en processos d'entrenament

**Nota de Seguretat:** No hi ha dades sensibles exposades. Els workflows públics mostren el procés d'entrenament, que és una característica del portfolio, no un risc de seguretat.

---

## Guia d'Instal·lació i Configuració (Des de Zero)
Aquesta guia està dissenyada per configurar el projecte en un ordinador Windows nou, anticipant els problemes més comuns.

### Requisits Previs: Eines de Desenvolupament
Si el teu ordinador no té les eines de desenvolupament, instal·la-les en aquest ordre:

#### Instal·la Git:
- Ves a [git-scm.com/download/win](https://git-scm.com/download/win) i descarrega l'instal·lador.
- Durant la instal·lació, accepta les opcions per defecte. Assegura't que l'opció "Git from the command line and also from 3rd-party software" estigui seleccionada per poder usar git al terminal.
- **Important**: Després d'instal·lar, tanca i obre de nou el terminal.

#### Instal·la Node.js:
- Ves a [nodejs.org](https://nodejs.org) i descarrega la versió LTS (Long-Term Support).
- Durant la instal·lació, pots marcar la casella "Automatically install the necessary tools...". Això obrirà un terminal addicional per instal·lar eines de compilació de Microsoft (pot trigar una bona estona, sigues pacient).
- **Important**: Després d'instal·lar, tanca i obre de nou el terminal.

#### Instal·la Python (Versió Recomanada):
- Per assegurar la compatibilitat amb les llibreries del projecte, es recomana instal·lar **Python 3.11**.
- Ves a [python.org/downloads/windows](https://www.python.org/downloads/windows) i busca un instal·lador per a la versió 3.11 (p. ex., Python 3.11.8).
- **Molt Important**: A la primera pantalla de l'instal·lador, marca la casella "Add python.exe to PATH".

### Pas 1: Preparar el Projecte
Clona el repositori a la teva carpeta d'usuari, que és el lloc ideal per als teus projectes.

```bash
# Navega a la teva carpeta desitjada
cd ~/projectes

# Clona el repositori
git clone https://github.com/gerardcabot/React-Flask.git

# Entra a la carpeta del projecte
cd React-Flask
```

### Pas 2: Descarregar i Col·locar les Dades
Les dades del projecte són massa grans per a GitHub i s'han de descarregar manualment.
- Descarrega les dades des de l'enllaç següent: [Enllaç de descàrrega](https://mega.nz/file/GU8lQJZL#sXN4YrdTBABAtt_p27fLBWcg6Kc7B4SalQU75gGbUEg)
- Descomprimeix el fitxer `data.zip` que has descarregat.
- Mou la carpeta `data` resultant a l'arrel del projecte (`React-Flask`). L'estructura de carpetes ha de ser:

```
React-Flask/
├── data/
├── client-react/
├── server-flask/
└── ...
```

### Pas 3: Instal·lar les Dependències
Aquest projecte té dues parts (backend i frontend) i cadascuna té les seves pròpies dependències.

#### A. Backend (Flask / Python)
Navega a la carpeta del servidor:

```bash
cd server-flask
```

Crea i activa un entorn virtual amb Python 3.11:

```bash
# Crea l'entorn virtual especificant la versió correcta
py -3.11 -m venv venv

# Activa l'entorn (el teu terminal mostrarà "(venv)" al principi)
.\venv\Scripts\activate
```

Instal·la les dependències de Python:
Aquesta comanda inclou una solució per a xarxes corporatives (firewalls). Si no ets en una, també funcionarà.

```bash
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

#### B. Frontend (React / Node.js)
Navega a la carpeta del client des de l'arrel del projecte:

```bash
# Si ets a 'server-flask', torna a l'arrel primer
cd ..

# Entra a la carpeta del client
cd client-react
```

Instal·la les dependències de Node.js:

```bash
npm install
```

### Pas 4: Executar l'Aplicació
Necessitaràs dos terminals oberts per executar el backend i el frontend simultàniament.

#### Terminal 1: Executar el Backend (Flask)

```bash
# Ves a la carpeta del servidor
cd C:\ruta\al\teu\projecte\React-Flask\server-flask

# Activa l'entorn virtual si no ho està
.\venv\Scripts\activate

# Executa el servidor
python main.py
```

El backend estarà funcionant a `http://localhost:5000`.

#### Terminal 2: Executar el Frontend (React)

```bash
# Ves a la carpeta del client
cd C:\ruta\al\teu\projecte\React-Flask\client-react

# Inicia el servidor de desenvolupament
npm run dev
```

El frontend estarà disponible a `http://localhost:5173`.

Ja ho tens tot a punt! Obre `http://localhost:5173` al teu navegador per utilitzar l'eina.

### Solució de Problemes Comuns (Troubleshooting)
Si trobes algun error durant la instal·lació, aquí tens les solucions als problemes més habituals:

#### Error: [SSL: CERTIFICATE_VERIFY_FAILED]
- **Causa**: Estàs en una xarxa corporativa o amb un firewall que intercepta el trànsit segur.
- **Solució**: Utilitza la comanda `pip install` amb el paràmetre `--trusted-host` com s'indica al pas 3A.

#### Error: ReadTimeoutError durant pip install
- **Causa**: La teva connexió a internet és lenta i `pip` es rendeix abans de descarregar paquets grans.
- **Solució**: Afegeix el paràmetre `--timeout` a la comanda:

```bash
pip install --timeout=100 -r requirements.txt
```

#### Error: metadata-generation-failed o molts errors de compilació (C++)
- **Causa**: Estàs utilitzant una versió de Python (p. ex., 3.12 o 3.13) que no és compatible amb les versions de les llibreries del projecte (com `numpy`).
- **Solució**: Assegura't d'instal·lar la versió recomanada (Python 3.11) i crear l'entorn virtual amb:

```bash
py -3.11 -m venv venv
```