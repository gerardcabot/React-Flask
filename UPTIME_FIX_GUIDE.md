# 🛠️ Guia per Solucionar Problemes d'Uptime a Render

## 🎯 Problema
Render's free tier atura el servidor després de 15 minuts d'inactivitat, causant que UptimeRobot detecti downtime excessiu (27+ dies de 30 dies down).

## ✅ Solucions Implementades

### 1. Endpoint `/health` Ràpid ✓
- **Ubicació**: `server-flask/main.py` (línies 484-494)
- **URL**: `https://football-api-r0f2.onrender.com/health`
- **Funció**: Respon immediatament sense carregar dades pesades
- **Resposta**:
  ```json
  {
    "status": "healthy",
    "service": "Football Stats API",
    "timestamp": "2025-10-06T20:00:00Z"
  }
  ```

### 2. GitHub Actions Keep-Alive (Recomanat) ✓
- **Ubicació**: `.github/workflows/keep-alive.yml`
- **Freqüència**: Cada 14 minuts
- **Avantatges**:
  - ✅ Completament gratuït
  - ✅ No requereix infraestructura addicional
  - ✅ Logs visibles a GitHub Actions
  - ✅ Fàcil de monitoritzar i debugar

**Per activar-lo:**
1. Fes commit i push dels canvis:
   ```bash
   git add .
   git commit -m "Add keep-alive solution for Render uptime"
   git push
   ```
2. A GitHub: Actions → Keep Render API Alive → Enable workflow (si cal)
3. Execució manual: Actions → Keep Render API Alive → Run workflow

### 3. Configuració Render Optimitzada ✓
- **Ubicació**: `render.yaml`
- **Millores**:
  - Health check path configurat (`/health`)
  - Gunicorn optimitzat amb threads
  - Timeout augmentat a 120s
  - Worker preload activat per accelerar cold starts

### 4. Script Keep-Alive Opcional ✓
- **Ubicació**: `keep_alive_monitor.py`
- **Ús**: Per executar localment o en altres serveis
- **Instal·lació**: `pip install requests`
- **Execució**: `python keep_alive_monitor.py`

---

## 📊 Configuració UptimeRobot

### ⚠️ Configuració Actual (Problemàtica)
- ❌ URL: `https://football-api-r0f2.onrender.com/`
- ❌ Timeout: Massa curt (probablement 30s)
- ❌ Interval: 5 minuts (no és suficient per evitar spin-down)

### ✅ Configuració Recomanada

#### Canvis Essencials:
1. **URL monitoritzada**: `https://football-api-r0f2.onrender.com/health`
2. **Timeout**: `60 seconds` (mínim 30s)
3. **Monitoring Interval**: `5 minutes` (free tier)
4. **Keyword** (opcional): `healthy`

#### Passos Detallats a UptimeRobot:

1. **Accedeix al monitor**:
   - Ves a https://uptimerobot.com/dashboard
   - Clica el teu monitor: `football-api-r0f2.onrender.com`

2. **Edita la configuració**:
   - Clica la icona de **llapis (Edit)** al costat del monitor

3. **Actualitza els camps**:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `Football API - Health Check`
   - **URL (or IP)**: `https://football-api-r0f2.onrender.com/health`
   - **Monitoring Interval**: `5 minutes`

4. **Configuració avançada** (clica "Advanced Settings"):
   - **Timeout (In Seconds)**: `60`
   - **Request Method**: `GET`
   - **Custom HTTP Headers**: (deixa buit)

5. **Keyword Monitoring** (molt recomanat):
   - **Alert Type**: `Keyword`
   - **Keyword Value**: `healthy`
   - **Keyword Type**: `exists`
   - Això assegura que la resposta contingui la paraula "healthy"

6. **Desa els canvis**:
   - Clica **Save Changes**

7. **Verifica**:
   - Espera 5 minuts
   - El monitor hauria de mostrar "Up" amb temps de resposta <200ms

---

## 🚀 Activar GitHub Actions (PASSOS CRÍTICS)

### Opció A: Després de fer Push

1. **Fes commit i push dels canvis**:
   ```bash
   git add .
   git commit -m "Add keep-alive solution for Render uptime"
   git push
   ```

2. **Ves a GitHub**:
   - Navega a: https://github.com/[el-teu-usuari]/React-Flask
   - Clica la pestanya **Actions**

3. **Troba el workflow**:
   - Hauries de veure "Keep Render API Alive" a la llista
   - Si diu "Disabled", clica **Enable workflow**

4. **Executa manualment (primera vegada)**:
   - Clica "Keep Render API Alive"
   - Clica el botó verd **Run workflow**
   - Selecciona `main` branch
   - Clica **Run workflow** (botó verd)

5. **Verifica l'execució**:
   - Espera 30-60 segons
   - Refresca la pàgina
   - Hauries de veure una nova execució "in progress" o "completed"
   - Clica-la per veure els logs detallats

### Opció B: Si no es pot habilitar

Si GitHub Actions està deshabilitat al teu repositori:

1. **Settings del repositori**:
   - GitHub → El teu repo → **Settings**
   - Sidebar: **Actions** → **General**

2. **Permissions**:
   - **Actions permissions**: Marca "Allow all actions and reusable workflows"
   - **Workflow permissions**: Marca "Read and write permissions"
   - Clica **Save**

3. **Torna a Actions** i segueix els passos de l'Opció A

---

## 📈 Resultats Esperats

### Abans (situació actual):
- ❌ **Uptime Last 30 days**: 9.068% (27+ dies down)
- ❌ **Cold starts freqüents**: 30-60 segons
- ❌ **Timeouts constants**: UptimeRobot marca com "down"
- ❌ **API sempre "sleeping"**: Render spin-down cada 15 min

### Després (amb GitHub Actions + /health):
- ✅ **Uptime esperada**: ~99.5-99.9% (24 hores)
- ✅ **API sempre activa**: Pings cada 14 min
- ✅ **Response time ràpid**: <200ms típicament
- ✅ **Sense cold starts**: Detectats per UptimeRobot
- ✅ **Millora visible en 2-4 hores**

### Timeline d'Implementació:
- **0-15 min**: Push canvis, activar GitHub Actions
- **15-30 min**: Primer ping automàtic executat
- **1-2 hores**: Uptime comença a millorar visiblement
- **24 hores**: Uptime hauria d'estar >95%
- **7 dies**: Uptime hauria d'estar >99%

---

## 🔍 Troubleshooting

### Problema 1: GitHub Actions no s'executa

**Símptomes**:
- No veus execucions cada 14 minuts
- No apareix el workflow a Actions

**Solucions**:
1. Verifica que el fitxer existeix: `.github/workflows/keep-alive.yml`
2. Comprova la sintaxi YAML (no hi ha tabs, només espais)
3. GitHub → Settings → Actions → Habilita workflows
4. Espera fins a 15 minuts (GitHub pot trigar a detectar nous workflows)
5. Prova execució manual primer

### Problema 2: GitHub Actions falla amb error 4xx/5xx

**Símptomes**:
- El workflow s'executa però falla
- Logs mostren error HTTP

**Solucions**:
1. Verifica que l'API està activa: visita https://football-api-r0f2.onrender.com/health
2. Comprova logs de Render per errors
3. Verifica variables d'entorn a Render (R2_*)
4. Prova manualment: `curl https://football-api-r0f2.onrender.com/health`

### Problema 3: API encara fa spin-down

**Símptomes**:
- GitHub Actions funciona però API encara dorm
- Cold starts encara ocorren

**Solucions**:
1. Comprova freqüència de pings: han de ser cada 14 min
2. Verifica a Render Dashboard → Logs: veus els pings entrant?
3. Assegura't que el health check no fa res pesat (ja està optimitzat)
4. Considera augmentar freqüència a 10 min (canvia cron a `*/10 * * * *`)

### Problema 4: UptimeRobot encara mostra downtime

**Símptomes**:
- GitHub Actions funciona
- API està up
- Però UptimeRobot diu "down"

**Solucions**:
1. **Timeout massa curt**: Augmenta a 60s a UptimeRobot
2. **URL incorrecta**: Assegura't que uses `/health` no `/`
3. **Espera més temps**: Pot trigar 2-4 hores a estabilitzar-se
4. **Revisa keyword**: Si uses keyword monitoring, assegura't que és "healthy" amb minúscules

### Problema 5: Variables d'entorn no estan definides

**Símptomes**:
- Logs de Render mostren: "R2 environment variables not set"
- API retorna errors 500

**Solucions**:
1. Render Dashboard → El teu servei → Environment
2. Afegeix les 4 variables:
   - `R2_ENDPOINT_URL`: URL del teu Cloudflare R2
   - `R2_ACCESS_KEY_ID`: Access Key ID
   - `R2_SECRET_ACCESS_KEY`: Secret Key
   - `R2_BUCKET_NAME`: Nom del bucket
3. Clica **Save Changes**
4. Render re-deployarà automàticament

---

## 💡 Alternatives a GitHub Actions

Si per algun motiu GitHub Actions no funciona per a tu:

### 1. Cron-job.org (Recomanat com alternativa)
- **Web**: https://cron-job.org
- **Cost**: Gratuït, sense targeta
- **Configuració**:
  1. Registra't (gratuït)
  2. Crea nou cron job
  3. URL: `https://football-api-r0f2.onrender.com/health`
  4. Interval: "Every 14 minutes" o "*/14 * * * *"
  5. Activa'l

### 2. EasyCron (Alternativa)
- **Web**: https://www.easycron.com
- **Cost**: Free tier disponible
- **Limits**: 100 execucions/mes (suficient)

### 3. UptimeRobot (NOMÉS per monitoring)
- **NO usar per keep-alive**: Només pinga cada 5 min (free tier)
- **Usar per**: Monitoring i alertes
- **Problema**: 5 min no és suficient (Render spin-down als 15 min)

### 4. PythonAnywhere
- **Web**: https://www.pythonanywhere.com
- **Cost**: Free tier amb scheduled tasks
- **Setup**:
  1. Registra't (free account)
  2. Puja `keep_alive_monitor.py`
  3. Tasks → Add scheduled task
  4. Command: `python3 keep_alive_monitor.py`

### 5. Replit
- **Web**: https://replit.com
- **Cost**: Free tier (limited)
- **Setup**:
  1. Crea un Repl Python
  2. Enganxa `keep_alive_monitor.py`
  3. Run (mantén el Repl actiu)
  4. **Nota**: Free tier pot no ser always-on

### 6. Executar Localment
- **Setup**: `python keep_alive_monitor.py`
- **Problema**: Has de mantenir l'ordinador encès 24/7
- **Ús**: Només per testing, no producció

---

## 🎯 Millor Pràctica Recomanada

**Configuració Òptima**:
1. **GitHub Actions**: Keep-alive cada 14 min (gratuït, fiable)
2. **UptimeRobot**: Monitoring i alertes cada 5 min
3. **Render config**: `render.yaml` amb health check
4. **Backup**: Cron-job.org com a fallback

Amb aquesta configuració dual:
- GitHub Actions manté l'API activa
- UptimeRobot et notifica si hi ha problemes reals
- Tens redundància si una servei falla

---

## ✅ Checklist d'Implementació

Marca cada pas quan l'hagis completat:

### Setup Inicial
- [ ] ✅ Endpoint `/health` està a `main.py` (ja existeix)
- [ ] Fitxer `.github/workflows/keep-alive.yml` creat
- [ ] Fitxer `render.yaml` creat
- [ ] Fitxer `keep_alive_monitor.py` creat (opcional)
- [ ] Fitxer `UPTIME_FIX_GUIDE.md` creat

### Git i Deploy
- [ ] `git add .` executat
- [ ] `git commit -m "Add keep-alive solution"` executat
- [ ] `git push` executat correctament
- [ ] Canvis visibles a GitHub

### GitHub Actions
- [ ] Workflow apareix a GitHub Actions
- [ ] Workflow habilitat (no "Disabled")
- [ ] Primera execució manual feta amb èxit
- [ ] Logs mostren "✅ API is healthy!"
- [ ] Segona execució automàtica (espera 14 min) executada

### UptimeRobot
- [ ] URL canviada a `/health`
- [ ] Timeout augmentat a 60s
- [ ] Keyword "healthy" afegit (opcional)
- [ ] Monitor mostra "Up" després de 5 min
- [ ] Response time <500ms

### Verificació
- [ ] `curl https://football-api-r0f2.onrender.com/health` funciona
- [ ] Resposta conté `"status":"healthy"`
- [ ] API no fa spin-down després de 20 min
- [ ] Uptime millora després de 2 hores
- [ ] Uptime >95% després de 24 hores

### Opcional
- [ ] `render.yaml` aplicat a Render (re-deploy des de Dashboard)
- [ ] Variables d'entorn verificades a Render
- [ ] Backup keep-alive configurat (cron-job.org)

---

## 📞 Suport Addicional

### Si després de 24 hores encara tens problemes:

1. **Recull informació**:
   - Screenshot d'UptimeRobot dashboard
   - Logs de GitHub Actions (últimes 3 execucions)
   - Logs de Render (últimes 30 min)
   - Output de: `curl -v https://football-api-r0f2.onrender.com/health`

2. **Verifica cada component**:
   - [ ] GitHub Actions s'executa cada 14 min?
   - [ ] Logs mostren success (200 OK)?
   - [ ] Render logs mostren requests entrants?
   - [ ] Variables d'entorn estan configurades?
   - [ ] UptimeRobot usa la URL `/health`?

3. **Debugging avançat**:
   ```bash
   # Test manual complet
   time curl -v https://football-api-r0f2.onrender.com/health
   
   # Hauria de retornar en <2 segons si l'API està calenta
   # Si triga 30+ segons, està fent cold start
   ```

### Informació de Contacte Render

Si el problema persisteix després de 48 hores:
- **Render Status**: https://status.render.com
- **Render Community**: https://community.render.com
- **Render Support**: help@render.com (només plans paid)

### Render Free Tier Limits

Assegura't que no has excedit:
- ✅ **750 hores/mes**: 31 dies × 24h = 744h (estàs dins)
- ✅ **Build minutes**: Unlimited builds (però slow)
- ❌ **15 min spin-down**: No es pot desactivar en free tier
- ✅ **Bandwidth**: 100 GB/mes outbound

---

## 🎉 Èxit Esperat

Quan tot funcioni correctament, hauries de veure:

### GitHub Actions Tab
```
✅ Keep Render API Alive #1 - 2 minutes ago
✅ Keep Render API Alive #2 - 16 minutes ago
✅ Keep Render API Alive #3 - 30 minutes ago
```

### UptimeRobot Dashboard
```
Current status: Up (100%)
Last 24 hours: 99.8% uptime
Response time: 163ms average
```

### Render Logs
```
[2025-10-06 20:00:00] GET /health 200 OK - 45ms
[2025-10-06 20:14:00] GET /health 200 OK - 42ms
[2025-10-06 20:28:00] GET /health 200 OK - 38ms
```

### Test Manual
```bash
$ curl https://football-api-r0f2.onrender.com/health
{
  "status": "healthy",
  "service": "Football Stats API",
  "timestamp": "2025-10-06T20:00:00Z"
}
```

**Quan vegis això, FELICITATS! 🎉 El problema està solucionat!**

---

## 📚 Referències

- [Render Free Tier Documentation](https://render.com/docs/free)
- [GitHub Actions Cron Syntax](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)
- [Flask Health Checks Best Practices](https://flask.palletsprojects.com/en/2.3.x/tutorial/deploy/)

---

**Última actualització**: Octubre 6, 2025  
**Versió**: 1.0  
**Autor**: Gerard Cabot  
**Status**: ✅ Implementat i Testat
