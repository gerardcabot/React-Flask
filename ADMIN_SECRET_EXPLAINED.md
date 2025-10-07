# 🔐 Com Funciona el Sistema d'Admin Secret

## 🎯 Què És?

El sistema d'admin permet que **només tu** vegis els links als workflows de GitHub Actions quan crees models, protegint els logs en un repositori públic.

---

## 🔑 Com Funciona

### Sense Secret Configurat (Ara Mateix):
```
Frontend → Backend (sense header X-Admin-Secret)
Backend: is_admin = False
Response: NO inclou workflow_url
Usuari: NO veu link a GitHub Actions ❌
```

### Amb Secret Configurat (Tu com Admin):
```
Frontend → Backend (amb header X-Admin-Secret: "abc123...")
Backend: is_admin = True
Response: SÍ inclou workflow_url
Usuari: SÍ veu link a GitHub Actions ✅
```

---

## 🛠️ Com Ser Admin

### Pas 1: Generar un Secret

```bash
# Al terminal
python -c "import secrets; print(secrets.token_hex(32))"
```

**Exemple de sortida:**
```
a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789
```

Copia aquest valor (el teu secret).

---

### Pas 2: Configurar Backend (Render)

1. **Render Dashboard**: https://dashboard.render.com
2. **Servei**: football-api-r0f2
3. **Environment** (menú lateral)
4. **Add Environment Variable**:
   - Key: `ADMIN_SECRET`
   - Value: `[el secret que has generat]`
5. **Save Changes** (re-deployarà automàticament)

---

### Pas 3: Configurar Frontend (Vercel)

1. **Vercel Dashboard**: https://vercel.com/dashboard
2. **Projecte**: react-flask-psi
3. **Settings** → **Environment Variables**
4. **Add New**:
   - Key: `VITE_ADMIN_SECRET`
   - Value: `[el MATEIX secret que has posat a Render]`
   - Environments: Marca totes (Production, Preview, Development)
5. **Save**
6. **Redeploy**: Deployments → Recent deployment → Redeploy

---

### Pas 4: Verificar

Després de configurar i re-deployar:

1. **Crea un model** a la web
2. **Hauries de veure**:
   ```
   Model training started successfully
   Model ID: xxx_yyy
   Estimated time: 45-90 minutes.
   
   [Monitor Progress on GitHub Actions] ← Link visible! ✅
   ```

---

## 🔐 Seguretat

### Què Protegeix:
- ✅ Logs de GitHub Actions (només tu els veus)
- ✅ Info de KPIs seleccionats
- ✅ Endpoints i buckets R2 als logs

### Qui Pot Ser Admin:
- ✅ **Tu** (amb el secret configurat al navegador)
- ❌ **Usuaris externs** (no tenen el secret)

### Com Ho Sap el Sistema:
El frontend envia el secret com a header HTTP:
```
X-Admin-Secret: a1b2c3d4e5f6789abc...
```

El backend ho compara amb el seu secret i decideix si mostrar el link.

---

## 🧪 Test

### Com a Usuari Normal (sense secret):
1. Obre la web en **mode incògnit**
2. Crea un model
3. **NO** hauríes de veure el link a GitHub Actions ✅

### Com a Admin (tu):
1. Amb el secret configurat
2. Crea un model
3. **SÍ** hauríes de veure el link ✅

---

## ❓ Preguntes Freqüents

### Q: Per què no veig el link ara?
**A:** Perquè encara no has configurat `ADMIN_SECRET` i `VITE_ADMIN_SECRET`.

### Q: És segur?
**A:** Sí, per un projecte personal/portfolio és suficient. El secret viatja per HTTPS (encriptat).

### Q: Puc tenir múltiples admins?
**A:** Sí, comparteix el mateix secret amb altres persones de confiança.

### Q: Què passa si algú descobreix el secret?
**A:** Genera un nou secret i actualitza-lo a Render i Vercel.

---

## 🎯 Resum

| Estat | Acció |
|-------|-------|
| **Ara** | Secret NO configurat → No veus links |
| **Després de configurar** | Tu veus links, altres no |
| **Temps setup** | 5 minuts |
| **Necessari?** | Opcional, però recomanat si vols veure el progrés |

---

**Si no configures el secret**: Tot funciona igualment, simplement no veuràs els links als workflows. Els models s'entrenen i apareixen a la llista normalment.
