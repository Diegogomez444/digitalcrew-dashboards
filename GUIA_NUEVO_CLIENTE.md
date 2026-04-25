# Guía de instalación — Dashboard Digital Crew
### Cómo montar este dashboard para un nuevo cliente

---

## ¿Qué necesitas antes de empezar?

- Cuenta en **GitHub** (gratis)
- Cuenta en **Streamlit Cloud** (gratis) → streamlit.io
- Acceso al repositorio base `Diegogomez444/digitalcrew-dashboards`
- Credenciales de **Telegram** del canal del cliente
- **Google Sheets** con los datos del cliente

---

## PASO 1 — Duplicar el repositorio

1. En GitHub, ve a `Diegogomez444/digitalcrew-dashboards`
2. Clic en **Fork** → dale un nombre como `dashboard-[nombre-cliente]`
3. Clona el fork en tu computador:
   ```bash
   git clone https://github.com/Diegogomez444/dashboard-[nombre-cliente].git
   cd dashboard-[nombre-cliente]
   ```

---

## PASO 2 — Configurar el Google Sheets del cliente

El dashboard lee datos de una hoja de Google Sheets. La hoja debe ser **pública** (o compartida con acceso de lectura a cualquiera con el link).

### Estructura de pestañas requeridas:

| Pestaña | Para qué sirve | GID (en la URL) |
|---|---|---|
| **Hoja principal (Resumen/Config)** | Datos generales del mes, presupuesto | `GID_GENERAL` |
| **Tracking diario (TG)** | Datos día a día de Meta Ads | `GID_TG` |
| **Histórico** | Datos de meses anteriores | `GID_HISTORICO` |

### Cómo obtener el SHEET_ID y los GIDs:

URL de ejemplo:
```
https://docs.google.com/spreadsheets/d/1ABC...XYZ/edit#gid=859239310
                                        ↑ SHEET_ID        ↑ GID de esa pestaña
```

- El **SHEET_ID** es el string largo entre `/d/` y `/edit`
- El **GID** de cada pestaña aparece al final de la URL cuando haces clic en esa pestaña

### Columnas requeridas en la pestaña de Tracking diario (TG):

La primera fila debe ser el encabezado exactamente así:

```
Fecha | Gasto | Resultado | CxResultado FB | CxResultado+ TG | Impresiones | Clics | CxClic | Visitas Pag | CxV. Pagina | CTR | Cargar Web | Conv Web | (vacía) | Ideal Gasto | Gasto Real | Dif Gasto | Meta Telegram | Meta VS Real | (vacías) | TG Tracking | Dolar Hoy
```

- Fechas en formato **DD/MM/AAAA** (ej: `23/04/2026`)
- Valores de dinero en formato colombiano: `$1.234.567` o `$1.234.567,89`
- Porcentajes con símbolo: `2,13%`
- Las filas de totales deben tener en la columna Fecha uno de estos textos: `Total Ads`, `Total General`, `P.Restante`, `Dias restantes`, `P.x dia`

### Columnas requeridas en la pestaña General (Resumen):

Esta pestaña tiene las configuraciones del mes. El dashboard busca estos campos por nombre:

```
inv_pauta     → Inversión en pauta del mes
inv_bot       → Inversión en bot/TG
inv_total     → Inversión total
cxr_obj       → CxR objetivo
leads         → Leads presupuestados
dias_pauta    → Días en pauta
presup_dia    → Presupuesto por día
gasto_actual  → Gasto acumulado actual
p_restante    → Presupuesto restante
```

---

## PASO 3 — Credenciales de Telegram

El dashboard se conecta al canal de Telegram del cliente para leer estadísticas de posts y crecimiento.

### 3.1 Obtener API ID y API HASH

1. Ve a **https://my.telegram.org**
2. Inicia sesión con tu número de teléfono
3. Clic en **API development tools**
4. Crea una nueva aplicación (nombre y plataforma no importan)
5. Copia el **App api_id** y el **App api_hash**

### 3.2 Generar el STRING de sesión (TG_SESSION)

Este string permite que el dashboard se autentique sin pedir código cada vez.

Ejecuta esto en tu terminal (con el entorno del proyecto activo):

```python
python3 -c "
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id   = TU_API_ID      # número entero
api_hash = 'TU_API_HASH'  # string

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print('SESSION STRING:', client.session.save())
"
```

Te pedirá tu número de teléfono y el código que te llega por Telegram. Al final imprime el string de sesión — **guárdalo, es como una contraseña**.

### 3.3 Obtener el username del canal

Es el `@username` del canal de Telegram del cliente (sin el @).
Ejemplo: si el canal es `@lafieraanalista`, el valor es `lafieraanalista`.

---

## PASO 4 — Configurar el archivo de secretos

En Streamlit Cloud, los secretos se configuran en la interfaz web (no se suben al repositorio).

Para desarrollo local, crea el archivo `.streamlit/secrets.toml`:

```toml
SHEET_ID      = "1ABC...XYZ"          # ID del Google Sheets del cliente
GID_GENERAL   = "0"                    # GID pestaña general/resumen
GID_TG        = "123456789"            # GID pestaña tracking diario
GID_HISTORICO = "987654321"            # GID pestaña histórico
CLIENTE       = "Nombre del Cliente"   # Nombre que aparece en el header
TG_API_ID     = "12345678"            # De my.telegram.org
TG_API_HASH   = "abcdef1234..."       # De my.telegram.org
TG_SESSION    = "1BVtsOK8Bu..."       # String generado en paso 3.2
TG_CHANNEL    = "username_del_canal"  # Sin el @
```

> ⚠️ Este archivo **nunca** debe subirse a GitHub. Ya está en `.gitignore`.

---

## PASO 5 — Personalizar el código para el cliente

En `app.py`, los únicos cambios visuales que podrías necesitar son opcionales:

```python
# Línea ~19 — nombre del cliente (se puede dejar en secrets)
CLIENTE = st.secrets.get("CLIENTE", "Nombre Cliente")
```

El nombre del cliente se muestra en el header del dashboard automáticamente.

---

## PASO 6 — Instalar dependencias localmente (para probar)

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## PASO 7 — Subir a GitHub y desplegar en Streamlit Cloud

### 7.1 Subir el código

```bash
git add .
git commit -m "Config cliente [nombre]"
git push origin main
```

### 7.2 Crear la app en Streamlit Cloud

1. Ve a **https://share.streamlit.io**
2. Clic en **New app**
3. Conecta tu GitHub y selecciona el repositorio del cliente
4. Branch: `main` | Main file: `app.py`
5. Clic en **Deploy**

### 7.3 Configurar los secretos en Streamlit Cloud

1. En la app desplegada, clic en **⋮** → **Settings**
2. Sección **Secrets**
3. Pega el contenido de tu `secrets.toml` (sin el nombre del archivo)
4. Clic en **Save** → la app se reinicia automáticamente

---

## PASO 8 — Verificar que todo funciona

Checklist:

- [ ] El header muestra el nombre del cliente correcto
- [ ] La hora en el header está en hora Colombia
- [ ] Tab **Resumen** muestra datos y el filtro de período funciona
- [ ] Tab **Mes Actual** filtra correctamente por fecha
- [ ] Tab **Meta Ads** carga los reportes subidos
- [ ] Tab **Telegram** muestra posts, suscriptores y crecimiento
- [ ] Tab **IA** genera análisis y sugerencias

---

## Estructura de archivos del proyecto

```
dashboard-[cliente]/
├── app.py                    ← código principal (no tocar salvo personalización)
├── requirements.txt          ← dependencias Python
├── .streamlit/
│   ├── config.toml           ← tema oscuro (ya configurado)
│   └── secrets.toml          ← credenciales (NO subir a GitHub)
├── .gitignore                ← ya excluye secrets.toml y CSVs privados
└── GUIA_NUEVO_CLIENTE.md     ← este archivo
```

---

## Solución de problemas frecuentes

| Problema | Causa probable | Solución |
|---|---|---|
| Tab Telegram muestra error | TG_SESSION vencida o incorrecta | Regenerar el string de sesión (Paso 3.2) |
| Filtro "Ayer" muestra 0 | Datos del día no registrados aún en Sheets | Normal si no se ha llenado la fila del día |
| Datos de Meta Ads no cargan | GID incorrecto o hoja no pública | Verificar que el Sheets sea público y los GIDs correctos |
| Dashboard "dormido" al abrir | Streamlit Cloud pausa apps inactivas | Esperar 30-60 seg en la primera visita del día |
| Fecha muestra día incorrecto | Zona horaria del servidor (UTC vs Colombia) | Ya corregido en V1 — no modificar el cálculo de fechas |

---

## Versiones guardadas

| Tag | Descripción | Fecha |
|---|---|---|
| `v1-digital-crew-basica` | Primera versión estable completa | Abril 2026 |

Para volver a una versión anterior:
```bash
git checkout v1-digital-crew-basica
git push origin main --force
```
