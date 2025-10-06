# 🤖 GitHub Actions Model Training Setup

## 📋 Overview

Aquesta solució permet entrenar models ML personalitzats mitjançant GitHub Actions, evitant els problemes de timeout que hi ha a Render free tier. Quan l'usuari crea un model des de la web, el backend triggera automàticament un GitHub Actions workflow que s'encarrega de l'entrenament.

## 🎯 Avantatges

✅ **Sense timeouts**: GitHub Actions permet execucions de fins a 6 hores  
✅ **Gratuït**: 2000 minuts/mes en free tier  
✅ **Logs detallats**: Tots els logs visibles a GitHub  
✅ **Fiable**: No depèn de Render staying awake  
✅ **UX millorada**: L'usuari pot veure el progrés en temps real  

---

## 🔧 Setup Complet

### 1. Crear GitHub Personal Access Token

Aquest token permet al backend de Render triggerar workflows de GitHub Actions.

#### Passos:

1. **Ves a GitHub Settings**:
   - Clica la teva foto de perfil → **Settings**
   - O visita: https://github.com/settings/profile

2. **Developer Settings**:
   - Scroll fins a baix del menú lateral esquerre
   - Clica **Developer settings**

3. **Personal Access Tokens**:
   - Clica **Personal access tokens** → **Tokens (classic)**
   - Clica **Generate new token** → **Generate new token (classic)**

4. **Configurar el Token**:
   - **Note**: `React-Flask Model Training` (o el nom que vulguis)
   - **Expiration**: Selecciona `No expiration` o `90 days` (recomanat renovar cada 90 dies)
   - **Select scopes**: 
     - ✅ Marca **`repo`** (accés complet al repositori)
     - ✅ Això també marca automàticament `workflow` que és el que necessitem
   
5. **Generar i Copiar**:
   - Clica **Generate token** (botó verd a baix)
   - **⚠️ IMPORTANT**: Copia el token IMMEDIATAMENT (comença amb `ghp_`)
   - No podràs tornar-lo a veure després!
   - Exemple: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

### 2. Afegir Token com a Secret a Render

Ara cal afegir aquest token com a variable d'entorn al servei de Render.

#### Passos:

1. **Ves a Render Dashboard**:
   - https://dashboard.render.com
   - Selecciona el teu servei: `football-api-r0f2`

2. **Environment Variables**:
   - Al menú lateral esquerre, clica **Environment**
   - O ves directament a la secció de variables d'entorn

3. **Afegir Nova Variable**:
   - Clica **Add Environment Variable**
   - **Key**: `GITHUB_TOKEN`
   - **Value**: Enganxa el token que has copiat (comença amb `ghp_`)
   - Clica **Save Changes**

4. **Re-deploy Automàtic**:
   - Render re-deployarà automàticament el servei
   - Espera que digui "Live" (2-5 minuts)

---

### 3. Configurar GitHub Secrets (per al Workflow)

El workflow de GitHub Actions necessita accedir a Cloudflare R2 per entrenar el model.

#### Passos:

1. **Ves al teu repositori a GitHub**:
   - https://github.com/gerardcabot/React-Flask

2. **Settings del Repositori**:
   - Clica **Settings** (tab a dalt)

3. **Secrets and variables**:
   - Al menú lateral esquerre: **Secrets and variables** → **Actions**

4. **Afegir els 4 Secrets**:
   Clica **New repository secret** per a cada un:

   **Secret 1:**
   - Name: `R2_BUCKET_NAME`
   - Secret: El nom del teu bucket de Cloudflare R2
   - Clica **Add secret**

   **Secret 2:**
   - Name: `R2_ENDPOINT_URL`
   - Secret: URL del teu endpoint R2 (format: `https://xxxxx.r2.cloudflarestorage.com`)
   - Clica **Add secret**

   **Secret 3:**
   - Name: `R2_ACCESS_KEY_ID`
   - Secret: La teva R2 Access Key ID
   - Clica **Add secret**

   **Secret 4:**
   - Name: `R2_SECRET_ACCESS_KEY`
   - Secret: La teva R2 Secret Access Key
   - Clica **Add secret**

---

## ✅ Verificació del Setup

### Test 1: Verificar que el Backend té el Token

```bash
# Render Dashboard → football-api-r0f2 → Environment
# Hauries de veure: GITHUB_TOKEN = ******* (hidden)
```

### Test 2: Verificar que GitHub té els Secrets

```
GitHub → React-Flask → Settings → Secrets and variables → Actions
Hauries de veure:
- R2_BUCKET_NAME
- R2_ENDPOINT_URL  
- R2_ACCESS_KEY_ID
- R2_SECRET_ACCESS_KEY
```

### Test 3: Provar des de la Web

1. Ves a: https://react-flask-psi.vercel.app/visualization
2. Omple el formulari de "Custom Model Builder"
3. Clica **"Crea un model personalitzat"**
4. Hauries de veure:
   ```
   ✅ Model training started via GitHub Actions
   Model ID: custom_attacker_abc123
   ⏱️ Estimated time: 10-30 minutes
   🔗 Monitor Progress on GitHub Actions
   ```
5. Clica el link per veure l'entrenament en progrés

### Test 4: Verificar GitHub Actions

1. Ves a: https://github.com/gerardcabot/React-Flask/actions
2. Hauries de veure una nova execució de **"Train Custom ML Model"**
3. Clica-la per veure els logs en temps real
4. Quan acabi (10-30 minuts), hauria de mostrar ✅

---

## 🚀 Com Funciona

### Flow Complet:

```
1. Usuari omple formulari a la web
   ↓
2. Frontend fa POST a /api/custom_model/trigger_github_training
   ↓
3. Backend (Render) valida els paràmetres
   ↓
4. Backend crida GitHub API per triggerar el workflow
   ↓
5. GitHub Actions inicia el workflow "Train Custom ML Model"
   ↓
6. Workflow:
   - Clona el repositori
   - Instal·la dependencies
   - Executa el training script
   - Carrega dades des de R2
   - Entrena el model (10-30 min)
   - Puja el model a R2
   ↓
7. Model disponible a /api/custom_model/list
   ↓
8. Usuari pot usar el model per fer prediccions
```

### Endpoints:

**Backend:**
- `POST /api/custom_model/trigger_github_training` - Triggera l'entrenament
- `GET /api/custom_model/list` - Llista models disponibles

**GitHub API (usat pel backend):**
- `POST https://api.github.com/repos/{owner}/{repo}/dispatches`
  - Event type: `train-model-event`
  - Payload: `model_id`, `position_group`, `impact_kpis`, `target_kpis`, `ml_features`

---

## 🐛 Troubleshooting

### Error: "GitHub Actions integration not configured"

**Causa**: El token `GITHUB_TOKEN` no està configurat a Render.

**Solució**:
1. Verifica que has afegit `GITHUB_TOKEN` a Render Environment Variables
2. Re-deploya el servei
3. Prova de nou

### Error: "Failed to trigger GitHub Actions: 401"

**Causa**: El token és invàlid o ha expirat.

**Solució**:
1. Genera un nou token a GitHub
2. Actualitza `GITHUB_TOKEN` a Render
3. Re-deploya

### Error: "Failed to trigger GitHub Actions: 404"

**Causa**: El repositori o l'owner són incorrectes.

**Solució**:
1. Verifica que `GITHUB_REPO_OWNER` és `gerardcabot`
2. Verifica que `GITHUB_REPO_NAME` és `React-Flask`
3. Pots configurar-los com a variables d'entorn a Render si són diferents

### El Workflow falla amb "Secret not found"

**Causa**: Els secrets R2 no estan configurats a GitHub.

**Solució**:
1. Ves a GitHub → Settings → Secrets and variables → Actions
2. Afegeix els 4 secrets R2 (veure pas 3 del setup)

### El Workflow es queda "In Progress" indefinidament

**Causa**: Error durant l'entrenament.

**Solució**:
1. Clica el workflow a GitHub Actions
2. Revisa els logs per veure l'error específic
3. Errors comuns:
   - Dades no trobades a R2
   - KPIs invàlids
   - Memory overflow (massa features)

---

## 📊 Limits i Restriccions

### GitHub Actions Free Tier:
- ✅ **2000 minuts/mes** d'execucions
- ✅ **Execucions de fins a 6 hores**
- ✅ **20 workflows concurrents**
- ⚠️ Si superes els minuts, GitHub desactiva Actions fins al proper mes

### Estimació de Consum:
- 1 entrenament de model: **15-30 minuts**
- Entrenamemts possibles/mes: **~67-130 models**
- Per a ús normal, més que suficient!

### Render Free Tier:
- ✅ **750 hores/mes** (suficient per mantenir l'API activa)
- ✅ **Instant wake-up** amb keep-alive GitHub Actions
- ⚠️ No pot fer entrenamemts llargs (timeout 120s)

---

## 🔒 Seguretat

### Best Practices:

1. **Token Permissions**:
   - Usa el mínim de permisos necessaris (`repo` i `workflow`)
   - Renova el token cada 90 dies

2. **Secrets**:
   - Mai comparteixis el token o els secrets
   - Usa sempre variables d'entorn, no hardcodegis

3. **Repository**:
   - Mantén el repositori privat si conté informació sensible
   - Revisa regularment els logs de GitHub Actions

---

## 📚 Referències

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Repository Dispatch Event](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Render Environment Variables](https://render.com/docs/environment-variables)

---

## ✅ Checklist Final

Abans de considerar el setup complet, verifica:

- [ ] GitHub Personal Access Token creat amb scope `repo`
- [ ] `GITHUB_TOKEN` afegit a Render Environment Variables
- [ ] Render re-deployat i "Live"
- [ ] 4 secrets R2 afegits a GitHub Actions
- [ ] Test des de la web completat amb èxit
- [ ] Workflow visible a GitHub Actions
- [ ] Model entrenat i disponible a la llista

---

**Última actualització**: Octubre 6, 2025  
**Versió**: 1.0  
**Status**: ✅ Implementat i Testat
