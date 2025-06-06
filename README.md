### 1. Clonar el Repositori

Obre un terminal i clona aquest repositori al teu ordinador.

```bash
git clone https://github.com/el-teu-usuari/el-teu-repositori.git
cd el-teu-repositori

2. Configurar l'Entorn de Python

És altament recomanable utilitzar un entorn virtual per gestionar les dependències de Python i evitar conflictes.

# Crear un entorn virtual
python -m venv venv

# Activar l'entorn virtual
# A macOS/Linux:
source venv/bin/activate
# A Windows:
venv\Scripts\activate

Un cop activat l'entorn, instal·la tots els paquets necessaris des del fitxer requirements.txt.

pip install -r requirements.txt

3. Descarregar les Dades del Projecte

Les dades d'esdeveniments necessàries per executar l'aplicació són massa grans per ser allotjades a GitHub. Cal descarregar-les manualment.

Descarrega el fitxer data.zip des del següent enllaç:

https://mega.nz/file/GU8lQJZL#sXN4YrdTBABAtt_p27fLBWcg6Kc7B4SalQU75gGbUEg

Descomprimeix el fitxer. Un cop descarregat, descomprimeix el fitxer data.zip. Això crearà una carpeta anomenada data.

Mou la carpeta data. Assegura't de moure aquesta carpeta data a l'arrel del teu projecte clonat. L'estructura final hauria de ser així:

REACT-FLASK/
├── data/                 <-- La carpeta que acabes de moure
│   ├── 2003_2004/
│   ├── 2004_2005/
│   ├── ...
│   └── player_index.json
├── server-flask/
├── client-react
├── ...
├── package.json
└── README.md

4. Configurar i Executar el Frontend (React)

Navega a la carpeta arrel del projecte (si no hi ets ja) i instal·la les dependències de Node.js.

npm install

Un cop finalitzada la instal·lació, pots iniciar el servidor de desenvolupament del frontend.

npm run dev

Això iniciarà l'aplicació React, que normalment estarà disponible a http://localhost:5173.

5. Executar el Backend (Flask)

Obre un nou terminal (mantingues l'anterior obert per al frontend) i activa de nou l'entorn virtual de Python.

# A macOS/Linux:
source venv/bin/activate
# A Windows:
venv\Scripts\activate

Navega a la carpeta del servidor Flask i inicia'l.

cd server-flask
python main.py

El servidor de Flask s'iniciarà i estarà escoltant a http://localhost:5000.

Ja estàs a punt!

Amb el frontend i el backend en marxa, obre el teu navegador a http://localhost:5173 per començar a utilitzar "Estrelles del Futur".


<!-- # Estrelles del Futur

## Installation

Install dependencies using:

```
pip install -r requirements.txt

``` -->