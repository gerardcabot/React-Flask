Estrelles del Futur
Eina d'anàlisi i scouting de futbolistes amb models de potencial personalitzables.
🚀 Guia d'Instal·lació
Per executar l'aplicació localment, segueix aquestes passes des del teu terminal.
1. Preparar el Projecte
Primer, clona el repositori i navega a la carpeta del projecte.
git clone https://github.com/gerardcabot/React-Flask.git
cd React-Flask
Use code with caution.
Bash
2. Descarregar i Col·locar les Dades
Les dades del projecte són massa grans per a GitHub i s'han de descarregar manualment.
Descarrega les dades des de l'enllaç següent:
https://mega.nz/file/GU8lQJZL#sXN4YrdTBABAtt_p27fLBWcg6Kc7B4SalQU75gGbUEg
Descomprimeix el fitxer data.zip que has descarregat.
Mou la carpeta data resultant a l'arrel del projecte (React-Flask). L'estructura de carpetes ha de ser la següent:
React-Flask/
├── data/
├── server-flask/
└── ...
Use code with caution.
3. Instal·lar les Dependències
Abans d'executar l'aplicació, has d'instal·lar les dependències tant per al backend com per al frontend.
# Instal·lar dependències del frontend (React)
npm install

# Crear i activar un entorn virtual per a Python
python -m venv venv
source venv/bin/activate  # A Windows: venv\Scripts\activate

# Instal·lar dependències del backend (Flask)
pip install -r requirements.txt
Use code with caution.
Bash
4. Executar l'Aplicació
Necessitaràs dos terminals oberts a la carpeta arrel del projecte (React-Flask).
Terminal 1: Executar el Backend (Flask)
# Activa l'entorn virtual
source venv/bin/activate  # O venv\Scripts\activate a Windows

# Navega a la carpeta del servidor i inicia'l
cd server-flask
python main.py
Use code with caution.
Bash
El backend estarà funcionant a http://localhost:5000.
Terminal 2: Executar el Frontend (React)
# Inicia el servidor de desenvolupament
npm run dev
Use code with caution.
Bash
El frontend estarà disponible a http://localhost:5173.
Ja ho tens tot a punt! Obre http://localhost:5173 al teu navegador per utilitzar l'eina.