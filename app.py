import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import date, timedelta, datetime
import io

# ── CONFIG ─────────────────────────────────────────────────────────────────────
try:
    SHEET_ID      = st.secrets.get("SHEET_ID",      "1KszbEw3CX5jWtWxqE_Oy7Bi17IA5ZJr6FfOkCRJ4zH4")
    GID_GENERAL   = st.secrets.get("GID_GENERAL",   "0")
    GID_TG        = st.secrets.get("GID_TG",        "859239310")
    GID_HISTORICO = st.secrets.get("GID_HISTORICO", "2086565186")
    CLIENTE       = st.secrets.get("CLIENTE",       "La Fiera Analista")
    TG_API_ID     = st.secrets.get("TG_API_ID",     "")
    TG_API_HASH   = st.secrets.get("TG_API_HASH",   "")
    TG_SESSION    = "".join(str(st.secrets.get("TG_SESSION", "")).split())
    TG_CHANNEL    = st.secrets.get("TG_CHANNEL",    "")
except Exception:
    SHEET_ID      = "1KszbEw3CX5jWtWxqE_Oy7Bi17IA5ZJr6FfOkCRJ4zH4"
    GID_GENERAL   = "0"
    GID_TG        = "859239310"
    GID_HISTORICO = "2086565186"
    CLIENTE       = "La Fiera Analista"
    TG_API_ID     = ""
    TG_API_HASH   = ""
    TG_SESSION    = ""
    TG_CHANNEL    = ""


# ── PALETTE ────────────────────────────────────────────────────────────────────
BG      = "#0B0F1A"
CARD    = "#141929"
CARD2   = "#1C2338"
BORDER  = "#252D45"
PURPLE  = "#7C3AED"
PURPLEL = "#A855F7"
PINK    = "#EC4899"
CYAN    = "#06B6D4"
CYANL   = "#22D3EE"
GREEN   = "#10B981"
RED     = "#EF4444"
AMBER   = "#F59E0B"
WHITE   = "#FFFFFF"
MUTED   = "#94A3B8"
MUTED2  = "#374151"

# ── HELPERS ────────────────────────────────────────────────────────────────────
def parse_cop(val):
    if pd.isna(val): return np.nan
    s = str(val).replace("$","").replace("\\-","-").strip()
    if s in ["","nan","#DIV/0!","-","#¡DIV/0!"]: return np.nan
    neg = s.startswith("-")
    s = s.lstrip("-").strip()
    if "," in s:
        p = s.split(",")
        s = p[0].replace(".","") + "." + p[1]
    else:
        s = s.replace(".","")
    try: return (-1 if neg else 1) * float(s)
    except: return np.nan

def parse_num(val):
    if pd.isna(val): return np.nan
    s = str(val).replace(".","").replace(",","").strip()
    if s in ["","nan","#DIV/0!"]: return np.nan
    try: return float(s)
    except: return np.nan

def parse_pct(val):
    if pd.isna(val): return np.nan
    s = str(val).replace("%","").replace(",",".").strip()
    if s in ["","nan","#DIV/0!"]: return np.nan
    try: return float(s)
    except: return np.nan

def fmt_cop(v, dec=0):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    neg = v < 0
    f = f"${abs(v):,.{dec}f}".replace(",","X").replace(".",",").replace("X",".")
    return f"-{f}" if neg else f

def fmt_num(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{int(v):,}".replace(",",".")

def kcard(label, value, style="plain", color="", sub="", delta=""):
    s = f"<div class='kc-sub'>{sub}</div>" if sub else ""
    d = f"<div style='margin-top:.3rem'>{delta}</div>" if delta else ""
    return f"<div class='kc kc-{style}'><div class='kc-lbl'>{label}</div><div class='kc-val {color}'>{value}</div>{s}{d}</div>"

def indicator_card(label, value, display, pct, color, ref_labels):
    bar = f"<div style='background:{MUTED2};border-radius:999px;height:8px;overflow:hidden;margin:.5rem 0'><div style='height:100%;width:{min(pct,100):.0f}%;background:{color};border-radius:999px'></div></div>"
    refs = f"<div style='font-size:.58rem;color:{MUTED};margin-top:.3rem'>{ref_labels}</div>"
    return f"<div class='kc kc-plain'><div class='kc-lbl'>{label}</div><div class='kc-val' style='color:{color};font-size:1.6rem'>{display}</div>{bar}{refs}</div>"

def delta_pct(current, prev):
    if prev and prev != 0:
        return (current - prev) / abs(prev) * 100
    return None

# ── META ADS HELPERS ───────────────────────────────────────────────────────────
META_COL = {
    "spend":       ["importe gastado (cop)","importe gastado","amount spent (cop)","amount spent","gasto"],
    "results":     ["resultados","results"],
    "cpr":         ["costo por resultado","cost per result"],
    "impressions": ["impresiones","impressions"],
    "clicks":      ["clics en el enlace","link clicks","clics (todos)","clics","clicks"],
    "ctr":         ["ctr (tasa de clics en el enlace)","ctr (link click-through rate)","ctr"],
    "reach":       ["alcance","reach"],
    "frequency":   ["frecuencia","frequency"],
    "campaign":    ["nombre de la campaña","campaign name"],
    "adset":       ["nombre del conjunto de anuncios","ad set name"],
    "ad":          ["nombre del anuncio","ad name"],
}
SKIP_VALS = {"","nan","total de la cuenta","totales","total","reporting ends","informe terminado"}

def find_col(df, key):
    aliases = META_COL.get(key, [])
    for col in df.columns:
        if col.strip().lower() in aliases:
            return col
    return None

def parse_meta_num(val):
    if pd.isna(val): return np.nan
    s = str(val).replace("$","").replace(" ","").strip()
    if s in ["","nan","-","N/A"]: return np.nan
    if "," in s and "." in s:
        s = s.replace(".","").replace(",",".")
    elif "," in s:
        s = s.replace(",",".")
    else:
        s = s.replace(".","")
    try: return float(s)
    except: return np.nan

# ── TELEGRAM LOADER ────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def load_telegram_data():
    if not TG_SESSION:
        return {"error": "Sin credenciales de Telegram configuradas."}
    import asyncio
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.functions.channels import GetFullChannelRequest

    async def _fetch():
        async with TelegramClient(StringSession(TG_SESSION), int(TG_API_ID), TG_API_HASH) as client:
            entity = await client.get_entity(TG_CHANNEL)
            full   = await client(GetFullChannelRequest(entity))

            subscribers = full.full_chat.participants_count
            title       = entity.title

            messages = []
            async for msg in client.iter_messages(entity, limit=300):
                if msg.date is None:
                    continue
                messages.append({
                    "id":          msg.id,
                    "fecha":       msg.date.replace(tzinfo=None),
                    "vistas":      msg.views    or 0,
                    "reenvios":    msg.forwards or 0,
                    "reacciones":  len(msg.reactions.results) if msg.reactions else 0,
                    "texto":       (msg.text or "")[:120],
                    "tiene_media": msg.media is not None,
                })

            df_msg = pd.DataFrame(messages)
            if not df_msg.empty:
                df_msg["fecha"]  = pd.to_datetime(df_msg["fecha"])
                df_msg["dia"]    = df_msg["fecha"].dt.date
                df_msg["semana"] = df_msg["fecha"].dt.to_period("W").apply(
                    lambda p: p.start_time.date())

            stats_data   = {}
            df_growth    = pd.DataFrame()
            growth_error = ""
            has_gross_data = False
            try:
                import json as _json
                from telethon.tl.functions.stats import GetBroadcastStatsRequest, LoadAsyncGraphRequest
                from telethon.tl.types import StatsGraph, StatsGraphAsync

                stats = await client(GetBroadcastStatsRequest(channel=entity, dark=False))
                f = stats.followers
                stats_data = {
                    "subs_actual":   f.current,
                    "subs_anterior": f.previous,
                    "vistas_post":   round(stats.views_per_post.current, 1) if stats.views_per_post else None,
                    "shares_post":   round(stats.shares_per_post.current, 1) if stats.shares_per_post else None,
                }

                async def parse_graph(g):
                    if isinstance(g, StatsGraphAsync):
                        g = await client(LoadAsyncGraphRequest(token=g.token))
                    if isinstance(g, StatsGraph):
                        raw  = _json.loads(g.json.data)
                        cols = raw.get("columns", [])
                        dates, series = [], {}
                        for col in cols:
                            if col[0] == "x":
                                dates = [datetime.fromtimestamp(ts/1000) for ts in col[1:]]
                            else:
                                series[col[0]] = [int(v) if v is not None else 0 for v in col[1:]]
                        return dates, series
                    return [], {}

                # growth_graph → total miembros acumulado por día
                gg = getattr(stats, "growth_graph", None)
                gg_dates, gg_series = (await parse_graph(gg)) if gg else ([], {})

                # followers_graph → y0=Se unieron  y1=Salieron (datos brutos diarios)
                fg = getattr(stats, "followers_graph", None)
                fg_dates, fg_series = (await parse_graph(fg)) if fg else ([], {})

                if gg_dates and gg_series:
                    members_vals = list(gg_series.values())[0]
                    df_m = pd.DataFrame({"fecha": gg_dates, "miembros": members_vals})
                    df_m["fecha"] = pd.to_datetime(df_m["fecha"]).dt.normalize()
                    df_m["net"]   = df_m["miembros"].diff().fillna(0).astype(int)

                    if fg_dates and fg_series:
                        series_vals = list(fg_series.values())
                        entradas_vals = series_vals[0] if len(series_vals) > 0 else [0]*len(fg_dates)
                        salidas_vals  = series_vals[1] if len(series_vals) > 1 else [0]*len(fg_dates)
                        df_f = pd.DataFrame({
                            "fecha":    fg_dates,
                            "entradas": entradas_vals,
                            "salidas":  salidas_vals,
                        })
                        df_f["fecha"] = pd.to_datetime(df_f["fecha"]).dt.normalize()
                        df_m = df_m.merge(df_f, on="fecha", how="left")
                        df_m["entradas"] = df_m["entradas"].fillna(0).astype(int)
                        df_m["salidas"]  = df_m["salidas"].fillna(0).astype(int)
                        has_gross_data   = True
                    else:
                        df_m["entradas"] = df_m["net"].clip(lower=0).astype(int)
                        df_m["salidas"]  = df_m["net"].clip(upper=0).abs().astype(int)

                    df_growth = df_m[["fecha","miembros","net","entradas","salidas"]].copy()
            except Exception as _e:
                growth_error = str(_e)
                stats_data   = {}

            return {
                "title":          title,
                "subscribers":    subscribers,
                "df_msg":         df_msg,
                "stats":          stats_data,
                "df_growth":      df_growth,
                "growth_error":   growth_error,
                "has_gross_data": has_gross_data,
            }

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_fetch())
        loop.close()
        return result
    except Exception as e:
        return {"error": str(e)}

# ── DATA LOADERS ───────────────────────────────────────────────────────────────
def fetch_csv(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    return pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

@st.cache_data(ttl=300)
def load_summary():
    raw = fetch_csv(GID_GENERAL)
    s = {}
    for idx, row in raw.iterrows():
        for j, cell in enumerate(row):
            c = str(cell).strip()
            if c == "Inversión Pauta"  and j+1 < len(row): s["inv_pauta"]   = str(row.iloc[j+1])
            if c == "Inversión Bot"    and j+1 < len(row): s["inv_bot"]     = str(row.iloc[j+1])
            if c == "Inversión Total"  and j+1 < len(row):
                s["inv_total"] = str(row.iloc[j+1])
                dias_ok = False
                for k in range(j+2, len(row)):
                    v = str(row.iloc[k]).strip()
                    if not v or v == "nan": continue
                    if "$" not in v and not dias_ok:
                        try:
                            n = float(v.replace(".","").replace(",","."))
                            if 1 <= n <= 365: s["dias_pauta"] = v; dias_ok = True
                        except: pass
                    elif "$" in v and "presup_dia" not in s:
                        s["presup_dia"] = v
            if c in ("CxR Objetivo TG:","CxR Objetivo TG") and j+1 < len(row):
                s["cxr_obj"] = str(row.iloc[j+1])
            if c == "Leads":
                try: s["leads"] = str(raw.iloc[idx+1, j])
                except: pass
            if c == "Gasto Actual" and j+1 < len(row):
                s["gasto_actual"] = str(row.iloc[j+1])
            if c == "P.Restante" and j+1 < len(row) and "p_restante" not in s:
                v = str(row.iloc[j+1]).strip()
                if "$" in v: s["p_restante"] = v
    return s

@st.cache_data(ttl=300)
def load_daily():
    raw = fetch_csv(GID_TG)
    hdr = None
    for i, row in raw.iterrows():
        if str(row.iloc[0]).strip() == "Fecha": hdr = i; break
    if hdr is None: return None
    cols = [str(h).strip() for h in raw.iloc[hdr]]
    df = raw.iloc[hdr+1:].copy()
    df.columns = range(len(df.columns))
    df = df.rename(columns={i: h for i, h in enumerate(cols) if h and h != "nan"})
    skip = {"","nan","Total Ads","Total General","P.Restante","Dias restantes","P.x dia"}
    df = df[df["Fecha"].apply(lambda x: str(x).strip() not in skip)]
    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df = df[df["Fecha"].notna() & (df["Fecha"].dt.date <= date.today())]
    for c in ["Gasto","CxResultado FB","CxResultado+ TG","CxClic","CxV. Pagina",
              "Ideal Gasto","Gasto Real","Dif Gasto","TG Tracking","Dolar Hoy"]:
        if c in df.columns: df[c] = df[c].apply(parse_cop)
    for c in ["Resultado","Impresiones","Clics","Visitas Pag","Meta Telegram","Meta VS Real"]:
        if c in df.columns: df[c] = df[c].apply(parse_num)
    for c in ["CTR","Cargar Web","Conv Web"]:
        if c in df.columns: df[c] = df[c].apply(parse_pct)
    return df.sort_values("Fecha").reset_index(drop=True)

@st.cache_data(ttl=300)
def load_historical():
    try:
        raw = fetch_csv(GID_HISTORICO)
    except Exception:
        return pd.DataFrame()
    hdr = None
    for i, row in raw.iterrows():
        if str(row.iloc[0]).strip() == "Fecha": hdr = i; break
    if hdr is None: return pd.DataFrame()
    cols = [str(h).strip() for h in raw.iloc[hdr]]
    df = raw.iloc[hdr+1:].copy()
    df.columns = range(len(df.columns))
    df = df.rename(columns={i: h for i, h in enumerate(cols) if h and h != "nan"})
    skip = {"","nan","Total Ads","Total General","P.Restante","Dias restantes","P.x dia"}
    df = df[df["Fecha"].apply(lambda x: str(x).strip() not in skip)]
    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df = df[df["Fecha"].notna() & (df["Fecha"].dt.date <= date.today())]
    for c in ["Gasto","CxResultado FB","CxResultado+ TG","CxClic","CxV. Pagina",
              "Ideal Gasto","Gasto Real","Dif Gasto","TG Tracking","Dolar Hoy"]:
        if c in df.columns: df[c] = df[c].apply(parse_cop)
    for c in ["Resultado","Impresiones","Clics","Visitas Pag","Meta Telegram","Meta VS Real"]:
        if c in df.columns: df[c] = df[c].apply(parse_num)
    for c in ["CTR","Cargar Web","Conv Web"]:
        if c in df.columns: df[c] = df[c].apply(parse_pct)
    return df.sort_values("Fecha").reset_index(drop=True)

# ── PAGE SETUP ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Digital Crew · Dashboard", page_icon="⚡", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*,*::before,*::after{{font-family:'Inter',sans-serif!important;box-sizing:border-box;}}
.stApp,[data-testid="stAppViewContainer"]{{background:{BG};}}
[data-testid="stHeader"],[data-testid="stToolbar"]{{background:transparent!important;}}
#MainMenu,footer{{visibility:hidden;}}
section[data-testid="stSidebar"]{{display:none;}}
.block-container{{padding:1.5rem 2.5rem 3rem 2.5rem!important;max-width:100%!important;}}

/* ── Header ── */
.hdr{{display:flex;justify-content:space-between;align-items:center;
  padding:0 0 1.4rem 0;border-bottom:1px solid {BORDER};margin-bottom:1.2rem;}}
.hdr-logo{{font-size:1.6rem;font-weight:900;letter-spacing:.2em;text-transform:uppercase;
  background:linear-gradient(90deg,{PURPLEL},{CYANL});-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;background-clip:text;}}
.hdr-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;
  background:{GREEN};box-shadow:0 0 8px {GREEN};margin-right:.5rem;vertical-align:middle;}}
.hdr-sub{{font-size:.65rem;color:{MUTED};letter-spacing:.22em;text-transform:uppercase;margin-top:4px;}}
.hdr-right{{text-align:right;font-size:.7rem;color:{MUTED};}}
.hdr-right strong{{color:{WHITE};font-weight:600;display:block;font-size:.8rem;}}

/* ── Section label ── */
.slabel{{font-size:.58rem;font-weight:700;letter-spacing:.25em;text-transform:uppercase;
  color:{CYANL};margin:1.6rem 0 .9rem 0;display:flex;align-items:center;gap:.6rem;}}
.slabel::after{{content:'';flex:1;height:1px;
  background:linear-gradient(90deg,{BORDER},transparent);}}

/* ── KPI Cards ── */
.kc{{border-radius:16px;padding:1.1rem 1.2rem;height:100%;
  border:1px solid rgba(255,255,255,.05);position:relative;overflow:hidden;}}
.kc-plain{{background:{CARD};border-color:{BORDER};}}
.kc-pu{{background:linear-gradient(135deg,#2D1B5E 0%,{CARD} 100%);
  border-color:rgba(168,85,247,.35);}}
.kc-cy{{background:linear-gradient(135deg,#0A3040 0%,{CARD} 100%);
  border-color:rgba(34,211,238,.35);}}
.kc-pk{{background:linear-gradient(135deg,#42102E 0%,{CARD} 100%);
  border-color:rgba(236,72,153,.35);}}
.kc-gn{{background:linear-gradient(135deg,#0A2E20 0%,{CARD} 100%);
  border-color:rgba(16,185,129,.35);}}
.kc-lbl{{font-size:.6rem;font-weight:600;color:{MUTED};letter-spacing:.14em;
  text-transform:uppercase;margin-bottom:.4rem;}}
.kc-val{{font-size:1.4rem;font-weight:800;color:{WHITE};line-height:1.1;}}
.kc-val.pu{{color:{PURPLEL};}} .kc-val.cy{{color:{CYANL};}}
.kc-val.pk{{color:{PINK};}}   .kc-val.gn{{color:{GREEN};}}
.kc-sub{{font-size:.65rem;color:{MUTED};margin-top:.3rem;}}
.kc-up{{color:{GREEN};font-size:.68rem;font-weight:700;}}
.kc-dn{{color:{RED};  font-size:.68rem;font-weight:700;}}

/* ── Progress bar ── */
.prog-wrap{{background:{CARD};border:1px solid {BORDER};border-radius:16px;
  padding:1.2rem 1.5rem;}}
.prog-row{{display:flex;justify-content:space-between;margin-bottom:.5rem;}}
.prog-title{{font-size:.62rem;font-weight:700;color:{MUTED};letter-spacing:.18em;text-transform:uppercase;}}
.prog-pct{{font-size:1rem;font-weight:800;
  background:linear-gradient(90deg,{PURPLEL},{CYANL});
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.prog-track{{background:{MUTED2};border-radius:999px;height:10px;overflow:hidden;}}
.prog-fill{{height:100%;border-radius:999px;
  background:linear-gradient(90deg,{PURPLE},{CYANL});}}
.prog-stats{{display:flex;justify-content:space-between;margin-top:.7rem;}}
.ps{{font-size:.7rem;}} .ps span{{color:{MUTED};}} .ps strong{{color:{WHITE};}}

/* ── Buttons ── */
.stButton>button{{
  background:{CARD}!important;border:1px solid {BORDER}!important;
  color:{MUTED}!important;border-radius:9px!important;
  font-size:.73rem!important;font-weight:500!important;
  width:100%;padding:.45rem .5rem!important;
  transition:all .2s!important;letter-spacing:.04em!important;}}
.stButton>button:hover{{
  border-color:{CYANL}!important;color:{CYANL}!important;
  background:rgba(34,211,238,.07)!important;
  box-shadow:0 0 12px rgba(34,211,238,.15)!important;}}

/* ── Date inputs ── */
[data-baseweb="input"] input{{
  background:{CARD2}!important;color:{WHITE}!important;
  border-color:{BORDER}!important;border-radius:9px!important;font-size:.8rem!important;}}
[data-baseweb="input"]{{background:{CARD2}!important;border-radius:9px!important;}}
label[data-testid="stWidgetLabel"] p{{
  color:{MUTED}!important;font-size:.62rem!important;
  font-weight:600;letter-spacing:.14em;text-transform:uppercase;}}

/* ── Main tabs (páginas) ── */
.stTabs [data-baseweb="tab-list"]{{
  background:{CARD};border-radius:12px;padding:5px;gap:4px;border:1px solid {BORDER};
  margin-bottom:1rem;}}
.stTabs [data-baseweb="tab"]{{
  color:{MUTED};background:transparent;border-radius:9px;
  font-size:.82rem;font-weight:500;padding:.45rem 1.4rem;}}
.stTabs [aria-selected="true"]{{
  background:linear-gradient(135deg,{PURPLE},{CYAN})!important;
  color:#fff!important;font-weight:700!important;
  box-shadow:0 2px 14px rgba(124,58,237,.45)!important;}}

/* ── DataFrame ── */
[data-testid="stDataFrame"]{{border:1px solid {BORDER};border-radius:14px;overflow:hidden;}}

/* ── File uploader ── */
[data-testid="stFileUploader"]{{
  background:{CARD};border:2px dashed {BORDER};border-radius:14px;padding:1rem;}}
[data-testid="stFileUploader"]:hover{{border-color:{PURPLEL};}}
</style>
""", unsafe_allow_html=True)

# ── LOAD DATA ──────────────────────────────────────────────────────────────────
summ     = load_summary()
df_all   = load_daily()
df_hist  = load_historical()

# Combinado TG + Histórico para el Resumen (TG tiene prioridad en fechas duplicadas)
df_combined = pd.concat([df_hist, df_all], ignore_index=True)
df_combined["Fecha"] = df_combined["Fecha"].dt.normalize()
df_combined = df_combined.drop_duplicates(subset=["Fecha"], keep="last")
df_combined = df_combined.sort_values("Fecha").reset_index(drop=True)

if df_all is None:
    st.error("No se pudieron cargar los datos. Verifica que el Sheet sea público.")
    st.stop()

# ── HEADER (siempre visible) ───────────────────────────────────────────────────
c_hdr, c_btn = st.columns([8, 1])
with c_hdr:
    st.markdown(f"""
    <div class="hdr">
      <div>
        <div class="hdr-logo">⚡ Digital Crew</div>
        <div class="hdr-sub">Control de Pauta &nbsp;·&nbsp; {CLIENTE}</div>
      </div>
      <div class="hdr-right">
        <span><span class="hdr-dot"></span>En vivo</span>
        <strong>{datetime.now().strftime('%d/%m/%Y  %H:%M')}</strong>
        Última actualización
      </div>
    </div>
    """, unsafe_allow_html=True)
with c_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⟳  Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Cargar datos de Telegram antes de las pestañas (necesario para Resumen)
tg = load_telegram_data()

# ── PESTAÑAS PRINCIPALES ───────────────────────────────────────────────────────
pg0, pg1, pg2, pg3 = st.tabs(["📊  Resumen", "📅  Mes Actual", "📘  Meta Ads", "📲  Telegram"])

components.html("""
<script>
(function() {
    const KEY = 'dc_main_tab';
    const doc = parent.document;

    function getMainTabs() {
        // Only use the FIRST tab-list on the page (main tabs, not sub-tabs)
        const list = doc.querySelector('[data-baseweb="tab-list"]');
        if (!list) return [];
        return Array.from(list.querySelectorAll('[data-baseweb="tab"]'));
    }

    function run() {
        const tabs = getMainTabs();
        if (!tabs.length) return false;

        // Save index when user clicks a main tab
        tabs.forEach((tab, i) => {
            if (!tab._dcBound) {
                tab._dcBound = true;
                tab.addEventListener('click', () => sessionStorage.setItem(KEY, String(i)));
            }
        });

        // Restore saved tab only if it's not already active
        const saved = sessionStorage.getItem(KEY);
        if (saved === null) return true;
        const idx = parseInt(saved);
        if (idx < 0 || idx >= tabs.length) return true;
        const alreadyActive = tabs[idx].getAttribute('aria-selected') === 'true';
        if (!alreadyActive) {
            tabs[idx].click();
        }
        return true;
    }

    // Retry until DOM is ready
    function attempt(n) {
        if (n <= 0) return;
        if (!run()) setTimeout(() => attempt(n - 1), 300);
    }
    setTimeout(() => attempt(5), 200);
})();
</script>
""", height=1)

# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA 0 — RESUMEN
# ══════════════════════════════════════════════════════════════════════════════
with pg0:
    def fmt_date_es_r(d):
        meses = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
        return f"{d.day} {meses[d.month-1]} {d.year}"

    min_d_r = df_combined["Fecha"].dt.date.min()
    ayer_r  = date.today() - timedelta(days=1)
    max_d_r = min(df_combined["Fecha"].dt.date.max(), ayer_r)

    # Usamos el key del radio directamente para que el label se actualice en el mismo rerun
    cur_sel_r = st.session_state.get("res_radio", "Todo el período")

    OPCIONES_R = {
        "Ayer":            (ayer_r, ayer_r),
        "Últimos 7 días":  (max_d_r - timedelta(days=6),  max_d_r),
        "Últimos 14 días": (max_d_r - timedelta(days=13), max_d_r),
        "Últimos 30 días": (max_d_r - timedelta(days=29), max_d_r),
        "Este mes":        (date.today().replace(day=1),  max_d_r),
        "Todo el período": (min_d_r, max_d_r),
        "Personalizado":   (
            st.session_state.get("res_ds", min_d_r),
            st.session_state.get("res_de", max_d_r),
        ),
    }

    if cur_sel_r in OPCIONES_R and cur_sel_r != "Personalizado":
        cur_start_r, cur_end_r = OPCIONES_R[cur_sel_r]
    else:
        cur_start_r = st.session_state.get("res_ds", min_d_r)
        cur_end_r   = st.session_state.get("res_de", max_d_r)
    cur_start_r = max(min_d_r, min(max_d_r, cur_start_r))
    cur_end_r   = max(min_d_r, min(max_d_r, cur_end_r))
    if cur_start_r > cur_end_r: cur_start_r = cur_end_r

    if cur_start_r == cur_end_r:
        btn_lbl_r = f"📅  {fmt_date_es_r(cur_start_r)}  ▾"
        rango_r   = fmt_date_es_r(cur_start_r)
    else:
        btn_lbl_r = f"📅  {fmt_date_es_r(cur_start_r)} – {fmt_date_es_r(cur_end_r)}  ▾"
        rango_r   = f"{fmt_date_es_r(cur_start_r)} – {fmt_date_es_r(cur_end_r)}"

    st.markdown('<div class="slabel">Resumen general</div>', unsafe_allow_html=True)

    lbl_col_r, pop_col_r = st.columns([5, 4])
    with lbl_col_r:
        st.markdown(
            f"<div style='padding-top:.6rem;font-size:.72rem;color:{MUTED};font-weight:500'>"
            f"Período analizado: <strong style='color:{CYANL}'>{rango_r}</strong></div>",
            unsafe_allow_html=True)
    with pop_col_r:
        with st.popover(btn_lbl_r, use_container_width=True):
            opciones_r = list(OPCIONES_R.keys())
            idx_r = opciones_r.index(cur_sel_r) if cur_sel_r in opciones_r else 5
            st.radio("Período", opciones_r, index=idx_r,
                     label_visibility="collapsed", key="res_radio")
            if st.session_state.get("res_radio") == "Personalizado":
                rpc1, rpc2 = st.columns(2)
                with rpc1:
                    st.date_input("Desde", value=st.session_state.get("res_ds", min_d_r),
                                  min_value=min_d_r, max_value=max_d_r, key="res_ds")
                with rpc2:
                    st.date_input("Hasta", value=st.session_state.get("res_de", max_d_r),
                                  min_value=min_d_r, max_value=max_d_r, key="res_de")

    r_sel = st.session_state.get("res_radio", "Todo el período")
    if r_sel != "Personalizado":
        r_start, r_end = OPCIONES_R[r_sel]
    else:
        r_start = st.session_state.get("res_ds", min_d_r)
        r_end   = st.session_state.get("res_de", max_d_r)
    r_start = max(min_d_r, min(max_d_r, r_start))
    r_end   = max(min_d_r, min(max_d_r, r_end))
    if r_start > r_end: r_start = r_end

    dfr  = df_combined[(df_combined["Fecha"].dt.date >= r_start) & (df_combined["Fecha"].dt.date <= r_end)].copy()
    dfrv = dfr[dfr["Gasto"].notna() & (dfr["Gasto"] > 0)].copy()

    # KPIs de inversión
    inv_ads_r   = float(dfrv["Gasto"].sum())       if "Gasto"       in dfrv.columns and not dfrv.empty else 0.0
    inv_bot_r   = float(dfrv["TG Tracking"].sum()) if "TG Tracking" in dfrv.columns and not dfrv.empty else 0.0
    total_inv_r = inv_ads_r + inv_bot_r

    # Entradas y salidas desde Telegram
    entradas_tg_r = 0
    salidas_tg_r  = 0
    if tg and "error" not in tg:
        df_growth_tg = tg.get("df_growth", pd.DataFrame())
        if not df_growth_tg.empty:
            dg_filt = df_growth_tg[
                (df_growth_tg["fecha"].dt.date >= r_start) &
                (df_growth_tg["fecha"].dt.date <= r_end)
            ]
            if "entradas" in df_growth_tg.columns:
                entradas_tg_r = int(dg_filt["entradas"].sum())
            if "salidas" in df_growth_tg.columns:
                salidas_tg_r  = int(dg_filt["salidas"].sum())

    registros_netos_r  = entradas_tg_r - salidas_tg_r
    cxl_ads_r          = inv_ads_r   / entradas_tg_r    if entradas_tg_r    > 0 else None
    cxl_gen_r          = total_inv_r / entradas_tg_r    if entradas_tg_r    > 0 else None
    cxl_ads_neto_r     = inv_ads_r   / registros_netos_r if registros_netos_r > 0 else None
    cxl_gen_neto_r     = total_inv_r / registros_netos_r if registros_netos_r > 0 else None
    tasa_des_r         = (salidas_tg_r / entradas_tg_r * 100) if entradas_tg_r > 0 else None

    conv_web_r = None
    if "Conv Web" in dfrv.columns and dfrv["Conv Web"].notna().any():
        conv_web_r = dfrv["Conv Web"].mean()

    neto_lbl   = f"{'+'if registros_netos_r >= 0 else ''}{fmt_num(registros_netos_r)}"
    neto_style = "gn" if registros_netos_r >= 0 else "pk"

    # ── Sección 1: Inversión ──────────────────────────────────────────────────
    st.markdown('<div class="slabel">Inversión del período</div>', unsafe_allow_html=True)

    rk1, rk2, rk3 = st.columns(3)
    rk1.markdown(kcard("Inversión Ads",    fmt_cop(inv_ads_r),   "pu","pu"), unsafe_allow_html=True)
    rk2.markdown(kcard("Inversión Bot TG", fmt_cop(inv_bot_r),   "plain"),   unsafe_allow_html=True)
    rk3.markdown(kcard("Total Inversión",  fmt_cop(total_inv_r), "cy","cy"), unsafe_allow_html=True)

    # ── Sección 2: Canal Telegram ─────────────────────────────────────────────
    st.markdown('<div class="slabel">Crecimiento del canal</div>', unsafe_allow_html=True)

    rk4, rk5, rk6, rk7 = st.columns(4)
    rk4.markdown(kcard("Entradas",
        f"+{fmt_num(entradas_tg_r)}" if entradas_tg_r else "—", "gn","gn"), unsafe_allow_html=True)
    rk5.markdown(kcard("Salidas",
        f"-{fmt_num(salidas_tg_r)}" if salidas_tg_r else "—", "pk","pk"),   unsafe_allow_html=True)
    rk6.markdown(kcard("Registros Netos", neto_lbl, neto_style, neto_style), unsafe_allow_html=True)
    rk7.markdown(kcard("Tasa de Deserción",
        f"{tasa_des_r:.1f}%" if tasa_des_r is not None else "—", "plain"),  unsafe_allow_html=True)

    # ── Sección 3: Eficiencia ─────────────────────────────────────────────────
    st.markdown('<div class="slabel">Eficiencia</div>', unsafe_allow_html=True)

    rk8, rk9, rk10, rk11, rk12 = st.columns(5)
    rk8.markdown(kcard("CxLead Ads (Sobre entradas)",
        fmt_cop(cxl_ads_r) if cxl_ads_r is not None else "—",         "pk","pk"), unsafe_allow_html=True)
    rk9.markdown(kcard("CxLead General (Sobre entradas)",
        fmt_cop(cxl_gen_r) if cxl_gen_r is not None else "—",         "pk","pk"), unsafe_allow_html=True)
    rk10.markdown(kcard("CxLead Ads (Neto)",
        fmt_cop(cxl_ads_neto_r) if cxl_ads_neto_r is not None else "—","pk","pk"), unsafe_allow_html=True)
    rk11.markdown(kcard("CxLead General (Neto)",
        fmt_cop(cxl_gen_neto_r) if cxl_gen_neto_r is not None else "—","pk","pk"), unsafe_allow_html=True)
    rk12.markdown(kcard("Conv Web",
        f"{conv_web_r:.2f}%" if conv_web_r is not None else "—",       "gn","gn"), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA 1 — REPORTE
# ══════════════════════════════════════════════════════════════════════════════
with pg1:

    # ── FILTRO DE FECHAS ───────────────────────────────────────────────────────
    min_d = df_all["Fecha"].dt.date.min()
    ayer  = date.today() - timedelta(days=1)
    max_d = min(df_all["Fecha"].dt.date.max(), ayer)

    if "ds" not in st.session_state: st.session_state.ds = min_d
    if "de" not in st.session_state: st.session_state.de = max_d
    OPCIONES = {
        "Todo el período":     (min_d, max_d),
        "Ayer":                (ayer, ayer),
        "Últimos 3 días":      (max_d - timedelta(days=2), max_d),
        "Últimos 7 días":      (max_d - timedelta(days=6), max_d),
        "Últimos 15 días":     (max_d - timedelta(days=14), max_d),
        "Este mes":            (date.today().replace(day=1), max_d),
        "Rango personalizado": (st.session_state.ds, st.session_state.de),
    }

    _, fil_col = st.columns([7, 2])
    with fil_col:
        seleccion = st.selectbox("Período", list(OPCIONES.keys()), index=0,
                                 label_visibility="collapsed")

    if seleccion != "Rango personalizado":
        d_start, d_end = OPCIONES[seleccion]
        st.session_state.ds, st.session_state.de = d_start, d_end
    else:
        cr1, cr2 = st.columns(2)
        with cr1:
            d_start = st.date_input("Desde", value=st.session_state.ds,
                                    min_value=min_d, max_value=max_d)
        with cr2:
            d_end = st.date_input("Hasta", value=st.session_state.de,
                                  min_value=min_d, max_value=max_d)
        st.session_state.ds, st.session_state.de = d_start, d_end

    df  = df_all[(df_all["Fecha"].dt.date >= d_start) & (df_all["Fecha"].dt.date <= d_end)].copy()
    dfv = df[df["Gasto"].notna() & (df["Gasto"] > 0)].copy()

    def get_delta(col):
        valid = df_all[df_all[col].notna() & (df_all[col] > 0)] if col == "Gasto" else df_all[df_all[col].notna()]
        if len(valid) < 6: return None
        last3 = valid.tail(3)[col].mean()
        prev3 = valid.iloc[-6:-3][col].mean()
        return delta_pct(last3, prev3)

    def delta_html(val, inverse=False):
        if val is None: return ""
        good  = val < 0 if inverse else val > 0
        arrow = "▲" if val > 0 else "▼"
        cls   = "kc-up" if good else "kc-dn"
        return f'<span class="{cls}">{arrow} {abs(val):.1f}%</span>'

    # ── PRESUPUESTO GENERAL ────────────────────────────────────────────────────
    st.markdown('<div class="slabel">Presupuesto del período</div>', unsafe_allow_html=True)

    inv_pauta = parse_cop(summ.get("inv_pauta","0"))
    inv_bot   = parse_cop(summ.get("inv_bot","0"))
    inv_total = parse_cop(summ.get("inv_total","0"))
    cxr_obj   = parse_cop(summ.get("cxr_obj","0"))
    leads_p   = parse_num(summ.get("leads","0"))
    dias_p    = parse_num(summ.get("dias_pauta","31"))
    pdia      = parse_cop(summ.get("presup_dia","0"))
    gasto_act = parse_cop(summ.get("gasto_actual","0"))
    p_rest    = parse_cop(summ.get("p_restante","0"))

    r1c1,r1c2,r1c3,r1c4,r1c5,r1c6,r1c7 = st.columns(7)
    r1c1.markdown(kcard("Inv. Pauta",    fmt_cop(inv_pauta),  "plain"),      unsafe_allow_html=True)
    r1c2.markdown(kcard("Inv. Bot",      fmt_cop(inv_bot),    "plain"),      unsafe_allow_html=True)
    r1c3.markdown(kcard("Inv. Total",    fmt_cop(inv_total),  "pu","pu"),    unsafe_allow_html=True)
    r1c4.markdown(kcard("CxR Obj. TG",  fmt_cop(cxr_obj),    "cy","cy"),    unsafe_allow_html=True)
    r1c5.markdown(kcard("Leads presup.",fmt_num(leads_p),     "plain"),      unsafe_allow_html=True)
    r1c6.markdown(kcard("Días en pauta",str(int(dias_p)) if dias_p else "—","plain"), unsafe_allow_html=True)
    r1c7.markdown(kcard("Presup./Día",  fmt_cop(pdia),        "plain"),      unsafe_allow_html=True)

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

    pauta_gastado = float(df_all["Gasto"].sum()) if "Gasto" in df_all.columns else 0.0
    pauta_rest    = (inv_pauta - pauta_gastado) if inv_pauta else 0.0
    pct = min((pauta_gastado / inv_pauta * 100) if inv_pauta else 0, 100)
    st.markdown(f"""
<div class="prog-wrap">
  <div class="prog-row">
    <span class="prog-title">Ejecución de presupuesto de pauta</span>
    <span class="prog-pct">{pct:.1f}%</span>
  </div>
  <div class="prog-track"><div class="prog-fill" style="width:{pct}%"></div></div>
  <div class="prog-stats">
    <div class="ps"><span>Gastado</span><br><strong>{fmt_cop(pauta_gastado)}</strong></div>
    <div class="ps" style="text-align:center"><span>Restante</span><br><strong>{fmt_cop(pauta_rest)}</strong></div>
    <div class="ps" style="text-align:right"><span>Total</span><br><strong>{fmt_cop(inv_pauta)}</strong></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── MÉTRICAS DEL PERÍODO ───────────────────────────────────────────────────
    st.markdown('<div class="slabel">Métricas del período seleccionado</div>', unsafe_allow_html=True)

    def safe_sum(col): return dfv[col].sum() if col in dfv.columns else 0
    def safe_mean(col): return dfv[col].mean() if col in dfv.columns and dfv[col].notna().any() else 0

    t_gasto    = safe_sum("Gasto")
    t_result   = safe_sum("Resultado")
    avg_cxrfb  = t_gasto / t_result if t_result > 0 else np.nan
    avg_cxrtg  = (t_gasto + safe_sum("TG Tracking")) / t_result if t_result > 0 else np.nan
    t_impr     = safe_sum("Impresiones")
    t_clics    = safe_sum("Clics")
    avg_ctr    = (t_clics / t_impr * 100) if t_impr > 0 else np.nan
    avg_cxclic = t_gasto / t_clics if t_clics > 0 else np.nan
    t_tg       = safe_sum("TG Tracking")
    t_visitas  = safe_sum("Visitas Pag")
    avg_cargw  = (t_visitas / t_clics * 100) if t_clics > 0 else np.nan
    avg_cw     = (t_result / t_clics * 100) if t_clics > 0 else np.nan

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.markdown(kcard("Gasto total",      fmt_cop(t_gasto),   "pu","pu",
        delta=delta_html(get_delta("Gasto"))), unsafe_allow_html=True)
    m2.markdown(kcard("Resultados",       fmt_num(t_result),  "cy","cy",
        delta=delta_html(get_delta("Resultado"))), unsafe_allow_html=True)
    m3.markdown(kcard("CxResultado FB",   fmt_cop(avg_cxrfb), "plain","",
        delta=delta_html(get_delta("CxResultado FB"), inverse=True)), unsafe_allow_html=True)
    m4.markdown(kcard("CxResultado + TG", fmt_cop(avg_cxrtg), "plain","",
        delta=delta_html(get_delta("CxResultado+ TG"), inverse=True)), unsafe_allow_html=True)
    m5.markdown(kcard("TG Tracking",      fmt_cop(t_tg),      "pk","pk",
        delta=delta_html(get_delta("TG Tracking"))), unsafe_allow_html=True)

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

    m6,m7,m8,m9,m10 = st.columns(5)
    m6.markdown(kcard("Impresiones",   fmt_num(t_impr),    "plain"), unsafe_allow_html=True)
    m7.markdown(kcard("Clics totales", fmt_num(t_clics),   "plain",
        delta=delta_html(get_delta("Clics"))), unsafe_allow_html=True)
    m8.markdown(kcard("CTR promedio",  f"{avg_ctr:.2f}%",  "gn","gn",
        delta=delta_html(get_delta("CTR"))), unsafe_allow_html=True)
    m9.markdown(kcard("CxClic prom.",  fmt_cop(avg_cxclic),"plain"), unsafe_allow_html=True)
    m10.markdown(kcard("Conv. Web",    f"{avg_cw:.2f}%",   "plain","",
        sub=f"Cargar Web: {avg_cargw:.1f}%"), unsafe_allow_html=True)

    # ── INDICADORES ───────────────────────────────────────────────────────────
    st.markdown('<div class="slabel">Indicadores de rendimiento</div>', unsafe_allow_html=True)

    def safe_last(col):
        if col not in dfv.columns or len(dfv[col].dropna()) == 0: return 0
        v = dfv[col].dropna().iloc[-1]
        return float(v) if not np.isnan(float(v)) else 0

    def cxr_color(v):
        if v < 750:  return GREEN
        if v < 1125: return "#84CC16"
        if v < 1500: return AMBER
        if v < 1875: return "#F97316"
        return RED

    def cxr_tier(v):
        if v < 750:  return "V1 Excelente"
        if v < 1125: return "V2 Optimizar"
        if v < 1500: return "V3 Objetivo ✓"
        if v < 1875: return "V4 Alerta"
        return "V5 Apagar"

    last_cxr  = safe_last("CxResultado FB")
    last_ctr  = safe_last("CTR")
    last_cw   = safe_last("Conv Web")
    last_carw = safe_last("Cargar Web")

    g1,g2,g3,g4 = st.columns(4)
    g1.markdown(indicator_card(
        "CxResultado FB · Último día", last_cxr, fmt_cop(last_cxr),
        (last_cxr / 2500) * 100, cxr_color(last_cxr),
        f"{cxr_tier(last_cxr)} &nbsp;·&nbsp; Objetivo: $1.500 &nbsp;·&nbsp; Alerta: $1.875"
    ), unsafe_allow_html=True)
    g2.markdown(indicator_card(
        "CTR · Último día", last_ctr, f"{last_ctr:.2f}%",
        (last_ctr / 5) * 100, GREEN if last_ctr >= 2 else AMBER if last_ctr >= 1 else RED,
        "Bajo &lt;1% &nbsp;·&nbsp; Normal 1–2% &nbsp;·&nbsp; Bueno &gt;2%"
    ), unsafe_allow_html=True)
    g3.markdown(indicator_card(
        "Conv. Web · Último día", last_cw, f"{last_cw:.2f}%",
        (last_cw / 50) * 100, GREEN if last_cw >= 25 else AMBER if last_cw >= 15 else RED,
        "Bajo &lt;15% &nbsp;·&nbsp; Normal 15–25% &nbsp;·&nbsp; Bueno &gt;25%"
    ), unsafe_allow_html=True)
    g4.markdown(indicator_card(
        "Cargar Web · Último día", last_carw, f"{last_carw:.2f}%",
        last_carw, GREEN if last_carw >= 80 else AMBER if last_carw >= 70 else RED,
        "Bajo &lt;70% &nbsp;·&nbsp; Normal 70–80% &nbsp;·&nbsp; Bueno &gt;80%"
    ), unsafe_allow_html=True)

    # ── GRÁFICAS ──────────────────────────────────────────────────────────────
    st.markdown('<div class="slabel">Análisis visual</div>', unsafe_allow_html=True)

    BASE = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(20,25,41,0.6)",
        font=dict(family="Inter", color=MUTED, size=11),
        margin=dict(l=10, r=10, t=70, b=10), height=360,
        hovermode="x unified", hoverlabel=dict(bgcolor=CARD2, font_color=WHITE),
        xaxis=dict(gridcolor=BORDER, showgrid=True, zeroline=False,
                   tickfont=dict(color=MUTED, size=10)),
        yaxis=dict(gridcolor=BORDER, showgrid=True, zeroline=False,
                   tickfont=dict(color=MUTED, size=10)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color=MUTED, size=10), bgcolor="rgba(0,0,0,0)")
    )

    ct1, ct2, ct3, ct4 = st.tabs([
        "📊 Gasto y Resultados", "💰 Costos Lead",
        "🎯 Ejecución de Presupuesto", "📲 Telegram"
    ])

    with ct1:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(
            x=dfv["Fecha"], y=dfv["Gasto"], name="Gasto",
            line=dict(color=PURPLEL, width=2.5),
            fill="tozeroy", fillcolor="rgba(168,85,247,0.15)",
            mode="lines", hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>Gasto</extra>"
        ), secondary_y=False)
        if "Resultado" in dfv.columns:
            fig.add_trace(go.Scatter(
                x=dfv["Fecha"], y=dfv["Resultado"], name="Resultados",
                line=dict(color=CYANL, width=2.5),
                mode="lines+markers", marker=dict(size=5, color=CYANL, line=dict(color=BG, width=1.5)),
                hovertemplate="%{x|%d/%m}<br><b>%{y}</b><extra>Resultados</extra>"
            ), secondary_y=True)
        fig.update_layout(**BASE, title=dict(text="Gasto Diario vs Resultados",
            font=dict(color=WHITE, size=13, weight=700)))
        fig.update_yaxes(title_text="Gasto (COP)", secondary_y=False,
            gridcolor=BORDER, tickfont=dict(color=MUTED, size=10))
        fig.update_yaxes(title_text="Resultados", secondary_y=True,
            gridcolor=BORDER, tickfont=dict(color=MUTED, size=10))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with ct2:
        fig = go.Figure()
        if "CxResultado FB" in dfv.columns:
            fig.add_trace(go.Scatter(
                x=dfv["Fecha"], y=dfv["CxResultado FB"], name="CxResultado FB",
                line=dict(color=PURPLEL, width=2.5),
                fill="tozeroy", fillcolor="rgba(168,85,247,0.1)",
                mode="lines+markers", marker=dict(size=5, color=PURPLEL, line=dict(color=BG, width=1.5)),
                hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>CxR FB</extra>"
            ))
        if "CxResultado+ TG" in dfv.columns:
            fig.add_trace(go.Scatter(
                x=dfv["Fecha"], y=dfv["CxResultado+ TG"], name="CxResultado + TG",
                line=dict(color=CYANL, width=2, dash="dot"),
                mode="lines+markers", marker=dict(size=4, color=CYANL),
                hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>CxR+TG</extra>"
            ))
        tiers = [(750,"V1 Excelente",GREEN),(1125,"V2 Optimizar","#84CC16"),
                 (1500,"V3 Objetivo",AMBER),(1875,"V4 Alerta","#F97316")]
        for val, lbl, col in tiers:
            fig.add_hline(y=val, line_dash="dash", line_color=col, opacity=0.5,
                annotation_text=f"  {lbl}  ${val:,}", annotation_position="right",
                annotation_font=dict(color=col, size=9))
        fig.update_layout(**BASE, title=dict(text="Costo por Resultado · Referencias V1–V4",
            font=dict(color=WHITE, size=13, weight=700)))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with ct3:
        fig = go.Figure()
        df_exec = df_all[df_all["Ideal Gasto"].notna()].copy()
        df_real = df_all[df_all["Gasto Real"].notna() & (df_all["Gasto Real"] > 0)].copy()
        fig.add_trace(go.Scatter(
            x=df_exec["Fecha"], y=df_exec["Ideal Gasto"], name="Ideal acumulado",
            line=dict(color=MUTED2, width=2, dash="dash"),
            hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>Ideal</extra>"
        ))
        fig.add_trace(go.Scatter(
            x=df_real["Fecha"], y=df_real["Gasto Real"], name="Gasto real",
            line=dict(color=PURPLEL, width=3),
            fill="tonexty", fillcolor="rgba(168,85,247,0.08)",
            mode="lines", hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>Real</extra>"
        ))
        if "Dif Gasto" in df_real.columns:
            cols_bar = [GREEN if v >= 0 else RED for v in df_real["Dif Gasto"].dropna()]
            fig.add_trace(go.Bar(
                x=df_real["Fecha"], y=df_real["Dif Gasto"], name="Diferencia",
                marker=dict(color=cols_bar, opacity=0.6), yaxis="y2",
                hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>Dif.</extra>"
            ))
        layout2 = {**BASE}
        layout2["yaxis2"] = dict(overlaying="y", side="right", gridcolor=BORDER,
            tickfont=dict(color=MUTED, size=10), zeroline=True,
            zerolinecolor=MUTED2, title="Diferencia ($)")
        fig.update_layout(**layout2, title=dict(text="Ejecución Acumulada vs Ideal · Diferencia diaria",
            font=dict(color=WHITE, size=13, weight=700)))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with ct4:
        fig = make_subplots(rows=1, cols=2,
            subplot_titles=("TG Tracking diario ($)", "Meta Telegram acumulada vs Real"),
            column_widths=[0.45, 0.55])
        if "TG Tracking" in dfv.columns:
            tg_vals   = dfv["TG Tracking"].fillna(0)
            tg_colors = [CYANL if v > 0 else MUTED2 for v in tg_vals]
            fig.add_trace(go.Bar(
                x=dfv["Fecha"], y=tg_vals, name="TG Tracking",
                marker=dict(color=tg_colors, opacity=0.85, line=dict(color="rgba(0,0,0,0)", width=0)),
                hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>TG Tracking</extra>"
            ), row=1, col=1)
        df_tg = df_all[df_all["Meta Telegram"].notna()].copy()
        if len(df_tg) > 0:
            fig.add_trace(go.Scatter(
                x=df_tg["Fecha"], y=df_tg["Meta Telegram"], name="Meta",
                line=dict(color=MUTED2, width=2, dash="dash"),
                hovertemplate="%{x|%d/%m}<br><b>%{y:,.0f}</b><extra>Meta</extra>"
            ), row=1, col=2)
        df_real_tg = df_all[df_all["Resultado"].notna() & (df_all["Resultado"] > 0)].copy()
        if len(df_real_tg) > 0:
            df_real_tg = df_real_tg.sort_values("Fecha")
            df_real_tg["Real acumulado"] = df_real_tg["Resultado"].cumsum()
            fig.add_trace(go.Scatter(
                x=df_real_tg["Fecha"], y=df_real_tg["Real acumulado"], name="Real",
                line=dict(color=CYANL, width=2.5), mode="lines+markers",
                marker=dict(size=5, color=CYANL, line=dict(color=BG, width=1)),
                hovertemplate="%{x|%d/%m}<br><b>%{y:,.0f}</b><extra>Real</extra>"
            ), row=1, col=2)
        fig.update_layout(**BASE, title=dict(text="Gasto Bot",
            font=dict(color=WHITE, size=13, weight=700)))
        fig.update_xaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
        fig.update_yaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
        for ann in fig.layout.annotations: ann.font.color = MUTED; ann.font.size = 11
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── TABLA DIARIA ──────────────────────────────────────────────────────────
    st.markdown('<div class="slabel">Detalle diario</div>', unsafe_allow_html=True)

    show_cols = ["Fecha","Gasto","Resultado","CxResultado FB","CxResultado+ TG",
                 "Impresiones","Clics","CxClic","CTR","Cargar Web","Conv Web","TG Tracking"]
    show_cols = [c for c in show_cols if c in dfv.columns]
    tbl = dfv[show_cols].copy()
    tbl["Fecha"] = tbl["Fecha"].dt.strftime("%d/%m/%Y")
    tbl = tbl.set_index("Fecha")
    fmt = {}
    for c in tbl.columns:
        if c in ["Gasto","CxResultado FB","CxResultado+ TG","CxClic","TG Tracking"]: fmt[c] = "${:,.0f}"
        elif c in ["CTR","Cargar Web","Conv Web"]: fmt[c] = "{:.2f}%"
        elif c in ["Resultado","Impresiones","Clics"]: fmt[c] = "{:,.0f}"
    st.dataframe(tbl.style.format(fmt, na_rep="—"), use_container_width=True, height=380)

# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA 2 — META ADS
# ══════════════════════════════════════════════════════════════════════════════
with pg2:

    if "meta_reports" not in st.session_state:
        st.session_state.meta_reports = []

    st.markdown('<div class="slabel">Subir reporte de Meta Ads Manager</div>', unsafe_allow_html=True)

    up_col, cnt_col = st.columns([5, 1])
    with up_col:
        uploaded_file = st.file_uploader(
            "Sube un reporte CSV exportado desde Meta Ads Manager",
            type=["csv"],
            help="Administrador de Anuncios → Exportar → CSV",
            label_visibility="collapsed"
        )
    with cnt_col:
        n_rep = len(st.session_state.meta_reports)
        if n_rep:
            st.markdown(kcard("Reportes", str(n_rep), "cy","cy"), unsafe_allow_html=True)

    if uploaded_file:
        try:
            raw_bytes = uploaded_file.read()
            try:
                df_up = pd.read_csv(io.BytesIO(raw_bytes), thousands=".", decimal=",",
                                    dtype=str, keep_default_na=False)
            except Exception:
                df_up = pd.read_csv(io.BytesIO(raw_bytes), dtype=str, keep_default_na=False)

            df_up.columns = [str(c).strip() for c in df_up.columns]

            col_spend   = find_col(df_up, "spend")
            col_results = find_col(df_up, "results")
            col_cpr     = find_col(df_up, "cpr")
            col_impr    = find_col(df_up, "impressions")
            col_clicks  = find_col(df_up, "clicks")
            col_ctr     = find_col(df_up, "ctr")
            col_reach   = find_col(df_up, "reach")
            col_camp    = find_col(df_up, "campaign")
            col_adset   = find_col(df_up, "adset")
            col_ad      = find_col(df_up, "ad")

            for c in [col_spend,col_results,col_cpr,col_impr,col_clicks,col_ctr,col_reach]:
                if c: df_up[c] = df_up[c].apply(parse_meta_num)

            name_col = col_ad or col_adset or col_camp
            if name_col:
                df_up = df_up[df_up[name_col].apply(
                    lambda x: str(x).strip().lower() not in SKIP_VALS)]

            if col_ad:      rtype = "Anuncios"
            elif col_adset: rtype = "Públicos"
            elif col_camp:  rtype = "Campañas"
            else:           rtype = "General"

            entry = {"name": uploaded_file.name, "type": rtype, "df": df_up,
                     "cols": dict(spend=col_spend, results=col_results, cpr=col_cpr,
                                  impressions=col_impr, clicks=col_clicks, ctr=col_ctr,
                                  reach=col_reach, campaign=col_camp, adset=col_adset, ad=col_ad)}
            if not any(r["name"] == uploaded_file.name for r in st.session_state.meta_reports):
                st.session_state.meta_reports.append(entry)

            st.markdown(
                f"<div style='font-size:.72rem;color:{GREEN};font-weight:600;margin:.4rem 0'>"
                f"✓ {uploaded_file.name} &nbsp;·&nbsp; Tipo: {rtype} &nbsp;·&nbsp; {len(df_up)} filas</div>",
                unsafe_allow_html=True)

            # KPIs
            t_spend   = df_up[col_spend].sum()   if col_spend   else np.nan
            t_results = df_up[col_results].sum() if col_results else np.nan
            avg_cpr_m = df_up[col_cpr].mean()    if col_cpr     else (t_spend/t_results if t_results else np.nan)
            t_impr_m  = df_up[col_impr].sum()    if col_impr    else np.nan
            avg_ctr_m = df_up[col_ctr].mean()    if col_ctr     else np.nan

            mk1,mk2,mk3,mk4,mk5 = st.columns(5)
            mk1.markdown(kcard("Gasto Total",  fmt_cop(t_spend),   "pu","pu"), unsafe_allow_html=True)
            mk2.markdown(kcard("Resultados",   fmt_num(t_results), "cy","cy"), unsafe_allow_html=True)
            mk3.markdown(kcard("CxResultado",  fmt_cop(avg_cpr_m), "plain"),   unsafe_allow_html=True)
            mk4.markdown(kcard("Impresiones",  fmt_num(t_impr_m),  "plain"),   unsafe_allow_html=True)
            mk5.markdown(kcard("CTR prom.",
                f"{avg_ctr_m:.2f}%" if avg_ctr_m and not np.isnan(avg_ctr_m) else "—",
                "gn","gn"), unsafe_allow_html=True)

            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

            # Gráficas de ranking
            if rtype in ["Públicos","Anuncios"] and name_col:
                lbl_name = "Público" if rtype == "Públicos" else "Anuncio"
                BASE_M = dict(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(20,25,41,0.6)",
                    font=dict(family="Inter", color=MUTED, size=11),
                    margin=dict(l=10, r=10, t=70, b=10), height=380,
                    hoverlabel=dict(bgcolor=CARD2, font_color=WHITE),
                    legend=dict(font=dict(color=MUTED, size=10), bgcolor="rgba(0,0,0,0)")
                )
                gc1, gc2 = st.columns(2)

                with gc1:
                    if col_results:
                        df_top = df_up[[name_col, col_results]].copy()
                        df_top = df_top[df_top[col_results].notna() & (df_top[col_results] > 0)]
                        df_top = df_top.sort_values(col_results, ascending=True).tail(10)
                        df_top[name_col] = df_top[name_col].apply(
                            lambda x: str(x)[:38]+"…" if len(str(x))>38 else str(x))
                        fig_r = go.Figure(go.Bar(
                            x=df_top[col_results], y=df_top[name_col], orientation="h",
                            marker=dict(color=df_top[col_results].values,
                                colorscale=[[0,PURPLE],[1,CYANL]], opacity=0.9),
                            hovertemplate="<b>%{y}</b><br>Resultados: %{x}<extra></extra>"
                        ))
                        fig_r.update_layout(**BASE_M,
                            title=dict(text=f"Top {lbl_name}s · Resultados",
                                font=dict(color=WHITE,size=13,weight=700)),
                            xaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9)),
                            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=WHITE,size=9)))
                        st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar":False})

                with gc2:
                    if col_cpr:
                        df_cpr_t = df_up[[name_col, col_cpr]].copy()
                        df_cpr_t = df_cpr_t[df_cpr_t[col_cpr].notna() & (df_cpr_t[col_cpr] > 0)]
                        df_cpr_t = df_cpr_t.sort_values(col_cpr, ascending=True).head(10)
                        df_cpr_t[name_col] = df_cpr_t[name_col].apply(
                            lambda x: str(x)[:38]+"…" if len(str(x))>38 else str(x))
                        fig_c = go.Figure(go.Bar(
                            x=df_cpr_t[col_cpr], y=df_cpr_t[name_col], orientation="h",
                            marker=dict(color=PINK, opacity=0.85),
                            hovertemplate="<b>%{y}</b><br>CxResultado: $%{x:,.0f}<extra></extra>"
                        ))
                        fig_c.update_layout(**BASE_M,
                            title=dict(text=f"Menor Costo por Resultado · {lbl_name}",
                                font=dict(color=WHITE,size=13,weight=700)),
                            xaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9)),
                            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=WHITE,size=9)))
                        st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar":False})

            # Tabla completa
            with st.expander("Ver tabla completa del reporte"):
                show = [c for c in [col_camp,col_adset,col_ad,col_spend,col_results,
                                    col_cpr,col_impr,col_clicks,col_ctr,col_reach] if c]
                if show:
                    fmt_tbl = {}
                    if col_spend:   fmt_tbl[col_spend]   = "${:,.0f}"
                    if col_cpr:     fmt_tbl[col_cpr]     = "${:,.0f}"
                    if col_ctr:     fmt_tbl[col_ctr]     = "{:.2f}%"
                    if col_results: fmt_tbl[col_results] = "{:,.0f}"
                    if col_impr:    fmt_tbl[col_impr]    = "{:,.0f}"
                    if col_clicks:  fmt_tbl[col_clicks]  = "{:,.0f}"
                    if col_reach:   fmt_tbl[col_reach]   = "{:,.0f}"
                    st.dataframe(df_up[show].style.format(fmt_tbl, na_rep="—"),
                                 use_container_width=True)

        except Exception as e:
            st.error(f"Error leyendo el archivo: {e}")

    else:
        st.markdown(f"""
<div style="background:{CARD};border:2px dashed {BORDER};border-radius:16px;
  padding:2.5rem;text-align:center;margin-top:.5rem">
  <div style="font-size:2.5rem;margin-bottom:.8rem">📊</div>
  <div style="color:{WHITE};font-weight:700;font-size:1rem;margin-bottom:.7rem">
    Sube un reporte de Meta Ads Manager</div>
  <div style="color:{MUTED};font-size:.8rem;line-height:2">
    1 · Abre el <strong style="color:{CYANL}">Administrador de Anuncios</strong> de Meta<br>
    2 · Ajusta el período y el nivel:
      <strong style="color:{CYANL}">Campañas / Conjuntos de anuncios / Anuncios</strong><br>
    3 · Haz clic en <strong style="color:{CYANL}">Exportar → CSV</strong><br>
    4 · Sube el archivo aquí — el dashboard detecta el tipo automáticamente
  </div>
</div>
""", unsafe_allow_html=True)

    # Historial
    if len(st.session_state.meta_reports) > 0:
        st.markdown('<div class="slabel">Historial de reportes</div>', unsafe_allow_html=True)
        for rep in st.session_state.meta_reports:
            hc1,hc2,hc3,hc4 = st.columns([4,1,1,1])
            sc = rep["cols"]["spend"]; rc = rep["cols"]["results"]
            df_r = rep["df"]
            hc1.markdown(f"<span style='color:{WHITE};font-size:.82rem'>{rep['name']}</span>",
                         unsafe_allow_html=True)
            hc2.markdown(f"<span style='color:{MUTED};font-size:.75rem'>{rep['type']}</span>",
                         unsafe_allow_html=True)
            hc3.markdown(f"<span style='color:{PURPLEL};font-size:.82rem;font-weight:700'>"
                         f"{fmt_cop(df_r[sc].sum()) if sc else '—'}</span>", unsafe_allow_html=True)
            hc4.markdown(f"<span style='color:{CYANL};font-size:.82rem;font-weight:700'>"
                         f"{fmt_num(df_r[rc].sum()) if rc else '—'} leads</span>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA 3 — TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
with pg3:
    if "error" in tg:
        st.error(f"Error conectando a Telegram: {tg['error']}")
    else:
        df_msg  = tg["df_msg"]
        stats   = tg["stats"]
        subs    = tg["subscribers"]

        BASE_TG = dict(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(20,25,41,0.6)",
            font=dict(family="Inter", color=MUTED, size=11),
            margin=dict(l=10, r=10, t=70, b=10), height=340,
            hovermode="x unified", hoverlabel=dict(bgcolor=CARD2, font_color=WHITE),
            xaxis=dict(gridcolor=BORDER, showgrid=True, zeroline=False,
                       tickfont=dict(color=MUTED, size=10)),
            yaxis=dict(gridcolor=BORDER, showgrid=True, zeroline=False,
                       tickfont=dict(color=MUTED, size=10)),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        font=dict(color=MUTED, size=10), bgcolor="rgba(0,0,0,0)")
        )

        # ── KPIs ──────────────────────────────────────────────────────────────
        st.markdown('<div class="slabel">Resumen del canal</div>', unsafe_allow_html=True)

        total_posts = len(df_msg) if not df_msg.empty else 0
        avg_vistas  = int(df_msg["vistas"].mean()) if not df_msg.empty else 0
        max_vistas  = int(df_msg["vistas"].max())  if not df_msg.empty else 0

        # Crecimiento desde stats si disponible
        sub_prev = stats.get("subs_anterior")
        sub_curr = stats.get("subs_actual", subs)
        if sub_prev and sub_curr:
            crecim = sub_curr - sub_prev
            crecim_txt = f"{'+'if crecim>=0 else ''}{crecim:,} vs período anterior"
        else:
            crecim_txt = ""

        tk1, tk2, tk3, tk4 = st.columns(4)
        tk1.markdown(kcard("Suscriptores", fmt_num(subs), "pu","pu",
            sub=crecim_txt), unsafe_allow_html=True)
        tk2.markdown(kcard("Posts analizados", fmt_num(total_posts), "plain"),
            unsafe_allow_html=True)
        tk3.markdown(kcard("Vistas promedio", fmt_num(avg_vistas), "cy","cy"),
            unsafe_allow_html=True)
        tk4.markdown(kcard("Mejor post", fmt_num(max_vistas)+" vistas", "gn","gn"),
            unsafe_allow_html=True)

        if not df_msg.empty:
            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

            # ── GRÁFICAS ──────────────────────────────────────────────────────
            df_growth = tg.get("df_growth", pd.DataFrame())

            tg_t1, tg_t2, tg_t3, tg_t4 = st.tabs([
                "📈 Vistas por post", "🏆 Top posts", "📅 Actividad semanal", "👥 Crecimiento"
            ])

            with tg_t1:
                df_plot = df_msg.sort_values("fecha").head(100)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_plot["fecha"],
                    y=df_plot["vistas"],
                    name="Vistas",
                    marker=dict(
                        color=df_plot["vistas"].values,
                        colorscale=[[0, PURPLE],[0.5, PURPLEL],[1, CYANL]],
                        opacity=0.9
                    ),
                    hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Vistas: %{y:,.0f}<extra></extra>"
                ))
                fig.add_trace(go.Scatter(
                    x=df_plot["fecha"],
                    y=df_plot["vistas"].rolling(7, min_periods=1).mean(),
                    name="Media 7 posts",
                    line=dict(color=CYANL, width=2, dash="dot"),
                    hovertemplate="%{y:.0f} (media)<extra></extra>"
                ))
                fig.update_layout(**BASE_TG, title=dict(
                    text="Vistas por publicación · últimos 100 posts",
                    font=dict(color=WHITE, size=13, weight=700)))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with tg_t2:
                df_top10 = df_msg.nlargest(10, "vistas").copy()
                df_top10["label"] = df_top10.apply(
                    lambda r: (r["texto"][:50]+"…" if len(r["texto"])>50 else r["texto"])
                              or f"Post {r['id']}", axis=1)

                fig2 = go.Figure(go.Bar(
                    x=df_top10["vistas"],
                    y=df_top10["label"],
                    orientation="h",
                    marker=dict(color=df_top10["vistas"].values,
                        colorscale=[[0,PURPLE],[1,CYANL]], opacity=0.9),
                    hovertemplate="<b>%{y}</b><br>Vistas: %{x:,.0f}<extra></extra>"
                ))
                fig2.update_layout(**{k:v for k,v in BASE_TG.items()
                                      if k not in ("xaxis","yaxis","height")},
                    height=400,
                    title=dict(text="Top 10 publicaciones por vistas",
                        font=dict(color=WHITE, size=13, weight=700)))
                fig2.update_xaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
                fig2.update_yaxes(gridcolor="rgba(0,0,0,0)",
                                  tickfont=dict(color=WHITE, size=9), autorange="reversed")
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

                # Tabla top posts
                st.markdown('<div class="slabel">Detalle top posts</div>', unsafe_allow_html=True)
                tbl_top = df_top10[["fecha","vistas","reacciones","texto"]].copy()
                tbl_top["fecha"] = tbl_top["fecha"].dt.strftime("%d/%m/%Y")
                tbl_top.columns = ["Fecha","Vistas","Reacciones","Texto"]
                st.dataframe(tbl_top.set_index("Fecha"), use_container_width=True)

            with tg_t3:
                if "semana" in df_msg.columns:
                    df_sem = df_msg.groupby("semana").agg(
                        posts=("id","count"),
                        vistas=("vistas","sum"),
                        avg_vistas=("vistas","mean"),
                    ).reset_index()
                    df_sem["semana"] = pd.to_datetime(df_sem["semana"])

                    fig3 = make_subplots(specs=[[{"secondary_y": True}]])
                    fig3.add_trace(go.Bar(
                        x=df_sem["semana"], y=df_sem["vistas"], name="Vistas totales",
                        marker=dict(color=PURPLEL, opacity=0.8),
                        hovertemplate="%{x|%d/%m}<br><b>%{y:,.0f} vistas</b><extra></extra>"
                    ), secondary_y=False)
                    fig3.add_trace(go.Scatter(
                        x=df_sem["semana"], y=df_sem["posts"], name="Posts",
                        line=dict(color=CYANL, width=2.5),
                        mode="lines+markers", marker=dict(size=6, color=CYANL),
                        hovertemplate="%{x|%d/%m}<br><b>%{y} posts</b><extra></extra>"
                    ), secondary_y=True)
                    fig3.update_layout(**{k:v for k,v in BASE_TG.items()
                                          if k not in ("xaxis","yaxis")},
                        title=dict(text="Actividad semanal · Vistas y publicaciones",
                            font=dict(color=WHITE, size=13, weight=700)))
                    fig3.update_xaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
                    fig3.update_yaxes(title_text="Vistas", secondary_y=False,
                        gridcolor=BORDER, tickfont=dict(color=MUTED, size=10))
                    fig3.update_yaxes(title_text="Posts", secondary_y=True,
                        gridcolor=BORDER, tickfont=dict(color=MUTED, size=10))
                    st.plotly_chart(fig3, use_container_width=True,
                        config={"displayModeBar": False})

            with tg_t4:
                growth_error   = tg.get("growth_error", "")
                has_gross_data = tg.get("has_gross_data", False)
                if df_growth.empty:
                    if growth_error:
                        st.error(f"Error al obtener estadísticas: {growth_error}")
                    else:
                        st.markdown(f"""
<div style="background:{CARD};border:2px dashed {BORDER};border-radius:14px;
  padding:2rem;text-align:center;margin-top:.5rem">
  <div style="font-size:1.8rem;margin-bottom:.6rem">📊</div>
  <div style="color:{WHITE};font-weight:700;font-size:.9rem;margin-bottom:.4rem">
    Datos de crecimiento no disponibles</div>
  <div style="color:{MUTED};font-size:.78rem;line-height:1.7">
    Para ver entradas y salidas por día, el canal necesita tener<br>
    habilitadas las <strong style="color:{CYANL}">estadísticas de canal</strong>
    en Telegram (requiere +500 suscriptores<br>y permiso de admin "Ver estadísticas").
  </div>
</div>""", unsafe_allow_html=True)
                else:
                    # Filtro de fechas
                    gmin = df_growth["fecha"].dt.date.min()
                    gmax = df_growth["fecha"].dt.date.max()

                    # Session state para el filtro de crecimiento
                    if "tg_g_sel" not in st.session_state:
                        st.session_state.tg_g_sel   = "Últimos 30 días"
                    if "tg_g_start" not in st.session_state:
                        st.session_state.tg_g_start = max(gmin, gmax - timedelta(days=29))
                    if "tg_g_end" not in st.session_state:
                        st.session_state.tg_g_end   = gmax

                    OPCIONES_G = {
                        "Ayer":            (gmax, gmax),
                        "Últimos 7 días":  (gmax - timedelta(days=6),  gmax),
                        "Últimos 14 días": (gmax - timedelta(days=13), gmax),
                        "Últimos 28 días": (gmax - timedelta(days=27), gmax),
                        "Últimos 30 días": (gmax - timedelta(days=29), gmax),
                        "Últimos 60 días": (gmax - timedelta(days=59), gmax),
                        "Últimos 90 días": (gmax - timedelta(days=89), gmax),
                        "Este mes":        (date.today().replace(day=1), gmax),
                        "Todo el período": (gmin, gmax),
                        "Personalizado":   (st.session_state.tg_g_start, st.session_state.tg_g_end),
                    }

                    cur_sel = st.session_state.tg_g_sel
                    if cur_sel in OPCIONES_G and cur_sel != "Personalizado":
                        cur_start, cur_end = OPCIONES_G[cur_sel]
                    else:
                        cur_start = st.session_state.tg_g_start
                        cur_end   = st.session_state.tg_g_end
                    cur_start = max(gmin, min(gmax, cur_start))
                    cur_end   = max(gmin, min(gmax, cur_end))
                    if cur_start > cur_end:
                        cur_start = cur_end

                    def fmt_date_es(d):
                        meses = ["ene","feb","mar","abr","may","jun",
                                 "jul","ago","sep","oct","nov","dic"]
                        return f"{d.day} {meses[d.month-1]} {d.year}"

                    if cur_start == cur_end:
                        btn_lbl    = f"📅  {fmt_date_es(cur_start)}  ▾"
                        rango_txt  = fmt_date_es(cur_start)
                    else:
                        btn_lbl    = f"📅  {fmt_date_es(cur_start)} – {fmt_date_es(cur_end)}  ▾"
                        rango_txt  = f"{fmt_date_es(cur_start)} – {fmt_date_es(cur_end)}"

                    lbl_col, pop_col = st.columns([5, 4])
                    with lbl_col:
                        st.markdown(
                            f"<div style='padding-top:.6rem;font-size:.72rem;color:{MUTED};font-weight:500'>"
                            f"Período analizado: <strong style='color:{CYANL}'>{rango_txt}</strong></div>",
                            unsafe_allow_html=True
                        )
                    with pop_col:
                        with st.popover(btn_lbl, use_container_width=True):
                            opciones_lista = list(OPCIONES_G.keys())
                            idx_def = opciones_lista.index(cur_sel) if cur_sel in opciones_lista else 5
                            new_sel = st.radio("Período", opciones_lista, index=idx_def,
                                               label_visibility="collapsed", key="tg_g_radio")
                            st.session_state.tg_g_sel = new_sel
                            if new_sel == "Personalizado":
                                pc1, pc2 = st.columns(2)
                                with pc1:
                                    ns = st.date_input("Desde",
                                        value=st.session_state.tg_g_start,
                                        min_value=gmin, max_value=gmax, key="tg_g_ds")
                                    st.session_state.tg_g_start = ns
                                with pc2:
                                    ne = st.date_input("Hasta",
                                        value=st.session_state.tg_g_end,
                                        min_value=gmin, max_value=gmax, key="tg_g_de")
                                    st.session_state.tg_g_end = ne

                    if st.session_state.tg_g_sel != "Personalizado":
                        g_start, g_end = OPCIONES_G[st.session_state.tg_g_sel]
                    else:
                        g_start = st.session_state.tg_g_start
                        g_end   = st.session_state.tg_g_end

                    # Clampear al rango disponible en ambos extremos
                    g_start = max(gmin, min(gmax, g_start))
                    g_end   = max(gmin, min(gmax, g_end))
                    if g_start > g_end:
                        g_start = g_end

                    dg = df_growth[(df_growth["fecha"].dt.date >= g_start) &
                                   (df_growth["fecha"].dt.date <= g_end)].copy()

                    # KPIs del período
                    neto     = int(dg["net"].sum()) if "net" in dg.columns else int((dg["entradas"] - dg["salidas"]).sum())
                    sub_fin  = int(dg["miembros"].iloc[-1]) if not dg.empty else subs
                    sub_ini  = int(dg["miembros"].iloc[0])  if not dg.empty else subs

                    if has_gross_data:
                        total_ent = int(dg["entradas"].sum())
                        total_sal = int(dg["salidas"].sum())
                        gk1, gk2, gk3, gk4 = st.columns(4)
                        gk1.markdown(kcard("Suscriptores al cierre", fmt_num(sub_fin), "pu","pu"), unsafe_allow_html=True)
                        gk2.markdown(kcard("Entradas período", f"+{fmt_num(total_ent)}", "gn","gn"), unsafe_allow_html=True)
                        gk3.markdown(kcard("Salidas período", f"-{fmt_num(total_sal)}", "pk","pk"), unsafe_allow_html=True)
                        gk4.markdown(kcard("Crecimiento neto",
                            f"{'+'if neto>=0 else ''}{fmt_num(neto)}",
                            "cy" if neto >= 0 else "pk",
                            "cy" if neto >= 0 else "pk"), unsafe_allow_html=True)
                    else:
                        dias_pos = int((dg["net"] > 0).sum()) if "net" in dg.columns else 0
                        dias_neg = int((dg["net"] < 0).sum()) if "net" in dg.columns else 0
                        gk1, gk2, gk3, gk4 = st.columns(4)
                        gk1.markdown(kcard("Suscriptores al cierre", fmt_num(sub_fin), "pu","pu"), unsafe_allow_html=True)
                        gk2.markdown(kcard("Crecimiento neto período",
                            f"{'+'if neto>=0 else ''}{fmt_num(neto)}",
                            "gn" if neto >= 0 else "pk",
                            "gn" if neto >= 0 else "pk"), unsafe_allow_html=True)
                        gk3.markdown(kcard("Días con crecimiento", fmt_num(dias_pos), "cy","cy"), unsafe_allow_html=True)
                        gk4.markdown(kcard("Días con pérdida", fmt_num(dias_neg), "plain"), unsafe_allow_html=True)

                    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

                    # Gráfica miembros totales
                    fig_g1 = go.Figure()
                    fig_g1.add_trace(go.Scatter(
                        x=dg["fecha"], y=dg["miembros"], name="Miembros",
                        line=dict(color=PURPLEL, width=2.5),
                        fill="tozeroy", fillcolor="rgba(168,85,247,0.12)",
                        hovertemplate="%{x|%d/%m/%Y}<br><b>%{y:,.0f} miembros</b><extra></extra>"
                    ))
                    fig_g1.update_layout(**{k:v for k,v in BASE_TG.items() if k not in ("xaxis","yaxis")},
                        title=dict(text="Evolución de suscriptores",
                            font=dict(color=WHITE, size=13, weight=700)))
                    fig_g1.update_xaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
                    fig_g1.update_yaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
                    st.plotly_chart(fig_g1, use_container_width=True, config={"displayModeBar": False})

                    # Segunda gráfica: entradas/salidas si hay datos brutos, si no cambio neto
                    fig_g2 = go.Figure()
                    if has_gross_data:
                        fig_g2.add_trace(go.Bar(
                            x=dg["fecha"], y=dg["entradas"], name="Entradas",
                            marker=dict(color=GREEN, opacity=0.85),
                            hovertemplate="%{x|%d/%m/%Y}<br><b>+%{y} entradas</b><extra></extra>"
                        ))
                        fig_g2.add_trace(go.Bar(
                            x=dg["fecha"], y=-dg["salidas"], name="Salidas",
                            marker=dict(color=RED, opacity=0.85),
                            hovertemplate="%{x|%d/%m/%Y}<br><b>-%{y} salidas</b><extra></extra>"
                        ))
                        g2_title = "Entradas y salidas diarias"
                    else:
                        # Cambio neto: verde si creció, rojo si perdió
                        net_col = dg["net"] if "net" in dg.columns else (dg["entradas"] - dg["salidas"])
                        bar_colors = [GREEN if v >= 0 else RED for v in net_col]
                        fig_g2.add_trace(go.Bar(
                            x=dg["fecha"], y=net_col,
                            name="Cambio neto",
                            marker=dict(color=bar_colors, opacity=0.85),
                            hovertemplate=(
                                "%{x|%d/%m/%Y}<br>"
                                "<b>%{y:+d} suscriptores</b><br>"
                                "<span style='color:#94A3B8'>Verde = más entradas que salidas<br>"
                                "Rojo = más salidas que entradas</span>"
                                "<extra></extra>"
                            )
                        ))
                        fig_g2.add_hline(y=0, line_color=MUTED2, line_width=1)
                        g2_title = "Cambio neto diario de suscriptores"

                    fig_g2.update_layout(**{k:v for k,v in BASE_TG.items() if k not in ("xaxis","yaxis")},
                        barmode="relative",
                        title=dict(text=g2_title, font=dict(color=WHITE, size=13, weight=700)))
                    fig_g2.update_xaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
                    fig_g2.update_yaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9),
                                        zeroline=True, zerolinecolor=MUTED2)
                    st.plotly_chart(fig_g2, use_container_width=True, config={"displayModeBar": False})

                    if not has_gross_data:
                        st.markdown(
                            f"<div style='font-size:.68rem;color:{MUTED};margin-top:-.5rem'>"
                            "⚠ Cambio neto: una barra verde significa que ese día entró más gente de la que salió, "
                            "pero pueden haber habido salidas. Los datos brutos de entradas/salidas por separado "
                            "no están disponibles para este canal.</div>",
                            unsafe_allow_html=True
                        )

                    # Tabla detalle
                    with st.expander("Ver detalle diario"):
                        if has_gross_data:
                            tbl_g = dg[["fecha","miembros","entradas","salidas"]].copy()
                            tbl_g["fecha"] = tbl_g["fecha"].dt.strftime("%d/%m/%Y")
                            tbl_g.columns  = ["Fecha","Miembros","Entradas","Salidas"]
                        else:
                            net_col = dg["net"] if "net" in dg.columns else (dg["entradas"] - dg["salidas"])
                            tbl_g = dg[["fecha","miembros"]].copy()
                            tbl_g["neto"] = net_col.values
                            tbl_g["fecha"] = tbl_g["fecha"].dt.strftime("%d/%m/%Y")
                            tbl_g.columns  = ["Fecha","Miembros","Neto"]
                        st.dataframe(tbl_g.set_index("Fecha"), use_container_width=True)

            # ── STATS AVANZADAS ───────────────────────────────────────────────
            if stats:
                st.markdown('<div class="slabel">Estadísticas avanzadas</div>',
                    unsafe_allow_html=True)
                sa1, sa2, sa3, sa4 = st.columns(4)
                sa1.markdown(kcard("Suscriptores actuales",
                    fmt_num(stats.get("subs_actual", subs)), "pu","pu"), unsafe_allow_html=True)
                sa2.markdown(kcard("Suscriptores anterior",
                    fmt_num(stats.get("subs_anterior",0)), "plain"), unsafe_allow_html=True)
                sa3.markdown(kcard("Vistas prom./post",
                    str(stats.get("vistas_post","—")), "cy","cy"), unsafe_allow_html=True)
                sa4.markdown(kcard("Reacciones prom./post",
                    str(stats.get("shares_post","—")), "plain"), unsafe_allow_html=True)

# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;padding:2.5rem 0 1rem 0;">
  <span style="font-size:.6rem;letter-spacing:.3em;text-transform:uppercase;
    background:linear-gradient(90deg,{PURPLEL},{CYANL});
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;font-weight:700;">
    ⚡ DIGITAL CREW &nbsp;·&nbsp; CONTROL DE PAUTA &nbsp;·&nbsp; {datetime.now().year}
  </span>
</div>
""", unsafe_allow_html=True)
