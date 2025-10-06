# 🔒 Security: Admin Secret Setup

## 📋 Overview

Per mantenir el repositori públic (per portfolio) però protegir els logs de GitHub Actions, hem implementat un sistema d'autenticació admin que només permet a l'administrador veure els links als workflows.

## 🎯 Com Funciona

### Usuaris Normals (sense secret):
```
✅ Model training started successfully
Model ID: custom_attacker_abc123
⏱️ Estimated time: 10-30 minutes.
The model will appear in the list automatically when ready.
```
❌ **NO** veuen el link al workflow de GitHub Actions

### Admin (amb secret):
```
✅ Model training started successfully
Model ID: custom_attacker_abc123
⏱️ Estimated time: 10-30 minutes.
You can monitor progress at GitHub Actions.
🔗 Monitor Progress on GitHub Actions
```
✅ **SÍ** veuen el link al workflow

---

## 🔧 Setup

### 1. Generar un Secret Fort

Genera un secret aleatori fort:

```bash
# Opció A: Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"

# Opció B: Python
python -c "import secrets; print(secrets.token_hex(32))"

# Opció C: OpenSSL
openssl rand -hex 32

# Opció D: Manual (menys segur)
# Usa un generador de passwords online i copia una string llarga
```

**Exemple de secret generat:**
```
a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789
```

---

### 2. Configurar Backend (Render)

1. **Ves a Render Dashboard**:
   - https://dashboard.render.com
   - Servei: **football-api-r0f2**

2. **Environment Variables**:
   - Clica **Environment** al menú lateral

3. **Afegir el Secret**:
   - Clica **"Add Environment Variable"**
   - **Key**: `ADMIN_SECRET`
   - **Value**: `[enganxa el secret generat]`
   - Exemple: `a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789`
   - Clica **"Save Changes"**

4. **Re-deploy**:
   - Render re-deployarà automàticament (2-3 min)

---

### 3. Configurar Frontend (Vercel)

1. **Ves a Vercel Dashboard**:
   - https://vercel.com/dashboard
   - Projecte: **react-flask-psi**

2. **Settings → Environment Variables**:
   - Clica el projecte
   - **Settings** (tab)
   - **Environment Variables** (sidebar)

3. **Afegir el Secret**:
   - Clica **"Add New"**
   - **Key**: `VITE_ADMIN_SECRET`
   - **Value**: `[el MATEIX secret que has posat a Render]`
   - **Environments**: Marca totes (Production, Preview, Development)
   - Clica **"Save"**

4. **Re-deploy**:
   - Ves a **Deployments**
   - Clica els 3 punts del deployment més recent
   - Clica **"Redeploy"**
   - O simplement fa un nou push i Vercel re-deployarà

---

## ✅ Verificació

### Test 1: Com a Admin (Tu)

1. **Assegura't que tens el secret configurat** (frontend + backend)
2. **Ves a**: https://react-flask-psi.vercel.app/visualization
3. **Crea un model personalitzat**
4. **Hauries de veure**:
   ```
   🔗 Monitor Progress on GitHub Actions
   ```
5. **Clica el link** → T'ha de portar a GitHub Actions

### Test 2: Com a Usuari Normal

1. **Obre la web en mode incognit** (sense el secret al navegador)
2. **Ves a**: https://react-flask-psi.vercel.app/visualization
3. **Crea un model personalitzat**
4. **Hauries de veure**:
   ```
   ✅ Model training started successfully
   ⏱️ Estimated time: 10-30 minutes.
   The model will appear in the list automatically when ready.
   ```
5. **NO hauries de veure** el link a GitHub Actions ✅

---

## 🔒 Seguretat

### Què està protegit:
- ✅ Logs de GitHub Actions (només admin)
- ✅ Model IDs i configuracions als logs
- ✅ Info sobre KPIs seleccionats
- ✅ Endpoints i buckets R2 que apareixen als logs

### Què NO està protegit (públic):
- ⚠️ Codi font del repositori (públic per design)
- ⚠️ Workflow YAML files (públics)
- ⚠️ README i documentació

### Best Practices:
1. **NO comparteixis el secret**
2. **Renova el secret cada 90-180 dies**
3. **Usa un secret diferent per development/production** (opcional)
4. **Mai hardcodegis el secret al codi**

---

## 🐛 Troubleshooting

### No veig el link al workflow i hauria de veure'l

**Causa**: Secret mal configurat.

**Solució**:
1. Verifica que `ADMIN_SECRET` a Render és exactament igual que `VITE_ADMIN_SECRET` a Vercel
2. Verifica que no hi ha espais abans/després del secret
3. Re-deploya ambdós serveis
4. Esborra caché del navegador i refresca

### Usuaris normals veuen el link

**Causa**: El secret és massa simple o està exposat.

**Solució**:
1. Genera un nou secret més fort
2. Actualitza-lo a Render i Vercel
3. Re-deploya

### Error "X-Admin-Secret header missing"

**Causa**: Frontend no està enviant el header.

**Solució**:
1. Verifica que `VITE_ADMIN_SECRET` està configurat a Vercel
2. Re-deploya el frontend
3. Esborra caché del navegador

---

## 📊 Diagrama de Flux

```
Usuario Normal (sense secret):
  ↓
  Fa POST sense header X-Admin-Secret
  ↓
  Backend: is_admin = False
  ↓
  Response NO inclou workflow_url
  ↓
  Frontend: NO mostra link
  ✅ Usuari veu missatge genèric

Admin (amb secret):
  ↓
  Fa POST amb header X-Admin-Secret: "abc123..."
  ↓
  Backend: is_admin = True
  ↓
  Response SÍ inclou workflow_url
  ↓
  Frontend: SÍ mostra link
  ✅ Admin pot veure GitHub Actions
```

---

## 🔄 Rotació del Secret

### Cada 90 dies (recomanat):

1. **Genera un nou secret** (veure pas 1)
2. **Actualitza a Render**: `ADMIN_SECRET`
3. **Actualitza a Vercel**: `VITE_ADMIN_SECRET`
4. **Re-deploya ambdós**
5. **Testa que funciona**

---

## 📚 Referències

- [Render Environment Variables](https://render.com/docs/environment-variables)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)

---

**Última actualització**: Octubre 6, 2025  
**Versió**: 1.0  
**Status**: ✅ Implementat (pendent deploy)
