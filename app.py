import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import date, timedelta, datetime
import io
import os
import json
import html as _html

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
    "spend":       ["importe gastado (cop)","importe gastado (usd)","importe gastado",
                    "amount spent (cop)","amount spent (usd)","amount spent","gasto","spend"],
    "results":     ["resultados","resultado","results","result",
                    "registros completados","registros","registrations completed"],
    "cpr":         ["costo por resultado","coste por resultado","cost per result","cpr"],
    "impressions": ["impresiones","impressions"],
    "clicks":      ["clics en el enlace","link clicks","clics (todos)","clics","clicks",
                    "clics en enlace"],
    "ctr":         ["ctr (tasa de clics en el enlace)","ctr (link click-through rate)",
                    "tasa de clics en el enlace","ctr"],
    "reach":       ["alcance","reach"],
    "frequency":   ["frecuencia","frequency"],
    "campaign":    ["nombre de la campaña","nombre de campaña","campaign name","campaña"],
    "adset":       ["nombre del conjunto de anuncios","conjunto de anuncios","ad set name","adset"],
    "ad":          ["nombre del anuncio","anuncio","ad name","ad"],
    # Video metrics
    "video_plays": ["reproducciones de video","reproducciones de vídeo","video plays",
                    "reproduccion de video","reproducciones"],
    "video_3s":    ["reproducciones de vídeo de al menos 3 segundos",
                    "reproducciones de video de al menos 3 segundos",
                    "3-second video plays","video reproducido 3 segundos",
                    "reproducciones de video de 3 segundos"],
    "video_p25":   ["porcentaje de reproducción del video al 25%","video plays at 25%",
                    "video watched at 25%","video visto al 25%"],
    "video_p50":   ["porcentaje de reproducción del video al 50%","video plays at 50%",
                    "video watched at 50%","video visto al 50%"],
    "video_p75":   ["porcentaje de reproducción del video al 75%","video plays at 75%",
                    "video watched at 75%","video visto al 75%"],
    "video_p100":  ["porcentaje de reproducción del video al 100%","video plays at 100%",
                    "video watched at 100%","video visto al 100%"],
    "thruplay":    ["thruplays","thruplay","reproducciones completas"],
    "cpm":         ["cpm (coste por 1.000 impresiones)","cpm (cost per 1,000 impressions)",
                    "cpm","coste por 1000 impresiones","costo por 1000 impresiones"],
    "cpp":         ["costo por clic en el enlace","coste por clic en el enlace",
                    "cost per link click","cpc","coste por clic"],
    "ad_id":       ["id del anuncio","ad id","id de anuncio","identificador del anuncio"],
    "ad_url":      ["url de vista previa del anuncio","url del anuncio","ad preview link",
                    "permalink de la publicación","permalink url","url de la publicación",
                    "post url","enlace de la publicación"],
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
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');
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

/* Clase utilitaria: ocultar solo en móvil */
.mobile-hidden{{display:block;}}

/* ══════════════════════════════════════════════════════
   RESPONSIVE — TABLET  (≤ 900px)
══════════════════════════════════════════════════════ */
@media (max-width:900px){{
  .block-container{{padding:1rem 1rem 2rem 1rem!important;}}
  .stTabs [data-baseweb="tab-list"]{{
    overflow-x:auto!important;flex-wrap:nowrap!important;
    -webkit-overflow-scrolling:touch!important;
    scrollbar-width:none!important;gap:2px!important;padding:4px!important;}}
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar{{display:none;}}
  .stTabs [data-baseweb="tab"]{{
    font-size:.72rem!important;padding:.38rem .75rem!important;
    white-space:nowrap!important;}}
  [data-testid="stHorizontalBlock"]{{flex-wrap:wrap!important;gap:.4rem 0!important;}}
  [data-testid="column"]{{
    min-width:calc(50% - .4rem)!important;
    flex:1 1 calc(50% - .4rem)!important;}}
  .hdr{{flex-direction:column;gap:.4rem;padding-bottom:.9rem;}}
  .hdr-right{{text-align:left;}}
  .hdr-logo{{font-size:1.3rem!important;}}
  .kc{{padding:.85rem .9rem;border-radius:12px;}}
  .kc-val{{font-size:1.2rem!important;}}
  .kc-lbl{{font-size:.55rem!important;}}
}}

/* ══════════════════════════════════════════════════════
   RESPONSIVE — MOBILE  (≤ 640px)
══════════════════════════════════════════════════════ */
@media (max-width:640px){{
  /* Contenedor */
  .block-container{{padding:.85rem .75rem 5rem .75rem!important;max-width:100%!important;overflow-x:hidden!important;}}

  /* ── Ocultar en móvil ── */
  .mobile-hidden{{display:none!important;}}

  /* ── Header: centrado y compacto ── */
  .hdr{{
    flex-direction:column;align-items:center;text-align:center;
    gap:.25rem;padding-bottom:.75rem;border-bottom-width:1px;}}
  .hdr-logo{{font-size:1.2rem!important;letter-spacing:.18em!important;}}
  .hdr-sub{{font-size:.57rem!important;letter-spacing:.18em!important;}}
  .hdr-dot{{width:6px;height:6px;}}
  .hdr-right{{font-size:.63rem!important;text-align:center!important;}}
  .hdr-right strong{{font-size:.73rem!important;display:inline!important;}}

  /* ── Botón actualizar: compacto ── */
  .stButton>button{{
    font-size:.76rem!important;padding:.55rem .7rem!important;
    min-height:44px!important;border-radius:12px!important;
    letter-spacing:.05em!important;}}

  /* ── Tabs: scroll horizontal sin barra ── */
  .stTabs [data-baseweb="tab-list"]{{
    overflow-x:auto!important;flex-wrap:nowrap!important;
    -webkit-overflow-scrolling:touch!important;
    scrollbar-width:none!important;gap:3px!important;
    padding:3px 2px!important;}}
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar{{display:none;}}
  .stTabs [data-baseweb="tab"]{{
    font-size:.67rem!important;padding:.38rem .65rem!important;
    white-space:nowrap!important;min-width:auto!important;}}

  /* ── COLUMNAS: todo a 100% por defecto ── */
  [data-testid="stHorizontalBlock"]{{flex-wrap:wrap!important;gap:.45rem 0!important;}}
  [data-testid="column"]{{
    width:100%!important;min-width:100%!important;
    flex:1 1 100%!important;padding:0!important;box-sizing:border-box!important;}}

  /* Filas de 4 KPIs → cuadrícula 2×2 */
  [data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(4))
    >[data-testid="column"]{{
      min-width:calc(50% - .25rem)!important;width:calc(50% - .25rem)!important;
      flex:1 1 calc(50% - .25rem)!important;}}
  /* Filas de 3 KPIs → 2+1 */
  [data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3)):not(:has(>[data-testid="column"]:nth-child(4)))
    >[data-testid="column"]{{
      min-width:calc(50% - .25rem)!important;width:calc(50% - .25rem)!important;
      flex:1 1 calc(50% - .25rem)!important;}}

  /* ── KPI cards ── */
  .kc{{padding:1rem 1.1rem!important;border-radius:14px!important;margin-bottom:.5rem!important;}}
  .kc-val{{font-size:1.45rem!important;letter-spacing:-.01em!important;line-height:1.15!important;}}
  .kc-lbl{{font-size:.57rem!important;letter-spacing:.16em!important;margin-bottom:.25rem!important;}}
  .kc-sub{{font-size:.63rem!important;margin-top:.3rem!important;}}
  .kc-arr{{font-size:.75rem!important;}}

  /* ── Section labels ── */
  .slabel{{font-size:.54rem!important;margin:1.1rem 0 .7rem 0!important;}}

  /* ── Popovers: fix ícono expand_more ── */
  [data-testid="stPopover"] button{{
    font-size:.74rem!important;min-height:44px!important;
    border-radius:10px!important;}}
  [data-testid="stPopover"] button .material-icons,
  [data-testid="stPopover"] button span[class*="material"]{{
    font-family:'Material Icons'!important;font-size:1.1rem!important;
    vertical-align:middle!important;line-height:1!important;}}

  /* ── File uploader ── */
  [data-testid="stFileUploader"]{{padding:.7rem!important;border-radius:12px!important;}}
  [data-testid="stFileUploader"] p{{font-size:.74rem!important;}}

  /* ── Progress bar pauta ── */
  .prog-wrap{{padding:.85rem .95rem!important;border-radius:12px!important;}}
  .prog-title{{font-size:.56rem!important;}}
  .prog-pct{{font-size:.92rem!important;}}
  .prog-bar{{height:9px!important;border-radius:5px!important;}}
  .ps{{font-size:.63rem!important;padding:.38rem!important;}}

  /* ── DataFrames: scroll horizontal ── */
  [data-testid="stDataFrame"]{{overflow-x:auto!important;-webkit-overflow-scrolling:touch!important;}}
  [data-testid="stDataFrame"] table{{min-width:460px;font-size:.71rem!important;}}
  [data-testid="stDataFrame"] th,[data-testid="stDataFrame"] td{{padding:.32rem .45rem!important;}}

  /* ── Selectbox e inputs ── */
  [data-testid="stSelectbox"] div,
  [data-testid="stDateInput"] input{{font-size:.76rem!important;}}

  /* ── Expanders ── */
  [data-testid="stExpander"] summary{{font-size:.76rem!important;min-height:40px!important;}}

  /* ── Textos generales ── */
  p,li{{font-size:.79rem!important;line-height:1.65!important;}}
  h1{{font-size:1.25rem!important;}} h2{{font-size:1.05rem!important;}} h3{{font-size:.92rem!important;}}

  /* ── Métricas nativas Streamlit ── */
  [data-testid="stMetric"]{{background:{CARD2};border-radius:12px;padding:.8rem!important;}}
  [data-testid="stMetricValue"]{{font-size:1.25rem!important;}}
  [data-testid="stMetricLabel"]{{font-size:.6rem!important;}}

  /* ── Ocultar barra lateral de Streamlit si aparece ── */
  section[data-testid="stSidebar"]{{display:none!important;}}
}}

/* ══════════════════════════════════════════════════════
   RESPONSIVE — TELÉFONO PEQUEÑO  (≤ 400px)
══════════════════════════════════════════════════════ */
@media (max-width:400px){{
  .block-container{{padding:.7rem .6rem 5rem .6rem!important;}}
  .kc-val{{font-size:1.25rem!important;}}
  .kc{{padding:.85rem .95rem!important;}}
  .hdr-logo{{font-size:1rem!important;letter-spacing:.12em!important;}}
  .stTabs [data-baseweb="tab"]{{font-size:.61rem!important;padding:.33rem .52rem!important;}}
  /* En teléfonos muy pequeños, 3 y 4 cols también van a 100% */
  [data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(3))
    >[data-testid="column"]{{
      min-width:100%!important;width:100%!important;flex:1 1 100%!important;}}
}}
</style>
""", unsafe_allow_html=True)

# Forzar viewport correcto en móvil (sin este tag el navegador hace zoom-out)
components.html("""
<script>
(function(){
  var m = parent.document.querySelector('meta[name="viewport"]');
  if(!m){
    m = parent.document.createElement('meta');
    m.name = 'viewport';
    parent.document.head.appendChild(m);
  }
  m.content = 'width=device-width, initial-scale=1.0, viewport-fit=cover';
})();
</script>
""", height=0)

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
        <strong>{(datetime.utcnow() - timedelta(hours=5)).strftime('%d/%m/%Y  %H:%M')}</strong>
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
pg0, pg1, pg2, pg3, pg4 = st.tabs(["📊  Resumen", "📅  Mes Actual", "📘  Meta Ads", "📲  Telegram", "🤖  IA"])

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
            f"<div class='mobile-hidden' style='padding-top:.6rem;font-size:.72rem;color:{MUTED};font-weight:500'>"
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

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "meta_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def _safe_fname(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)

def _save_report_disk(entry: dict):
    base = _safe_fname(entry["name"])
    entry["df"].to_csv(os.path.join(REPORTS_DIR, base + ".csv"), index=False)
    meta = {k: v for k, v in entry.items() if k != "df"}
    meta["date_start"] = meta["date_start"].isoformat() if meta["date_start"] else None
    meta["date_end"]   = meta["date_end"].isoformat()   if meta["date_end"]   else None
    with open(os.path.join(REPORTS_DIR, base + ".json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

def _delete_report_disk(name: str):
    base = _safe_fname(name)
    for ext in (".csv", ".json"):
        p = os.path.join(REPORTS_DIR, base + ext)
        if os.path.exists(p):
            os.remove(p)

def _load_reports_disk() -> list:
    loaded = []
    for fn in os.listdir(REPORTS_DIR):
        if not fn.endswith(".json"):
            continue
        json_path = os.path.join(REPORTS_DIR, fn)
        csv_path  = json_path.replace(".json", ".csv")
        if not os.path.exists(csv_path):
            continue
        try:
            with open(json_path, encoding="utf-8") as f:
                meta = json.load(f)
            df = pd.read_csv(csv_path, keep_default_na=False)
            # Re-aplicar conversión numérica a columnas de métricas
            num_keys = ("spend","results","cpr","impressions","clicks","ctr","reach","freq",
                        "video_plays","video_3s","video_p25","video_p50","video_p75",
                        "video_p100","thruplay","cpm","cpp")
            for k in num_keys:
                col = meta.get("cols", {}).get(k)
                if col and col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            meta["df"] = df
            for key in ("date_start", "date_end"):
                if meta.get(key):
                    meta[key] = date.fromisoformat(meta[key])
                else:
                    meta[key] = None
            loaded.append(meta)
        except Exception:
            pass
    return loaded

with pg2:

    MESES_ES_S = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

    def _month_label(ym):
        try:
            y, m = ym.split("-")
            return f"{MESES_ES_S[int(m)-1]} {y}"
        except Exception:
            return ym

    def _detect_date_range(df):
        """Busca columnas de fecha en el CSV y devuelve (min_date, max_date)."""
        keywords = ["date", "fecha", "start", "stop", "inicio", "fin",
                    "day", "semana", "week", "month", "mes", "periodo", "período"]
        best_min = best_max = None
        for col in df.columns:
            if any(k in col.lower() for k in keywords):
                try:
                    parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                    valid = parsed.dropna()
                    if valid.empty:
                        continue
                    cmin, cmax = valid.min().date(), valid.max().date()
                    if best_min is None or cmin < best_min:
                        best_min = cmin
                    if best_max is None or cmax > best_max:
                        best_max = cmax
                except Exception:
                    pass
        return best_min, best_max

    def _fmt_dr(d1, d2):
        """Formatea un rango de fechas en español."""
        if d1 is None:
            return "Sin fechas"
        M = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        if d1 == d2:
            return f"{d1.day} {M[d1.month-1]} {d1.year}"
        if d1.year == d2.year and d1.month == d2.month:
            return f"{d1.day}–{d2.day} {M[d1.month-1]} {d1.year}"
        if d1.year == d2.year:
            return f"{d1.day} {M[d1.month-1]} – {d2.day} {M[d2.month-1]} {d1.year}"
        return f"{d1.day} {M[d1.month-1]} {d1.year} – {d2.day} {M[d2.month-1]} {d2.year}"

    if "meta_reports" not in st.session_state:
        st.session_state.meta_reports = _load_reports_disk()
    reports = st.session_state.meta_reports

    BASE_MA = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(20,25,41,0.6)",
        font=dict(family="Inter", color=MUTED, size=11),
        margin=dict(l=10, r=10, t=60, b=10), height=320,
        hoverlabel=dict(bgcolor=CARD2, font_color=WHITE),
        legend=dict(font=dict(color=MUTED, size=10), bgcolor="rgba(0,0,0,0)",
                    orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )

    # ── UPLOADER ──────────────────────────────────────────────────────────────
    st.markdown('<div class="slabel">Subir reporte</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "CSV Meta Ads", type=["csv"], label_visibility="collapsed"
    )

    if uploaded_file:
        try:
            raw = uploaded_file.read()
            try:
                df_up = pd.read_csv(io.BytesIO(raw), thousands=".", decimal=",",
                                    dtype=str, keep_default_na=False)
            except Exception:
                df_up = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
            df_up.columns = [str(c).strip() for c in df_up.columns]

            col_spend     = find_col(df_up, "spend")
            col_results   = find_col(df_up, "results")
            col_cpr       = find_col(df_up, "cpr")
            col_impr      = find_col(df_up, "impressions")
            col_clicks    = find_col(df_up, "clicks")
            col_ctr       = find_col(df_up, "ctr")
            col_reach     = find_col(df_up, "reach")
            col_freq      = find_col(df_up, "frequency")
            col_camp      = find_col(df_up, "campaign")
            col_adset     = find_col(df_up, "adset")
            col_ad        = find_col(df_up, "ad")
            col_vplays    = find_col(df_up, "video_plays")
            col_v3s       = find_col(df_up, "video_3s")
            col_vp25      = find_col(df_up, "video_p25")
            col_vp50      = find_col(df_up, "video_p50")
            col_vp75      = find_col(df_up, "video_p75")
            col_vp100     = find_col(df_up, "video_p100")
            col_thruplay  = find_col(df_up, "thruplay")
            col_cpm       = find_col(df_up, "cpm")
            col_cpp       = find_col(df_up, "cpp")
            col_ad_id     = find_col(df_up, "ad_id")
            col_ad_url    = find_col(df_up, "ad_url")

            for c in [col_spend, col_results, col_cpr, col_impr,
                      col_clicks, col_ctr, col_reach, col_freq,
                      col_vplays, col_v3s, col_vp25, col_vp50,
                      col_vp75, col_vp100, col_thruplay, col_cpm, col_cpp]:
                if c:
                    df_up[c] = df_up[c].apply(parse_meta_num)

            if col_ad:      rtype = "Anuncios"
            elif col_adset: rtype = "Públicos"
            elif col_camp:  rtype = "Campañas"
            else:           rtype = "General"

            name_col = col_ad or col_adset or col_camp
            if name_col:
                df_up = df_up[df_up[name_col].apply(
                    lambda x: str(x).strip().lower() not in SKIP_VALS)]

            # Auto-detectar rango de fechas del reporte
            d_start, d_end = _detect_date_range(df_up)
            date_label = _fmt_dr(d_start, d_end)
            month_key  = d_start.strftime("%Y-%m") if d_start else "9999-99"

            entry = {
                "name": uploaded_file.name, "type": rtype,
                "month": month_key, "month_label": _month_label(month_key) if d_start else "?",
                "date_start": d_start, "date_end": d_end, "date_label": date_label,
                "df": df_up,
                "cols": dict(spend=col_spend, results=col_results, cpr=col_cpr,
                             impressions=col_impr, clicks=col_clicks, ctr=col_ctr,
                             reach=col_reach, freq=col_freq,
                             campaign=col_camp, adset=col_adset, ad=col_ad,
                             video_plays=col_vplays, video_3s=col_v3s,
                             video_p25=col_vp25, video_p50=col_vp50,
                             video_p75=col_vp75, video_p100=col_vp100,
                             thruplay=col_thruplay, cpm=col_cpm, cpp=col_cpp,
                             ad_id=col_ad_id, ad_url=col_ad_url)
            }
            # Reemplazar si ya existe mismo archivo
            _delete_report_disk(uploaded_file.name)
            reports = [r for r in reports if r["name"] != uploaded_file.name]
            reports.append(entry)
            st.session_state.meta_reports = reports
            _save_report_disk(entry)
            st.success(f"✓  {rtype} · {date_label} · {len(df_up)} filas")
        except Exception as e:
            st.error(f"Error leyendo el archivo: {e}")

    # ── TABLA DE REPORTES CARGADOS (con botón eliminar) ───────────────────────
    if reports:
        st.markdown('<div class="slabel">Reportes cargados</div>', unsafe_allow_html=True)
        reps_sorted = sorted(reports, key=lambda x: (x.get("date_start") or date(2000,1,1)))
        for i, r in enumerate(reps_sorted):
            c = r["cols"]; df_r = r["df"]
            sp  = fmt_cop(float(df_r[c["spend"]].sum()))   if c["spend"]   else "—"
            rs  = fmt_num(float(df_r[c["results"]].sum())) if c["results"] else "—"
            dl  = r.get("date_label", r.get("month_label", "?"))
            idx_orig = reports.index(r)

            rc1, rc2, rc3, rc4, rc5 = st.columns([3.2, 1.2, 1.2, 1.2, 0.5])
            rc1.markdown(
                f"<span style='color:{WHITE};font-size:.8rem;font-weight:600'>📅 {dl}</span>"
                f"<span style='color:{MUTED};font-size:.75rem;margin-left:8px'>{r['type']}</span>",
                unsafe_allow_html=True)
            rc2.markdown(f"<span style='color:{PURPLEL};font-size:.8rem;font-weight:700'>{sp}</span>",
                         unsafe_allow_html=True)
            rc3.markdown(f"<span style='color:{CYANL};font-size:.8rem;font-weight:700'>{rs} leads</span>",
                         unsafe_allow_html=True)
            rc4.markdown(f"<span style='color:{MUTED};font-size:.72rem'>{r['name'][:28]}</span>",
                         unsafe_allow_html=True)
            if rc5.button("✕", key=f"del_rep_{i}", help="Eliminar reporte"):
                _delete_report_disk(r["name"])
                st.session_state.meta_reports.pop(idx_orig)
                st.rerun()

        # ── KPIs GLOBALES ─────────────────────────────────────────────────────
        all_spend = all_results = all_impr = 0.0
        cpr_vals: list = []; ctr_vals: list = []
        for r in reports:
            c = r["cols"]; df_r = r["df"]
            if c["spend"]:        all_spend   += float(df_r[c["spend"]].sum())
            if c["results"]:      all_results += float(df_r[c["results"]].sum())
            if c["impressions"]:  all_impr    += float(df_r[c["impressions"]].sum())
            if c["cpr"] and not df_r[c["cpr"]].dropna().empty:
                cpr_vals.append(float(df_r[c["cpr"]].mean()))
            if c["ctr"] and not df_r[c["ctr"]].dropna().empty:
                ctr_vals.append(float(df_r[c["ctr"]].mean()))

        avg_cpr_g = float(np.mean(cpr_vals)) if cpr_vals else (all_spend / all_results if all_results else np.nan)
        avg_ctr_g = float(np.mean(ctr_vals)) if ctr_vals else np.nan
        ctr_txt   = f"{avg_ctr_g:.2f}%" if not np.isnan(avg_ctr_g) else "—"
        n_meses   = len({r.get("month") for r in reports})

        st.markdown('<div class="slabel">Resumen consolidado</div>', unsafe_allow_html=True)
        gk1,gk2,gk3,gk4,gk5 = st.columns(5)
        gk1.markdown(kcard("Total Invertido",  fmt_cop(all_spend),    "pu","pu"), unsafe_allow_html=True)
        gk2.markdown(kcard("Total Resultados", fmt_num(all_results),  "cy","cy"), unsafe_allow_html=True)
        gk3.markdown(kcard("CPR Promedio",     fmt_cop(avg_cpr_g),    "plain"),   unsafe_allow_html=True)
        gk4.markdown(kcard("CTR Promedio",     ctr_txt,               "gn","gn"), unsafe_allow_html=True)
        gk5.markdown(kcard("Meses cargados",   str(n_meses),          "plain"),   unsafe_allow_html=True)

        st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

        # ── SUB-PESTAÑAS DE ANÁLISIS ──────────────────────────────────────────
        ma1, ma2, ma3, ma4, ma5 = st.tabs([
            "📈 Tendencias", "🏆 Campañas", "👥 Públicos", "🎨 Anuncios", "🔍 Diagnóstico"
        ])

        # ── Helpers de visualización ──────────────────────────────────────────
        def _trunc(s, n=32):
            s = str(s); return s[:n]+"…" if len(s) > n else s

        COLORS_PIE = [PURPLE, CYANL, GREEN, PINK, PURPLEL, AMBER, "#9B59B6", "#1ABC9C"]

        def _podium(items, val_label="resultados", val_fmt="{:,.0f}", color=CYANL, urls=None):
            medals = ["🥇", "🥈", "🥉"]
            mc_list = [AMBER, "#C0C0C0", "#CD7F32"]
            cols_p = st.columns(min(len(items), 3))
            for idx, (col_p, (nm, vl)) in enumerate(zip(cols_p, items[:3])):
                mc = mc_list[idx]
                url = urls[idx] if urls and idx < len(urls) else None
                with col_p:
                    st.markdown(f"""
<div style="background:{CARD2};border:1px solid {mc}55;border-radius:14px;
  padding:1rem .8rem;text-align:center">
  <div style="font-size:1.6rem;line-height:1">{medals[idx]}</div>
  <div style="color:{mc};font-size:.68rem;font-weight:700;letter-spacing:.05em;
    margin:.2rem 0">PUESTO #{idx+1}</div>
  <div style="color:{WHITE};font-size:.73rem;font-weight:600;line-height:1.45;
    min-height:2.8rem;display:flex;align-items:center;justify-content:center">
    {_trunc(nm, 32)}</div>
  <div style="color:{color};font-size:1.15rem;font-weight:800;margin-top:.5rem">
    {val_fmt.format(vl)}</div>
  <div style="color:{MUTED};font-size:.64rem;margin-top:.1rem">{val_label}</div>
</div>""", unsafe_allow_html=True)
                    if url:
                        st.link_button("Ver anuncio →", url, use_container_width=True)

        def _hbar(df_plot, x_col, y_col, title, fmt_hover,
                  color_lo=PURPLE, color_hi=CYANL, xsuffix="", invert=False, h=300):
            df_s = df_plot.copy()
            df_s[y_col] = df_s[y_col].apply(lambda x: _trunc(x, 36))
            df_s = (df_s.sort_values(x_col, ascending=False).head(10)
                    if invert else
                    df_s.sort_values(x_col, ascending=True).tail(10))
            fig = go.Figure(go.Bar(
                x=df_s[x_col], y=df_s[y_col], orientation="h",
                marker=dict(color=df_s[x_col].values,
                    colorscale=[[0, color_lo], [1, color_hi]], opacity=0.9),
                hovertemplate=f"<b>%{{y}}</b><br>{fmt_hover}<extra></extra>"
            ))
            xaxis_cfg = dict(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9),
                             ticksuffix=xsuffix)
            if xsuffix == "%":
                xaxis_cfg["tickformat"] = ".2f"
            fig.update_layout(**{**BASE_MA, "height": h},
                title=dict(text=title, font=dict(color=WHITE, size=13, weight=700)),
                xaxis=xaxis_cfg,
                yaxis=dict(tickfont=dict(color=WHITE, size=9)))
            return fig

        def _donut(df_plot, name_col, val_col, title=""):
            df_d = (df_plot[[name_col, val_col]].dropna()
                    .query(f"`{val_col}` > 0")
                    .sort_values(val_col, ascending=False).head(8)).copy()
            df_d[name_col] = df_d[name_col].apply(lambda x: _trunc(x, 26))
            fig = go.Figure(go.Pie(
                labels=df_d[name_col], values=df_d[val_col], hole=0.45,
                marker=dict(colors=COLORS_PIE),
                textfont=dict(color=WHITE, size=10),
                hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>"
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", height=280,
                margin=dict(l=10, r=10, t=30, b=10),
                title=dict(text=title, font=dict(color=WHITE, size=12)),
                legend=dict(font=dict(color=MUTED, size=9), bgcolor="rgba(0,0,0,0)"),
                font=dict(family="Inter", color=MUTED)
            )
            return fig

        def _build_agg(reps, name_key):
            if not reps: return None, None, None
            dfs = []
            for r in reps:
                df_r = r["df"].copy(); df_r["__mes__"] = r.get("month_label", "")
                dfs.append(df_r)
            df_all = pd.concat(dfs, ignore_index=True)
            c0 = reps[0]["cols"]
            col_name = c0.get(name_key)
            if not col_name: return None, None, None
            agg_d = {}
            for k in ["spend","results","impressions","clicks","video_plays",
                      "video_3s","video_p25","video_p50","video_p75","video_p100","thruplay"]:
                if c0.get(k) and c0[k] in df_all.columns: agg_d[c0[k]] = "sum"
            for k in ["ctr","cpm","cpp","frequency"]:
                if c0.get(k) and c0[k] in df_all.columns: agg_d[c0[k]] = "mean"
            if not agg_d: return df_all, c0, None
            df_g = df_all.groupby(col_name).agg(agg_d).reset_index()
            if c0.get("spend") and c0.get("results") and c0["results"] in df_g.columns:
                df_g["__cpr__"] = df_g[c0["spend"]] / df_g[c0["results"]].replace(0, np.nan)
            if c0.get("video_3s") and c0.get("impressions") and c0["video_3s"] in df_g.columns:
                df_g["__hook_rate__"] = (df_g[c0["video_3s"]] /
                                         df_g[c0["impressions"]].replace(0, np.nan) * 100)
            if c0.get("video_p100") and c0.get("video_3s") and c0["video_p100"] in df_g.columns:
                df_g["__completion__"] = (df_g[c0["video_p100"]] /
                                          df_g[c0["video_3s"]].replace(0, np.nan) * 100)
            # Normalized retention rates (relative to 3s views)
            v3 = c0.get("video_3s")
            for pct_k, lbl in [("video_p25","__ret25__"),("video_p50","__ret50__"),
                                ("video_p75","__ret75__"),("video_p100","__ret100__")]:
                if c0.get(pct_k) and v3 and c0[pct_k] in df_g.columns and c0[v3] in df_g.columns:
                    df_g[lbl] = df_g[c0[pct_k]] / df_g[c0[v3]].replace(0, np.nan) * 100
            return df_all, c0, df_g

        def _ad_url_map(reps):
            """Builds {ad_name: url} from all reports using ad_url or ad_id column."""
            result = {}
            for r in reps:
                c = r["cols"]; df_r = r["df"]
                cn = c.get("ad"); cu = c.get("ad_url"); ci = c.get("ad_id")
                if not cn or cn not in df_r.columns: continue
                for _, row in df_r.iterrows():
                    nm = str(row.get(cn, ""))
                    if not nm or nm in result: continue
                    url = None
                    if cu and cu in df_r.columns:
                        v = str(row.get(cu, ""))
                        if v and v not in ("", "nan", "None"): url = v
                    if not url and ci and ci in df_r.columns:
                        v = str(row.get(ci, "")).split(".")[0].strip()
                        if v and v.isdigit():
                            url = f"https://adsmanager.facebook.com/adsmanager/manage/ads?selected_ad_ids={v}"
                    if url: result[nm] = url
            return result

        # ── TENDENCIAS ────────────────────────────────────────────────────────
        with ma1:
            monthly = []
            for r in sorted(reports, key=lambda x: x.get("month", "")):
                c = r["cols"]; df_r = r["df"]
                sp = float(df_r[c["spend"]].sum())       if c.get("spend")       else np.nan
                rs = float(df_r[c["results"]].sum())     if c.get("results")     else np.nan
                im = float(df_r[c["impressions"]].sum()) if c.get("impressions") else np.nan
                cp = float(df_r[c["cpr"]].mean())        if c.get("cpr")         else (sp/rs if rs else np.nan)
                ct = float(df_r[c["ctr"]].mean())        if c.get("ctr")         else np.nan
                cm = float(df_r[c["cpm"]].mean())        if c.get("cpm")         else (sp/im*1000 if im else np.nan)
                monthly.append({
                    "Mes": r.get("month_label", r.get("month", "")),
                    "MesKey": r.get("month", ""),
                    "Inversión": sp, "Resultados": rs,
                    "CPR": cp, "CTR": ct, "Impresiones": im, "CPM": cm
                })
            df_mon = pd.DataFrame(monthly).sort_values("MesKey").reset_index(drop=True)

            if len(df_mon) < 2:
                st.info("Sube reportes de al menos **2 meses distintos** para ver tendencias.")
            else:
                tc1, tc2 = st.columns(2)
                with tc1:
                    fig_t1 = go.Figure(go.Bar(
                        x=df_mon["Mes"], y=df_mon["Inversión"],
                        marker=dict(color=df_mon["Inversión"].values,
                            colorscale=[[0, PURPLE], [1, PURPLEL]], opacity=0.9),
                        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>"
                    ))
                    fig_t1.update_layout(**BASE_MA,
                        title=dict(text="Inversión mensual", font=dict(color=WHITE,size=13,weight=700)),
                        xaxis=dict(tickfont=dict(color=WHITE,size=9)),
                        yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9)))
                    st.plotly_chart(fig_t1, use_container_width=True, config={"displayModeBar":False})
                with tc2:
                    fig_t2 = go.Figure(go.Bar(
                        x=df_mon["Mes"], y=df_mon["Resultados"],
                        marker=dict(color=df_mon["Resultados"].values,
                            colorscale=[[0, CYAN], [1, CYANL]], opacity=0.9),
                        hovertemplate="<b>%{x}</b><br>%{y:,.0f} resultados<extra></extra>"
                    ))
                    fig_t2.update_layout(**BASE_MA,
                        title=dict(text="Resultados mensuales", font=dict(color=WHITE,size=13,weight=700)),
                        xaxis=dict(tickfont=dict(color=WHITE,size=9)),
                        yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9)))
                    st.plotly_chart(fig_t2, use_container_width=True, config={"displayModeBar":False})

                tc3, tc4 = st.columns(2)
                with tc3:
                    fig_t3 = go.Figure(go.Scatter(
                        x=df_mon["Mes"], y=df_mon["CPR"], mode="lines+markers",
                        line=dict(color=PINK, width=2.5), marker=dict(size=8, color=PINK,
                            line=dict(width=2, color=WHITE)),
                        hovertemplate="<b>%{x}</b><br>CPR: $%{y:,.0f}<extra></extra>"
                    ))
                    fig_t3.update_layout(**BASE_MA,
                        title=dict(text="Costo por Resultado · ↓ es mejor", font=dict(color=WHITE,size=13,weight=700)),
                        xaxis=dict(tickfont=dict(color=WHITE,size=9)),
                        yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9)))
                    st.plotly_chart(fig_t3, use_container_width=True, config={"displayModeBar":False})
                with tc4:
                    fig_t4 = go.Figure(go.Scatter(
                        x=df_mon["Mes"], y=df_mon["CTR"], mode="lines+markers",
                        line=dict(color=GREEN, width=2.5), marker=dict(size=8, color=GREEN,
                            line=dict(width=2, color=WHITE)),
                        hovertemplate="<b>%{x}</b><br>CTR: %{y:.2f}%<extra></extra>"
                    ))
                    fig_t4.update_layout(**BASE_MA,
                        title=dict(text="CTR mensual · ↑ es mejor", font=dict(color=WHITE,size=13,weight=700)),
                        xaxis=dict(tickfont=dict(color=WHITE,size=9)),
                        yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9),
                                   ticksuffix="%"))
                    st.plotly_chart(fig_t4, use_container_width=True, config={"displayModeBar":False})

                st.markdown('<div class="slabel">Resumen mes a mes</div>', unsafe_allow_html=True)

                def _fmt_safe(x, fmt): return fmt(x) if pd.notna(x) and not np.isnan(float(x)) else "—"
                df_tbl = df_mon[["Mes","Inversión","Resultados","CPR","CTR","Impresiones","CPM"]].copy()
                df_tbl["Inversión"]   = df_tbl["Inversión"].apply(lambda x: _fmt_safe(x, fmt_cop))
                df_tbl["Resultados"]  = df_tbl["Resultados"].apply(lambda x: _fmt_safe(x, lambda v: f"{v:,.0f}"))
                df_tbl["CPR"]         = df_tbl["CPR"].apply(lambda x: _fmt_safe(x, fmt_cop))
                df_tbl["CTR"]         = df_tbl["CTR"].apply(lambda x: _fmt_safe(x, lambda v: f"{v:.2f}%"))
                df_tbl["Impresiones"] = df_tbl["Impresiones"].apply(lambda x: _fmt_safe(x, lambda v: f"{v:,.0f}"))
                df_tbl["CPM"]         = df_tbl["CPM"].apply(lambda x: _fmt_safe(x, fmt_cop))
                st.dataframe(df_tbl, use_container_width=True, hide_index=True)

        # ── CAMPAÑAS ──────────────────────────────────────────────────────────
        with ma2:
            camp_reps = [r for r in reports if r["cols"].get("campaign")]
            if not camp_reps:
                st.info("No hay datos de campaña. Sube un reporte que incluya columna de campaña.")
            else:
                _, c0c, df_cg = _build_agg(camp_reps, "campaign")
                col_cn = c0c.get("campaign"); col_cs = c0c.get("spend"); col_cr = c0c.get("results")

                if df_cg is not None and col_cn:
                    if col_cr and col_cr in df_cg.columns:
                        top3_c = (df_cg[[col_cn, col_cr]].dropna()
                                  .query(f"`{col_cr}` > 0")
                                  .sort_values(col_cr, ascending=False).head(3))
                        if not top3_c.empty:
                            st.markdown('<div class="slabel">🏆 Mejores campañas · Resultados acumulados</div>', unsafe_allow_html=True)
                            _podium(list(zip(top3_c[col_cn], top3_c[col_cr])),
                                    val_label="resultados", val_fmt="{:,.0f}", color=CYANL)
                            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if col_cr and col_cr in df_cg.columns:
                            top_cr = df_cg[[col_cn, col_cr]].dropna().query(f"`{col_cr}` > 0")
                            st.plotly_chart(_hbar(top_cr, col_cr, col_cn,
                                "Resultados por campaña",
                                "%{x:,.0f} resultados", PURPLE, CYANL),
                                use_container_width=True, config={"displayModeBar":False})
                    with cc2:
                        if "__cpr__" in df_cg.columns:
                            eff_c = df_cg[[col_cn, "__cpr__"]].dropna().query("__cpr__ > 0")
                            st.plotly_chart(_hbar(eff_c, "__cpr__", col_cn,
                                "Campañas más eficientes · ↓ CPR",
                                "CPR: $%{x:,.0f}", GREEN, CYANL, invert=True),
                                use_container_width=True, config={"displayModeBar":False})

                    if col_cs and col_cs in df_cg.columns:
                        st.plotly_chart(_donut(df_cg, col_cn, col_cs,
                            "Distribución del gasto por campaña"),
                            use_container_width=True, config={"displayModeBar":False})

        # ── PÚBLICOS ──────────────────────────────────────────────────────────
        with ma3:
            pub_reps = [r for r in reports if r["cols"].get("adset")]
            if not pub_reps:
                st.info("No hay datos de públicos. Sube un reporte que incluya columna de conjunto de anuncios.")
            else:
                _, c0p, df_pg = _build_agg(pub_reps, "adset")
                col_pn = c0p.get("adset"); col_ps = c0p.get("spend")
                col_pr = c0p.get("results"); col_pt = c0p.get("ctr")

                if df_pg is not None and col_pn:
                    if col_pr and col_pr in df_pg.columns:
                        top3_p = (df_pg[[col_pn, col_pr]].dropna()
                                  .query(f"`{col_pr}` > 0")
                                  .sort_values(col_pr, ascending=False).head(3))
                        if not top3_p.empty:
                            st.markdown('<div class="slabel">🏆 Mejores públicos · Resultados acumulados</div>', unsafe_allow_html=True)
                            _podium(list(zip(top3_p[col_pn], top3_p[col_pr])),
                                    val_label="resultados", val_fmt="{:,.0f}", color=CYANL)
                            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

                    pc1, pc2 = st.columns(2)
                    with pc1:
                        if col_pr and col_pr in df_pg.columns:
                            top_pr = df_pg[[col_pn, col_pr]].dropna().query(f"`{col_pr}` > 0")
                            st.plotly_chart(_hbar(top_pr, col_pr, col_pn,
                                "Resultados por público",
                                "%{x:,.0f} resultados", PURPLE, CYANL),
                                use_container_width=True, config={"displayModeBar":False})
                    with pc2:
                        if "__cpr__" in df_pg.columns:
                            eff_p = df_pg[[col_pn, "__cpr__"]].dropna().query("__cpr__ > 0")
                            st.plotly_chart(_hbar(eff_p, "__cpr__", col_pn,
                                "Públicos más eficientes · ↓ CPR",
                                "CPR: $%{x:,.0f}", GREEN, CYANL, invert=True),
                                use_container_width=True, config={"displayModeBar":False})

                    if col_pt and col_pt in df_pg.columns:
                        st.markdown('<div class="slabel">Relevancia del targeting · CTR por público</div>', unsafe_allow_html=True)
                        ctr_p = df_pg[[col_pn, col_pt]].dropna().query(f"`{col_pt}` > 0")
                        st.plotly_chart(_hbar(ctr_p, col_pt, col_pn,
                            "CTR por público · ↑ mejor",
                            "CTR: %{x:.2f}%", PINK, AMBER, xsuffix="%"),
                            use_container_width=True, config={"displayModeBar":False})

                    if col_ps and col_ps in df_pg.columns:
                        st.plotly_chart(_donut(df_pg, col_pn, col_ps,
                            "Distribución del gasto por público"),
                            use_container_width=True, config={"displayModeBar":False})

        # ── ANUNCIOS ──────────────────────────────────────────────────────────
        with ma4:
            ad_reps = [r for r in reports if r["cols"].get("ad")]
            if not ad_reps:
                st.info("No hay datos de anuncios. Sube un reporte que incluya columna de anuncio.")
            else:
                _, c0a, df_ag = _build_agg(ad_reps, "ad")
                col_an  = c0a.get("ad");     col_as_ = c0a.get("spend")
                col_ar  = c0a.get("results"); col_at  = c0a.get("ctr")
                col_av3 = c0a.get("video_3s"); col_avim = c0a.get("impressions")
                col_avp25 = c0a.get("video_p25"); col_avp50 = c0a.get("video_p50")
                col_avp75 = c0a.get("video_p75"); col_avp100 = c0a.get("video_p100")
                col_atp = c0a.get("thruplay"); col_avpl = c0a.get("video_plays")

                if df_ag is not None and col_an:
                    ad_urls = _ad_url_map(ad_reps)

                    # ── TOP 3 RESULTADOS (con link) ───────────────────────────
                    if col_ar and col_ar in df_ag.columns:
                        top3_a = (df_ag[[col_an, col_ar]].dropna()
                                  .query(f"`{col_ar}` > 0")
                                  .sort_values(col_ar, ascending=False).head(3))
                        if not top3_a.empty:
                            st.markdown('<div class="slabel">🏆 Mejores anuncios · Resultados acumulados</div>', unsafe_allow_html=True)
                            urls_top = [ad_urls.get(nm) for nm in top3_a[col_an]]
                            _podium(list(zip(top3_a[col_an], top3_a[col_ar])),
                                    val_label="resultados", val_fmt="{:,.0f}",
                                    color=CYANL, urls=urls_top)
                            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

                    # ── RANKINGS ─────────────────────────────────────────────
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        if col_ar and col_ar in df_ag.columns:
                            top_ar = df_ag[[col_an, col_ar]].dropna().query(f"`{col_ar}` > 0")
                            st.plotly_chart(_hbar(top_ar, col_ar, col_an,
                                "Resultados por anuncio",
                                "%{x:,.0f} resultados", PURPLE, CYANL),
                                use_container_width=True, config={"displayModeBar":False})
                    with ac2:
                        if "__cpr__" in df_ag.columns:
                            eff_a = df_ag[[col_an, "__cpr__"]].dropna().query("__cpr__ > 0")
                            st.plotly_chart(_hbar(eff_a, "__cpr__", col_an,
                                "Anuncios más eficientes · ↓ CPR",
                                "CPR: $%{x:,.0f}", GREEN, CYANL, invert=True),
                                use_container_width=True, config={"displayModeBar":False})

                    if col_at and col_at in df_ag.columns:
                        top_ctr_a = df_ag[[col_an, col_at]].dropna().query(f"`{col_at}` > 0")
                        st.plotly_chart(_hbar(top_ctr_a, col_at, col_an,
                            "CTR por anuncio · ↑ mejor",
                            "CTR: %{x:.2f}%", PINK, AMBER, xsuffix="%"),
                            use_container_width=True, config={"displayModeBar":False})

                    # ── VIDEO / HOOK ──────────────────────────────────────────
                    has_video = any(c0a.get(k) for k in
                        ["video_3s","video_p25","video_p50","video_p75","video_p100","thruplay"])
                    if has_video:
                        st.markdown(f"""
<div style="background:linear-gradient(135deg,{PURPLE}22,{CYANL}11);
  border:1px solid {PURPLE}44;border-radius:12px;padding:.6rem 1rem;margin:.8rem 0 .4rem 0">
  <div style="color:{WHITE};font-weight:700;font-size:.88rem">🎬 Análisis de Video · Hook & Retención</div>
  <div style="color:{MUTED};font-size:.72rem;margin-top:.1rem">
    Hook Rate = reproducciones 3s / impresiones &nbsp;·&nbsp;
    Completado = vistas 100% / reproducciones 3s</div>
</div>""", unsafe_allow_html=True)

                        # Top 3 por hook rate con link
                        if "__hook_rate__" in df_ag.columns:
                            top3_hk = (df_ag[[col_an, "__hook_rate__"]].dropna()
                                       .query("__hook_rate__ > 0")
                                       .sort_values("__hook_rate__", ascending=False).head(3))
                            if not top3_hk.empty:
                                st.markdown('<div class="slabel">🎣 Top 3 · Mayor Hook Rate (engancha en los primeros 3s)</div>', unsafe_allow_html=True)
                                urls_hk = [ad_urls.get(nm) for nm in top3_hk[col_an]]
                                _podium(list(zip(top3_hk[col_an], top3_hk["__hook_rate__"])),
                                        val_label="hook rate", val_fmt="{:.2f}%",
                                        color=AMBER, urls=urls_hk)
                                st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

                        # Top 3 por completado con link
                        if "__completion__" in df_ag.columns:
                            top3_comp = (df_ag[[col_an, "__completion__"]].dropna()
                                         .query("__completion__ > 0")
                                         .sort_values("__completion__", ascending=False).head(3))
                            if not top3_comp.empty:
                                st.markdown('<div class="slabel">✅ Top 3 · Mayor tasa de completado (ven el video entero)</div>', unsafe_allow_html=True)
                                urls_comp = [ad_urls.get(nm) for nm in top3_comp[col_an]]
                                _podium(list(zip(top3_comp[col_an], top3_comp["__completion__"])),
                                        val_label="% completado", val_fmt="{:.2f}%",
                                        color=GREEN, urls=urls_comp)
                                st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

                        vc1, vc2 = st.columns(2)
                        with vc1:
                            if "__hook_rate__" in df_ag.columns:
                                hr_d = df_ag[[col_an, "__hook_rate__"]].dropna().query("__hook_rate__ > 0")
                                st.plotly_chart(_hbar(hr_d, "__hook_rate__", col_an,
                                    "Hook Rate por anuncio · ↑ mejor",
                                    "Hook: %{x:.2f}%", AMBER, GREEN, xsuffix="%"),
                                    use_container_width=True, config={"displayModeBar":False})
                        with vc2:
                            if "__completion__" in df_ag.columns:
                                comp_d = df_ag[[col_an, "__completion__"]].dropna().query("__completion__ > 0")
                                st.plotly_chart(_hbar(comp_d, "__completion__", col_an,
                                    "Tasa de completado · ↑ mejor",
                                    "Completado: %{x:.2f}%", PURPLE, CYANL, xsuffix="%"),
                                    use_container_width=True, config={"displayModeBar":False})

                        # Retención por hitos (25/50/75/100%) para top 8 anuncios por hook rate
                        ret_cols = [(k, l) for k, l in
                                    [("__ret25__","25%"),("__ret50__","50%"),("__ret75__","75%"),("__ret100__","100%")]
                                    if k in df_ag.columns]
                        if ret_cols:
                            st.markdown('<div class="slabel">% Retención por hito · Top 8 anuncios con más hook</div>', unsafe_allow_html=True)
                            base_col = "__hook_rate__" if "__hook_rate__" in df_ag.columns else col_ar
                            if base_col and base_col in df_ag.columns:
                                top8 = (df_ag[[col_an] + [k for k, _ in ret_cols] + [base_col]]
                                        .dropna(subset=[base_col])
                                        .query(f"`{base_col}` > 0")
                                        .sort_values(base_col, ascending=False)
                                        .head(8))
                                top8_names = top8[col_an].apply(lambda x: _trunc(x, 28))
                                ret_colors = [CYANL, GREEN, AMBER, PINK]
                                fig_ret = go.Figure()
                                for idx_r, (rk_col, rk_lbl) in enumerate(ret_cols):
                                    if rk_col in top8.columns:
                                        fig_ret.add_trace(go.Bar(
                                            name=rk_lbl,
                                            x=top8_names,
                                            y=top8[rk_col],
                                            marker_color=ret_colors[idx_r],
                                            opacity=0.85,
                                            hovertemplate=f"<b>%{{x}}</b><br>{rk_lbl}: %{{y:.1f}}%<extra></extra>"
                                        ))
                                fig_ret.update_layout(**{**BASE_MA, "height": 350},
                                    barmode="group",
                                    title=dict(text="% Retención en cada hito (relativo a vistas 3s)",
                                               font=dict(color=WHITE,size=13,weight=700)),
                                    xaxis=dict(tickfont=dict(color=WHITE,size=8), tickangle=-25),
                                    yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9),
                                               ticksuffix="%", tickformat=".1f"))
                                st.plotly_chart(fig_ret, use_container_width=True, config={"displayModeBar":False})

                        # Embudo global
                        funnel_vals, funnel_lbls = [], []
                        for fc, fl in [(col_avim,"Impresiones"),(col_avpl,"Reproducciones"),
                                       (col_av3,"3 seg · Hook"),(col_avp25,"25% visto"),
                                       (col_avp50,"50% visto"),(col_avp75,"75% visto"),
                                       (col_avp100,"100% visto"),(col_atp,"ThruPlay")]:
                            if fc and fc in df_ag.columns:
                                tv = float(df_ag[fc].sum())
                                if tv > 0: funnel_vals.append(tv); funnel_lbls.append(fl)
                        if len(funnel_vals) >= 3:
                            st.markdown('<div class="slabel">Embudo de retención global · todos los anuncios acumulados</div>', unsafe_allow_html=True)
                            F_COLORS = [PURPLE, PURPLEL, CYANL, CYAN, GREEN, AMBER, PINK, RED]
                            fig_funnel = go.Figure(go.Funnel(
                                y=funnel_lbls, x=funnel_vals,
                                marker=dict(color=F_COLORS[:len(funnel_lbls)]),
                                textfont=dict(color=WHITE, size=11),
                                textinfo="value+percent initial",
                                hovertemplate="<b>%{y}</b><br>%{x:,.0f}<extra></extra>"
                            ))
                            fig_funnel.update_layout(
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(20,25,41,0.6)",
                                font=dict(family="Inter", color=MUTED, size=11),
                                margin=dict(l=10,r=10,t=20,b=10), height=320,
                                hoverlabel=dict(bgcolor=CARD2, font_color=WHITE)
                            )
                            st.plotly_chart(fig_funnel, use_container_width=True, config={"displayModeBar":False})

                    # ── PEORES ───────────────────────────────────────────────
                    if "__cpr__" in df_ag.columns:
                        st.markdown('<div class="slabel">⚠️ Mayor CPR · Candidatos a revisar o pausar</div>', unsafe_allow_html=True)
                        worst = (df_ag[[col_an, "__cpr__"]].dropna()
                                 .query("__cpr__ > 0")
                                 .sort_values("__cpr__", ascending=False).head(8)).copy()
                        worst[col_an] = worst[col_an].apply(lambda x: _trunc(x, 40))
                        fig_worst = go.Figure(go.Bar(
                            x=worst["__cpr__"], y=worst[col_an], orientation="h",
                            marker=dict(color=PINK, opacity=0.85),
                            hovertemplate="<b>%{y}</b><br>CPR: $%{x:,.0f}<extra></extra>"
                        ))
                        fig_worst.update_layout(**{**BASE_MA, "height": 270},
                            title=dict(text="Anuncios con mayor Costo por Resultado", font=dict(color=WHITE,size=13,weight=700)),
                            xaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9)),
                            yaxis=dict(tickfont=dict(color=WHITE,size=9)))
                        st.plotly_chart(fig_worst, use_container_width=True, config={"displayModeBar":False})

        # ── DIAGNÓSTICO ───────────────────────────────────────────────────────
        with ma5:
            def _safe_chg(nv, ov):
                try:
                    nv, ov = float(nv), float(ov)
                    if np.isnan(nv) or np.isnan(ov) or ov == 0: return np.nan
                    return (nv - ov) / ov * 100
                except Exception: return np.nan

            def _insight_card(title, body, accion, color, priority_lbl):
                st.markdown(f"""
<div style="background:{CARD2};border-left:4px solid {color};border-radius:12px;
  padding:.85rem 1.1rem;margin-bottom:.6rem">
  <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem">
    <span style="background:{color}22;color:{color};font-size:.62rem;font-weight:800;
      letter-spacing:.06em;padding:.15rem .5rem;border-radius:20px">{priority_lbl}</span>
    <span style="color:{WHITE};font-size:.82rem;font-weight:700">{title}</span>
  </div>
  <div style="color:{MUTED};font-size:.76rem;line-height:1.7;margin-bottom:.4rem">{body}</div>
  <div style="background:{color}18;border-radius:8px;padding:.4rem .7rem">
    <span style="color:{color};font-size:.72rem;font-weight:700">→ Acción: </span>
    <span style="color:{WHITE};font-size:.72rem">{accion}</span>
  </div>
</div>""", unsafe_allow_html=True)

            alta:    list = []  # (title, body, accion)
            import_: list = []
            sugier:  list = []

            # ── Ganadores ────────────────────────────────────────────────────
            st.markdown('<div class="slabel">🏆 Ganadores acumulados</div>', unsafe_allow_html=True)
            win_cols_ui = st.columns(3)
            win_best = {}
            for wi, (rk, lbl, clr) in enumerate([
                ("campaign","🎯 Mejor Campaña", PURPLE),
                ("adset",   "👥 Mejor Público",  CYANL),
                ("ad",      "🎨 Mejor Anuncio",  GREEN)
            ]):
                rk_reps = [r for r in reports if r["cols"].get(rk)]
                if rk_reps:
                    df_rk = pd.concat([r["df"] for r in rk_reps], ignore_index=True)
                    c_nm = rk_reps[0]["cols"].get(rk); c_rs = rk_reps[0]["cols"].get("results")
                    if c_nm and c_rs and c_rs in df_rk.columns:
                        grp = df_rk.groupby(c_nm)[c_rs].sum()
                        bn  = _trunc(str(grp.idxmax()), 38); bv = int(grp.max())
                        win_best[rk] = (str(grp.idxmax()), bv)
                        win_cols_ui[wi].markdown(f"""
<div style="background:{CARD2};border:1px solid {clr}44;border-radius:14px;
  padding:1rem .9rem;text-align:center">
  <div style="font-size:.76rem;color:{MUTED};margin-bottom:.3rem">{lbl}</div>
  <div style="color:{WHITE};font-size:.74rem;font-weight:600;line-height:1.5;
    min-height:3rem;display:flex;align-items:center;justify-content:center">{bn}</div>
  <div style="color:{clr};font-size:1.15rem;font-weight:800;margin-top:.5rem">{bv:,}</div>
  <div style="color:{MUTED};font-size:.64rem">resultados totales</div>
</div>""", unsafe_allow_html=True)
                    else:
                        win_cols_ui[wi].markdown(f'<div style="color:{MUTED};font-size:.75rem">Sin datos</div>', unsafe_allow_html=True)
                else:
                    win_cols_ui[wi].markdown(f'<div style="color:{MUTED};font-size:.75rem">Sin datos</div>', unsafe_allow_html=True)

            st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

            # ── Mapa de eficiencia (treemap) ──────────────────────────────────
            _, c0q, df_q = _build_agg([r for r in reports if r["cols"].get("campaign")], "campaign")
            if df_q is not None and c0q and c0q.get("results") and "__cpr__" in df_q.columns:
                col_qn = c0q.get("campaign"); col_qr = c0q.get("results"); col_qs = c0q.get("spend")
                q_data = (df_q[[col_qn, col_qr, "__cpr__"] +
                                ([col_qs] if col_qs and col_qs in df_q.columns else [])]
                           .dropna(subset=[col_qn, col_qr, "__cpr__"])
                           .query(f"`{col_qr}` > 0 and __cpr__ > 0")
                           .sort_values(col_qr, ascending=False).head(15))
                if len(q_data) >= 2:
                    st.markdown('<div class="slabel">📊 Mapa de eficiencia · Campañas (área = resultados · color = CPR)</div>', unsafe_allow_html=True)
                    # Normalizar CPR para colorscale (0=mejor/verde, 1=peor/rojo)
                    cpr_min = float(q_data["__cpr__"].min())
                    cpr_max = float(q_data["__cpr__"].max())
                    cpr_norm = ((q_data["__cpr__"] - cpr_min) / (cpr_max - cpr_min + 1)).fillna(0)
                    spend_vals = (q_data[col_qs].values if col_qs and col_qs in q_data.columns
                                  else q_data[col_qr].values)
                    labels_tm = q_data[col_qn].apply(lambda x: _trunc(x, 24))
                    fig_tm = go.Figure(go.Treemap(
                        labels=labels_tm,
                        parents=[""] * len(q_data),
                        values=q_data[col_qr].values,
                        customdata=list(zip(
                            q_data[col_qr].values,
                            q_data["__cpr__"].values,
                            spend_vals
                        )),
                        marker=dict(
                            colors=cpr_norm.values,
                            colorscale=[[0, GREEN], [0.45, AMBER], [1, PINK]],
                            showscale=True,
                            colorbar=dict(
                                title=dict(text="CPR →", font=dict(color=MUTED, size=10)),
                                tickvals=[0, 0.5, 1],
                                ticktext=["Bajo", "Medio", "Alto"],
                                tickfont=dict(color=MUTED, size=9),
                                thickness=10, len=0.6
                            )
                        ),
                        texttemplate=(
                            "<b>%{label}</b><br>"
                            "%{customdata[0]:,.0f} resultados<br>"
                            "CPR $%{customdata[1]:,.0f}"
                        ),
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "Resultados: %{customdata[0]:,.0f}<br>"
                            "CPR: $%{customdata[1]:,.0f}<br>"
                            "Gasto: $%{customdata[2]:,.0f}"
                            "<extra></extra>"
                        ),
                        textfont=dict(color=WHITE, size=11),
                        tiling=dict(packing="squarify", pad=3),
                    ))
                    fig_tm.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=0, r=0, t=10, b=0), height=380,
                        font=dict(family="Inter", color=MUTED),
                        hoverlabel=dict(bgcolor=CARD2, font_color=WHITE, font_size=12)
                    )
                    st.plotly_chart(fig_tm, use_container_width=True, config={"displayModeBar":False})
                    st.markdown(
                        f'<div style="color:{MUTED};font-size:.7rem;text-align:right;margin-top:-.4rem">'
                        f'Verde = CPR bajo (eficiente) &nbsp;·&nbsp; Rojo = CPR alto (revisar) &nbsp;·&nbsp; '
                        f'Área = cantidad de resultados</div>',
                        unsafe_allow_html=True)

            # ── Recopilación de insights ──────────────────────────────────────
            if "df_mon" not in dir() or df_mon is None or df_mon.empty:
                monthly_d: list = []
                for r in sorted(reports, key=lambda x: x.get("month","")):
                    c = r["cols"]; df_r = r["df"]
                    sp = float(df_r[c["spend"]].sum())   if c.get("spend")   else np.nan
                    rs = float(df_r[c["results"]].sum()) if c.get("results") else np.nan
                    cp = float(df_r[c["cpr"]].mean())    if c.get("cpr")     else (sp/rs if rs else np.nan)
                    ct = float(df_r[c["ctr"]].mean())    if c.get("ctr")     else np.nan
                    monthly_d.append({"Mes": r.get("month_label",""), "MesKey": r.get("month",""),
                                      "Inversión": sp, "Resultados": rs, "CPR": cp, "CTR": ct})
                df_mon = pd.DataFrame(monthly_d).sort_values("MesKey").reset_index(drop=True)

            if len(df_mon) >= 2:
                last_m = df_mon.iloc[-1]; prev_m = df_mon.iloc[-2]
                cpr_chg = _safe_chg(last_m["CPR"], prev_m["CPR"])
                res_chg = _safe_chg(last_m["Resultados"], prev_m["Resultados"])
                ctr_chg = _safe_chg(last_m["CTR"], prev_m["CTR"])

                if not np.isnan(cpr_chg):
                    if cpr_chg > 20:
                        alta.append((
                            f"CPR se disparó +{cpr_chg:.0f}%",
                            f"Subió de {fmt_cop(prev_m['CPR'])} a {fmt_cop(last_m['CPR'])} entre {prev_m['Mes']} y {last_m['Mes']}. "
                            f"El costo por resultado está en niveles críticos.",
                            f"Pausa hoy los 2 anuncios con mayor CPR. Activa una copia del mejor anuncio del mes anterior."))
                    elif cpr_chg > 10:
                        import_.append((
                            f"CPR subiendo +{cpr_chg:.0f}%",
                            f"El CPR pasó de {fmt_cop(prev_m['CPR'])} a {fmt_cop(last_m['CPR'])}. Tendencia negativa.",
                            f"Identifica qué anuncios empujaron el costo hacia arriba y ajusta presupuesto hacia los más eficientes."))
                    elif cpr_chg < -10:
                        sugier.append((
                            f"CPR bajando {abs(cpr_chg):.0f}% — buena señal",
                            f"El CPR mejoró de {fmt_cop(prev_m['CPR'])} a {fmt_cop(last_m['CPR'])}. "
                            f"La optimización está funcionando.",
                            f"Escala el presupuesto en las campañas con mejor CPR para aprovechar el momento."))

                if not np.isnan(res_chg):
                    if res_chg < -15:
                        alta.append((
                            f"Resultados cayendo {abs(res_chg):.0f}%",
                            f"Bajaron de {int(prev_m['Resultados']):,} a {int(last_m['Resultados']):,} leads. Caída significativa.",
                            f"Revisa si la página de destino funciona, si las audiencias están saturadas y si los creativos siguen siendo relevantes."))
                    elif res_chg < -5:
                        import_.append((
                            f"Resultados bajando {abs(res_chg):.0f}%",
                            f"De {int(prev_m['Resultados']):,} a {int(last_m['Resultados']):,} leads entre {prev_m['Mes']} y {last_m['Mes']}.",
                            f"Prueba nuevos creativos y amplía el público objetivo para recuperar volumen."))
                    elif res_chg > 10:
                        sugier.append((
                            f"Resultados creciendo +{res_chg:.0f}%",
                            f"Subieron de {int(prev_m['Resultados']):,} a {int(last_m['Resultados']):,}. Muy buena tendencia.",
                            f"Identifica qué campaña o creativo está impulsando el crecimiento y asígnale más presupuesto."))

                if not np.isnan(ctr_chg) and ctr_chg < -20:
                    alta.append((
                        "Fatiga creativa severa",
                        f"El CTR cayó {abs(ctr_chg):.0f}% ({prev_m['CTR']:.2f}% → {last_m['CTR']:.2f}%). "
                        "La audiencia ya no reacciona a los anuncios actuales.",
                        "Renueva el 100% de los creativos activos. Prueba nuevos hooks, formatos y mensajes."))
                elif not np.isnan(ctr_chg) and ctr_chg < -10:
                    import_.append((
                        f"CTR cayendo {abs(ctr_chg):.0f}%",
                        f"Bajó de {prev_m['CTR']:.2f}% a {last_m['CTR']:.2f}%. Señal de desgaste de creativos.",
                        "Introduce 2-3 nuevas variantes creativas. Prioriza los hooks que mejor funcionaron."))

            # Alerta frecuencia alta
            for r in reports:
                c = r["cols"]; df_r = r["df"]
                if c.get("frequency") and c["frequency"] in df_r.columns:
                    avg_freq = float(df_r[c["frequency"]].mean())
                    if avg_freq > 4:
                        alta.append((
                            f"Frecuencia crítica · {r.get('month_label','')} ({avg_freq:.1f}x)",
                            f"La audiencia ve tus anuncios en promedio {avg_freq:.1f} veces. Saturación alta.",
                            "Amplía el público objetivo mínimo en un 30%, agrega exclusiones o cambia los creativos esta semana."))
                    elif avg_freq > 3:
                        import_.append((
                            f"Frecuencia alta · {r.get('month_label','')} ({avg_freq:.1f}x)",
                            f"Frecuencia promedio de {avg_freq:.1f}. Riesgo de fatiga de audiencia.",
                            "Considera rotar creativos o ampliar el público para que la frecuencia no suba más."))
                    break

            # Alerta peor anuncio por CPR
            _, c0alrt, df_alrt = _build_agg([r for r in reports if r["cols"].get("ad")], "ad")
            if df_alrt is not None and "__cpr__" in df_alrt.columns and c0alrt:
                col_alrt_n = c0alrt.get("ad")
                worst_alrt = (df_alrt[[col_alrt_n, "__cpr__", c0alrt.get("results","__dummy__") or "__cpr__"]]
                               .dropna(subset=[col_alrt_n, "__cpr__"])
                               .query("__cpr__ > 0")
                               .sort_values("__cpr__", ascending=False).head(1))
                if not worst_alrt.empty:
                    wn = _trunc(str(worst_alrt.iloc[0][col_alrt_n]), 50)
                    wc = worst_alrt.iloc[0]["__cpr__"]
                    # Compare to average CPR
                    avg_cpr_ad = float(df_alrt["__cpr__"].mean())
                    if wc > avg_cpr_ad * 2:
                        import_.append((
                            "Anuncio con CPR fuera de rango",
                            f"'{wn}' tiene un CPR de {fmt_cop(wc)}, más del doble del promedio ({fmt_cop(avg_cpr_ad)}).",
                            f"Pausa este anuncio o actualiza su creativo. Redistribuye su presupuesto al mejor anuncio."))

            # Sugerencia hook rate bajo
            if df_alrt is not None and "__hook_rate__" in df_alrt.columns and c0alrt:
                col_alrt_n = c0alrt.get("ad")
                avg_hook = float(df_alrt["__hook_rate__"].mean())
                if avg_hook < 3:
                    sugier.append((
                        f"Hook Rate promedio bajo ({avg_hook:.1f}%)",
                        "Menos del 3% de las personas que ven tus anuncios los reproducen por 3 segundos.",
                        "Prueba hooks más directos: pregunta al espectador algo, usa texto grande en los primeros 2s, o empieza con el resultado que ofreces."))
                elif avg_hook < 6:
                    sugier.append((
                        f"Hook Rate puede mejorar ({avg_hook:.1f}%)",
                        "Un Hook Rate entre 3-6% es aceptable pero hay margen de mejora.",
                        "Toma los 3 mejores hooks y prueba variantes. Cambia el primer frame o el primer mensaje."))

            # Sugerencia completado bajo
            if df_alrt is not None and "__completion__" in df_alrt.columns:
                avg_comp = float(df_alrt["__completion__"].mean())
                if avg_comp < 20:
                    sugier.append((
                        f"Tasa de completado baja ({avg_comp:.1f}%)",
                        "Solo 1 de cada 5 personas que ven los primeros 3s terminan el video.",
                        "Acorta los videos a menos de 30s. Coloca el mensaje clave antes del segundo 10."))

            # Eficiencia global
            if all_spend > 0 and all_results > 0:
                sugier.append((
                    "Resumen de eficiencia histórica",
                    f"Total invertido: {fmt_cop(all_spend)} · {int(all_results):,} resultados · "
                    f"CPR histórico: {fmt_cop(all_spend/all_results)} · {n_meses} mes(es) analizados.",
                    "Usa este CPR como benchmark. Cualquier campaña por encima de este valor merece atención."))

            # ── Render por prioridades ────────────────────────────────────────
            if not alta and not import_ and not sugier:
                st.info("Sube más reportes para generar diagnósticos automáticos.")
            else:
                if alta:
                    st.markdown(f"""
<div style="background:{RED}18;border:1px solid {RED}55;border-radius:10px;
  padding:.5rem 1rem;margin:.8rem 0 .4rem 0">
  <span style="color:{RED};font-size:.8rem;font-weight:800">🚨 PRIORIDAD ALTA — Actuar hoy</span>
</div>""", unsafe_allow_html=True)
                    for t, b, a in alta:
                        _insight_card(t, b, a, RED, "🚨 URGENTE")

                if import_:
                    st.markdown(f"""
<div style="background:{AMBER}18;border:1px solid {AMBER}55;border-radius:10px;
  padding:.5rem 1rem;margin:.8rem 0 .4rem 0">
  <span style="color:{AMBER};font-size:.8rem;font-weight:800">⚡ IMPORTANTE — Esta semana</span>
</div>""", unsafe_allow_html=True)
                    for t, b, a in import_:
                        _insight_card(t, b, a, AMBER, "⚡ ESTA SEMANA")

                if sugier:
                    st.markdown(f"""
<div style="background:{CYANL}18;border:1px solid {CYANL}55;border-radius:10px;
  padding:.5rem 1rem;margin:.8rem 0 .4rem 0">
  <span style="color:{CYANL};font-size:.8rem;font-weight:800">💡 SUGERENCIAS — Cuando puedas</span>
</div>""", unsafe_allow_html=True)
                    for t, b, a in sugier:
                        _insight_card(t, b, a, CYANL, "💡 SUGERENCIA")

    else:
        st.markdown(f"""
<div style="background:{CARD};border:2px dashed {BORDER};border-radius:16px;
  padding:1.8rem;text-align:center;margin-top:.3rem">
  <div style="font-size:2rem;margin-bottom:.5rem">📊</div>
  <div style="color:{WHITE};font-weight:700;font-size:.95rem;margin-bottom:.5rem">
    Sube tu primer reporte de Meta Ads Manager</div>
  <div style="color:{MUTED};font-size:.78rem;line-height:2">
    1 · <strong style="color:{CYANL}">Administrador de Anuncios</strong> → ajusta período y nivel<br>
    2 · Nivel: <strong style="color:{CYANL}">Campañas / Públicos / Anuncios</strong><br>
    3 · <strong style="color:{CYANL}">Exportar → CSV</strong> · Sube un reporte por mes
  </div>
</div>
""", unsafe_allow_html=True)

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
        df_growth      = tg.get("df_growth", pd.DataFrame())
        growth_error   = tg.get("growth_error", "")
        has_gross_data = tg.get("has_gross_data", False)

        BASE_TG = dict(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(20,25,41,0.6)",
            font=dict(family="Inter", color=MUTED, size=11),
            margin=dict(l=10, r=10, t=55, b=10), height=320,
            hoverlabel=dict(bgcolor=CARD2, font_color=WHITE),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        font=dict(color=MUTED, size=10), bgcolor="rgba(0,0,0,0)")
        )

        # ── KPIs principales ──────────────────────────────────────────────────
        total_posts = len(df_msg) if not df_msg.empty else 0
        avg_vistas  = int(df_msg["vistas"].mean())    if not df_msg.empty else 0
        max_vistas  = int(df_msg["vistas"].max())     if not df_msg.empty else 0
        avg_react   = round(df_msg["reacciones"].mean(), 1) if not df_msg.empty and "reacciones" in df_msg.columns else 0

        sub_prev = stats.get("subs_anterior")
        sub_curr = stats.get("subs_actual", subs)
        crecim_txt = (f"{'+'if (sub_curr-sub_prev)>=0 else ''}{(sub_curr-sub_prev):,} vs período anterior"
                      if sub_prev and sub_curr else "")

        tk1, tk2, tk3, tk4 = st.columns(4)
        tk1.markdown(kcard("Suscriptores",    fmt_num(subs),              "pu","pu", sub=crecim_txt), unsafe_allow_html=True)
        tk2.markdown(kcard("Posts analizados",fmt_num(total_posts),        "plain"),  unsafe_allow_html=True)
        tk3.markdown(kcard("Vistas promedio", fmt_num(avg_vistas),         "cy","cy"), unsafe_allow_html=True)
        tk4.markdown(kcard("Mejor post",      fmt_num(max_vistas)+" 👁",   "gn","gn"), unsafe_allow_html=True)

        if not df_msg.empty:
            st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

            # ── GRÁFICA PRINCIPAL: vistas con área ────────────────────────────
            st.markdown('<div class="slabel">📈 Evolución de vistas por publicación</div>', unsafe_allow_html=True)
            df_plot = df_msg.sort_values("fecha").tail(80)
            fig_area = go.Figure()
            fig_area.add_trace(go.Scatter(
                x=df_plot["fecha"], y=df_plot["vistas"],
                name="Vistas", mode="lines",
                line=dict(color=PURPLEL, width=0),
                fill="tozeroy", fillcolor="rgba(124,58,237,0.25)",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.0f} vistas<extra></extra>"
            ))
            fig_area.add_trace(go.Scatter(
                x=df_plot["fecha"], y=df_plot["vistas"],
                name="Vistas", mode="lines",
                line=dict(color=PURPLEL, width=2),
                showlegend=False,
                hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.0f} vistas<extra></extra>"
            ))
            rolling = df_plot["vistas"].rolling(7, min_periods=1).mean()
            fig_area.add_trace(go.Scatter(
                x=df_plot["fecha"], y=rolling,
                name="Media 7 posts", mode="lines",
                line=dict(color=CYANL, width=2, dash="dot"),
                hovertemplate="Media: %{y:.0f}<extra></extra>"
            ))
            avg_line = float(df_plot["vistas"].mean())
            fig_area.add_hline(y=avg_line, line_color=MUTED2, line_width=1, line_dash="dot",
                annotation_text=f"Promedio {avg_line:,.0f}", annotation_font_color=MUTED,
                annotation_position="bottom right")
            fig_area.update_layout(**{**BASE_TG, "height": 280},
                title=dict(text="Vistas · últimos 80 posts", font=dict(color=WHITE,size=13,weight=700)),
                xaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9), showgrid=False),
                yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9), showgrid=True),
                hovermode="x unified")
            st.plotly_chart(fig_area, use_container_width=True, config={"displayModeBar":False})

            # ── TOP POSTS — CARDS VISUALES ────────────────────────────────────
            st.markdown('<div class="slabel">🏆 Top posts por vistas</div>', unsafe_allow_html=True)
            df_top = df_msg.nlargest(8, "vistas").reset_index(drop=True)
            max_v  = float(df_top["vistas"].iloc[0]) if not df_top.empty else 1
            medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣"]
            mc_colors = [AMBER,"#C0C0C0","#CD7F32",MUTED,MUTED,MUTED,MUTED,MUTED]

            cards_html = ""
            for idx, row in df_top.iterrows():
                txt = str(row.get("texto","") or "").strip()
                if txt:
                    excerpt_raw = txt[:120] + ("…" if len(txt) >= 120 else "")
                elif row.get("tiene_media", False):
                    excerpt_raw = "📷  Post multimedia sin texto"
                else:
                    excerpt_raw = f"💬  Post #{row.get('id','')}"
                excerpt   = _html.escape(excerpt_raw)
                fecha_str = _html.escape(row["fecha"].strftime("%d %b %Y") if pd.notna(row["fecha"]) else "—")
                vistas_v  = int(row["vistas"])
                react_v   = int(row.get("reacciones", 0)) if pd.notna(row.get("reacciones", 0)) else 0
                bar_pct   = max(2, int(vistas_v / max_v * 100))
                medal  = medals[idx]
                accent = AMBER if idx == 0 else (MUTED2 if idx > 2 else BORDER)
                react_span = f'<span style="color:{PINK};font-size:.8rem;font-weight:700">❤️&nbsp;{react_v}</span>' if react_v else ""
                cards_html += (
                    f'<div style="background:{CARD2};border:1px solid {accent};border-radius:14px;padding:.85rem 1.1rem;margin-bottom:.6rem">'
                    f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.45rem">'
                    f'<div style="display:flex;align-items:center;gap:.55rem">'
                    f'<span style="font-size:1.1rem">{medal}</span>'
                    f'<span style="color:{MUTED};font-size:.72rem">📅&nbsp;{fecha_str}</span>'
                    f'</div>'
                    f'<div style="display:flex;gap:.9rem;align-items:center">'
                    f'<span style="color:{PURPLEL};font-weight:800;font-size:.9rem">👁&nbsp;{vistas_v:,}</span>'
                    f'{react_span}'
                    f'</div>'
                    f'</div>'
                    f'<div style="color:{WHITE};font-size:.78rem;line-height:1.55;margin-bottom:.5rem">{excerpt}</div>'
                    f'<div style="background:{BORDER};border-radius:4px;height:4px;overflow:hidden">'
                    f'<div style="background:linear-gradient(90deg,{PURPLE},{CYANL});width:{bar_pct}%;height:100%;border-radius:4px"></div>'
                    f'</div>'
                    f'</div>'
                )
            st.markdown(cards_html, unsafe_allow_html=True)

            # ── DOS COLUMNAS: Actividad semanal + Dispersión vistas/reacciones ─
            st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown('<div class="slabel">📅 Actividad semanal</div>', unsafe_allow_html=True)
                if "semana" in df_msg.columns:
                    df_sem = (df_msg.groupby("semana")
                              .agg(posts=("id","count"), vistas=("vistas","sum"),
                                   avg_v=("vistas","mean"))
                              .reset_index())
                    df_sem["semana"] = pd.to_datetime(df_sem["semana"])
                    fig_sem = make_subplots(specs=[[{"secondary_y": True}]])
                    fig_sem.add_trace(go.Bar(
                        x=df_sem["semana"], y=df_sem["vistas"], name="Vistas",
                        marker=dict(color=PURPLE, opacity=0.8),
                        hovertemplate="%{x|%d/%m}<br><b>%{y:,.0f} vistas</b><extra></extra>"
                    ), secondary_y=False)
                    fig_sem.add_trace(go.Scatter(
                        x=df_sem["semana"], y=df_sem["posts"], name="Posts",
                        mode="lines+markers",
                        line=dict(color=CYANL, width=2),
                        marker=dict(size=5, color=CYANL),
                        hovertemplate="%{x|%d/%m}<br><b>%{y} posts</b><extra></extra>"
                    ), secondary_y=True)
                    fig_sem.update_layout(
                        **{k:v for k,v in BASE_TG.items() if k not in ("height",)},
                        height=280,
                        title=dict(text="Vistas y posts por semana", font=dict(color=WHITE,size=12,weight=700)))
                    fig_sem.update_xaxes(gridcolor=BORDER, tickfont=dict(color=MUTED,size=8))
                    fig_sem.update_yaxes(gridcolor=BORDER, tickfont=dict(color=MUTED,size=8), secondary_y=False)
                    fig_sem.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=CYANL,size=8), secondary_y=True)
                    st.plotly_chart(fig_sem, use_container_width=True, config={"displayModeBar":False})

            with col_right:
                st.markdown('<div class="slabel">💬 Vistas vs Reacciones</div>', unsafe_allow_html=True)
                if "reacciones" in df_msg.columns:
                    df_sc = df_msg.dropna(subset=["vistas","reacciones"]).copy()
                    df_sc = df_sc[df_sc["reacciones"] >= 0]
                    txt_sc = df_sc.apply(lambda r: (str(r.get("texto",""))[:40] or f"Post {r.get('id','')}"), axis=1)
                    fig_sc = go.Figure(go.Scatter(
                        x=df_sc["vistas"], y=df_sc["reacciones"],
                        mode="markers", text=txt_sc,
                        marker=dict(
                            size=9, opacity=0.75,
                            color=df_sc["vistas"].values,
                            colorscale=[[0,PURPLE],[0.5,PURPLEL],[1,CYANL]],
                            line=dict(width=0.5, color=BORDER)
                        ),
                        hovertemplate="<b>%{text}</b><br>👁 %{x:,.0f} vistas<br>❤️ %{y} reacciones<extra></extra>"
                    ))
                    fig_sc.update_layout(
                        **{k:v for k,v in BASE_TG.items() if k not in ("height","hovermode")},
                        height=280,
                        title=dict(text="¿Más vistas = más reacciones?", font=dict(color=WHITE,size=12,weight=700)),
                        xaxis=dict(title=dict(text="Vistas", font=dict(color=MUTED,size=9)),
                                   gridcolor=BORDER, tickfont=dict(color=MUTED,size=8)),
                        yaxis=dict(title=dict(text="Reacciones", font=dict(color=MUTED,size=9)),
                                   gridcolor=BORDER, tickfont=dict(color=MUTED,size=8)),
                        hovermode="closest"
                    )
                    st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar":False})

            # ── CRECIMIENTO ───────────────────────────────────────────────────
            st.markdown(f'<div style="border-top:1px solid {BORDER};margin:1rem 0 .6rem 0"></div>', unsafe_allow_html=True)
            st.markdown('<div class="slabel">👥 Crecimiento de suscriptores</div>', unsafe_allow_html=True)

            if df_growth.empty:
                st.markdown(f"""
<div style="background:{CARD};border:1px dashed {BORDER};border-radius:12px;
  padding:1.2rem;text-align:center">
  <div style="color:{MUTED};font-size:.8rem;line-height:1.8">
    Datos de crecimiento no disponibles.<br>
    El canal necesita <strong style="color:{CYANL}">+500 suscriptores</strong>
    y permiso de admin <strong style="color:{CYANL}">Ver estadísticas</strong>.
  </div>
</div>""", unsafe_allow_html=True)
            else:
                gmin = df_growth["fecha"].dt.date.min()
                gmax = df_growth["fecha"].dt.date.max()

                dg = df_growth.copy()

                neto    = int(dg["net"].sum()) if "net" in dg.columns else int((dg["entradas"]-dg["salidas"]).sum())
                sub_fin = int(dg["miembros"].iloc[-1]) if not dg.empty else subs

                if has_gross_data:
                    total_ent = int(dg["entradas"].sum()); total_sal = int(dg["salidas"].sum())
                    gk1,gk2,gk3,gk4 = st.columns(4)
                    gk1.markdown(kcard("Suscriptores cierre", fmt_num(sub_fin), "pu","pu"), unsafe_allow_html=True)
                    gk2.markdown(kcard("Entradas", f"+{fmt_num(total_ent)}", "gn","gn"), unsafe_allow_html=True)
                    gk3.markdown(kcard("Salidas",  f"-{fmt_num(total_sal)}", "pk","pk"), unsafe_allow_html=True)
                    gk4.markdown(kcard("Crecimiento neto", f"{'+'if neto>=0 else ''}{fmt_num(neto)}",
                                       "cy" if neto>=0 else "pk", "cy" if neto>=0 else "pk"), unsafe_allow_html=True)
                else:
                    dias_pos = int((dg["net"] > 0).sum()) if "net" in dg.columns else 0
                    dias_neg = int((dg["net"] < 0).sum()) if "net" in dg.columns else 0
                    gk1,gk2,gk3,gk4 = st.columns(4)
                    gk1.markdown(kcard("Suscriptores cierre", fmt_num(sub_fin), "pu","pu"), unsafe_allow_html=True)
                    gk2.markdown(kcard("Crecimiento neto", f"{'+'if neto>=0 else ''}{fmt_num(neto)}",
                                       "gn" if neto>=0 else "pk", "gn" if neto>=0 else "pk"), unsafe_allow_html=True)
                    gk3.markdown(kcard("Días con crecimiento", fmt_num(dias_pos), "cy","cy"), unsafe_allow_html=True)
                    gk4.markdown(kcard("Días con pérdida", fmt_num(dias_neg), "plain"), unsafe_allow_html=True)

                st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
                gcol1, gcol2 = st.columns(2)

                with gcol1:
                    fig_g1 = go.Figure()
                    fig_g1.add_trace(go.Scatter(
                        x=dg["fecha"], y=dg["miembros"], name="Miembros",
                        mode="lines",
                        line=dict(color=PURPLEL, width=2),
                        fill="tozeroy", fillcolor="rgba(168,85,247,0.15)",
                        hovertemplate="%{x|%d/%m/%Y}<br><b>%{y:,.0f} suscriptores</b><extra></extra>"
                    ))
                    fig_g1.update_layout(**{**BASE_TG, "height": 260},
                        title=dict(text="Evolución de suscriptores", font=dict(color=WHITE,size=12,weight=700)),
                        xaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=8), showgrid=False),
                        yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=8)),
                        hovermode="x unified")
                    st.plotly_chart(fig_g1, use_container_width=True, config={"displayModeBar":False})

                with gcol2:
                    fig_g2 = go.Figure()
                    if has_gross_data:
                        fig_g2.add_trace(go.Bar(x=dg["fecha"], y=dg["entradas"], name="Entradas",
                            marker=dict(color=GREEN, opacity=0.85),
                            hovertemplate="%{x|%d/%m}<br><b>+%{y}</b><extra></extra>"))
                        fig_g2.add_trace(go.Bar(x=dg["fecha"], y=-dg["salidas"], name="Salidas",
                            marker=dict(color=RED, opacity=0.85),
                            hovertemplate="%{x|%d/%m}<br><b>-%{y}</b><extra></extra>"))
                        g2t = "Entradas y salidas diarias"
                    else:
                        net_col = dg["net"] if "net" in dg.columns else (dg["entradas"]-dg["salidas"])
                        fig_g2.add_trace(go.Bar(x=dg["fecha"], y=net_col, name="Neto",
                            marker=dict(color=[GREEN if v>=0 else RED for v in net_col], opacity=0.85),
                            hovertemplate="%{x|%d/%m}<br><b>%{y:+d}</b><extra></extra>"))
                        fig_g2.add_hline(y=0, line_color=MUTED2, line_width=1)
                        g2t = "Cambio neto diario"
                    fig_g2.update_layout(**{**BASE_TG, "height": 260}, barmode="relative",
                        title=dict(text=g2t, font=dict(color=WHITE,size=12,weight=700)),
                        xaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=8), showgrid=False),
                        yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=8),
                                   zeroline=True, zerolinecolor=MUTED2),
                        hovermode="x unified")
                    st.plotly_chart(fig_g2, use_container_width=True, config={"displayModeBar":False})

                with st.expander("Ver detalle diario"):
                    if has_gross_data:
                        tbl_g = dg[["fecha","miembros","entradas","salidas"]].copy()
                        tbl_g["fecha"] = tbl_g["fecha"].dt.strftime("%d/%m/%Y")
                        tbl_g.columns = ["Fecha","Miembros","Entradas","Salidas"]
                    else:
                        net_col2 = dg["net"] if "net" in dg.columns else (dg["entradas"]-dg["salidas"])
                        tbl_g = dg[["fecha","miembros"]].copy()
                        tbl_g["neto"] = net_col2.values
                        tbl_g["fecha"] = tbl_g["fecha"].dt.strftime("%d/%m/%Y")
                        tbl_g.columns = ["Fecha","Miembros","Neto"]
                    st.dataframe(tbl_g.set_index("Fecha"), use_container_width=True)

        # ── STATS AVANZADAS ───────────────────────────────────────────────────
        if stats:
            st.markdown(f'<div style="border-top:1px solid {BORDER};margin:.8rem 0 .5rem 0"></div>', unsafe_allow_html=True)
            st.markdown('<div class="slabel">📊 Estadísticas avanzadas</div>', unsafe_allow_html=True)
            sa1, sa2, sa3 = st.columns(3)
            sa1.markdown(kcard("Suscriptores actuales", fmt_num(stats.get("subs_actual", subs)), "pu","pu"), unsafe_allow_html=True)
            sa2.markdown(kcard("Suscriptores anterior", fmt_num(stats.get("subs_anterior",0)), "plain"), unsafe_allow_html=True)
            sa3.markdown(kcard("Vistas prom./post",     str(stats.get("vistas_post","—")), "cy","cy"), unsafe_allow_html=True)

# ── PESTAÑA IA (análisis algorítmico) ────────────────────────────────────────
def _build_ia_context(reports, tg_data):  # kept for potential future use
    """Construye un resumen de datos para enviar a Claude."""
    lines = []

    # ── META ADS ──────────────────────────────────────────────────────────────
    if reports:
        lines.append("=== META ADS ===")
        for r in reports:
            df_r = r["df"]; c = r["cols"]
            lines.append(f"\nReporte: {r['name']}")
            if r.get("date_start"): lines.append(f"Período: {r['date_start']} → {r['date_end']}")

            def _col_sum(k):
                col = c.get(k)
                return float(df_r[col].sum()) if col and col in df_r.columns else 0.0
            def _col_mean(k):
                col = c.get(k)
                return float(df_r[col].mean()) if col and col in df_r.columns else 0.0

            spend    = _col_sum("spend")
            results  = _col_sum("results")
            cpr      = spend / results if results > 0 else 0
            ctr      = _col_mean("ctr")
            impr     = _col_sum("impressions")
            freq     = _col_mean("frequency")
            v3s      = _col_sum("video_3s")
            hook_r   = (v3s / impr * 100) if impr > 0 else 0
            v100     = _col_sum("video_p100")
            compl    = (v100 / v3s * 100) if v3s > 0 else 0

            lines.append(f"Inversión total: ${spend:,.0f}")
            lines.append(f"Resultados: {results:,.0f} | CPR: ${cpr:,.0f} | CTR: {ctr:.2f}%")
            lines.append(f"Impresiones: {impr:,.0f} | Frecuencia: {freq:.1f}")
            if hook_r: lines.append(f"Hook rate promedio: {hook_r:.1f}% | Tasa completación video: {compl:.1f}%")

            # Top campañas
            if c.get("campaign") and c["campaign"] in df_r.columns:
                agg = df_r.groupby(c["campaign"]).agg(
                    spend=(c["spend"], "sum"), results=(c["results"], "sum")
                ).assign(cpr=lambda x: x["spend"] / x["results"].replace(0, np.nan))
                top3 = agg.nsmallest(3, "cpr")
                lines.append("Top 3 campañas (menor CPR):")
                for nm, row in top3.iterrows():
                    lines.append(f"  • {str(nm)[:60]}: CPR ${row['cpr']:,.0f}, resultados {row['results']:,.0f}")

            # Top anuncios por hook
            if c.get("ad") and c.get("video_3s") and c.get("impressions"):
                df_tmp = df_r.copy()
                df_tmp["__hook__"] = df_tmp[c["video_3s"]] / df_tmp[c["impressions"]].replace(0, np.nan) * 100
                top_h = df_tmp.nlargest(3, "__hook__")[[c["ad"], "__hook__"]].dropna()
                lines.append("Top anuncios por hook rate:")
                for _, row in top_h.iterrows():
                    lines.append(f"  • {str(row[c['ad']])[:60]}: {row['__hook__']:.1f}%")

    else:
        lines.append("=== META ADS === (sin reportes cargados)")

    # ── TELEGRAM ──────────────────────────────────────────────────────────────
    lines.append("\n=== TELEGRAM ===")
    if "error" not in tg_data:
        df_tg  = tg_data.get("df_msg", pd.DataFrame())
        subs   = tg_data.get("subscribers", 0)
        stats  = tg_data.get("stats", {})
        df_grw = tg_data.get("df_growth", pd.DataFrame())

        lines.append(f"Suscriptores actuales: {subs:,}")
        if not df_tg.empty:
            lines.append(f"Posts analizados: {len(df_tg)}")
            lines.append(f"Vistas promedio: {df_tg['vistas'].mean():.0f} | Máximo: {df_tg['vistas'].max():,.0f}")

            # Tendencia últimas 4 semanas vs anteriores
            df_s = df_tg.sort_values("fecha")
            if len(df_s) >= 20:
                rec  = df_s.tail(min(40, len(df_s)//2))["vistas"].mean()
                prev = df_s.head(min(40, len(df_s)//2))["vistas"].mean()
                trend_dir = "↑ en aumento" if rec > prev * 1.05 else ("↓ en descenso" if rec < prev * 0.95 else "→ estable")
                lines.append(f"Tendencia de vistas: {trend_dir} ({rec:.0f} reciente vs {prev:.0f} anterior)")

            # Frecuencia de publicación por semana
            if "semana" in df_tg.columns:
                ppw = df_tg.groupby("semana")["id"].count()
                lines.append(f"Posts/semana: prom {ppw.mean():.1f}, mín {ppw.min()}, máx {ppw.max()}")
                # Semanas con más vistas
                vxsem = df_tg.groupby("semana")["vistas"].mean().sort_values(ascending=False).head(3)
                lines.append("Semanas con más vistas promedio:")
                for sem, v in vxsem.items():
                    posts_sem = ppw.get(sem, 0)
                    lines.append(f"  • Semana {sem}: {v:.0f} vistas prom | {posts_sem} posts publicados")

            # Top 5 posts
            top5 = df_tg.nlargest(5, "vistas")
            lines.append("Top 5 posts por vistas:")
            for _, row in top5.iterrows():
                txt = str(row.get("texto","")).strip()[:100] or "(sin texto/multimedia)"
                has_media = "📷" if row.get("tiene_media") else "💬"
                lines.append(f"  • {has_media} {row['vistas']:,} vistas | {txt}")

            # Posts con texto vs sin texto
            con_txt = df_tg[df_tg["texto"].str.strip().astype(bool)]
            sin_txt = df_tg[~df_tg["texto"].str.strip().astype(bool)]
            if len(con_txt) and len(sin_txt):
                lines.append(f"Vistas prom posts con texto: {con_txt['vistas'].mean():.0f}")
                lines.append(f"Vistas prom posts solo multimedia: {sin_txt['vistas'].mean():.0f}")

        # Crecimiento
        if not df_grw.empty:
            neto_total = int(df_grw["net"].sum()) if "net" in df_grw.columns else 0
            lines.append(f"Crecimiento neto suscriptores: {'+'if neto_total>=0 else ''}{neto_total:,}")
    else:
        lines.append(f"Sin datos de Telegram: {tg_data.get('error','')}")

    return "\n".join(lines)


def _run_ia_analysis(context_text, api_key):
    """Llama a Claude y retorna el texto de análisis completo."""
    client = _anthropic.Anthropic(api_key=api_key)
    prompt = f"""Eres un analista experto en marketing digital, crecimiento de canales de Telegram y publicidad en Meta Ads (Facebook/Instagram). Analiza los siguientes datos reales de un cliente y genera un informe completo en español.

DATOS DEL CLIENTE:
{context_text}

Genera un análisis estructurado con estas secciones exactas (usa los emojis y encabezados indicados):

## 🎯 Resumen Ejecutivo
2-3 conclusiones clave sobre el estado general del canal y la pauta.

## 📊 Análisis Meta Ads
- Qué campañas/anuncios están funcionando mejor y por qué
- Tendencia del CPR y CTR
- Calidad creativa (hook rate, completación de video si hay datos)
- Alertas si el CPR es alto o el CTR bajo

## 📲 Análisis Telegram
- Tendencia de vistas y qué la explica
- Qué tipo de contenido genera más vistas (texto vs multimedia, temas)
- Frecuencia de publicación: ¿es suficiente? ¿hay semanas donde publicar más mejoró las vistas?
- Estado del crecimiento de suscriptores

## 🔗 Correlaciones Detectadas
Encuentra relaciones entre Meta Ads y Telegram: por ejemplo, si en semanas con más pauta el canal creció más, o si hay períodos donde pese a la pauta el canal no creció (posible problema de contenido). Sé específico con los números.

## 🎬 Qué Tipo de Contenido Funciona Mejor
Basado en los top posts: ¿qué tienen en común? ¿qué temáticas o formatos llaman más la atención? ¿qué debería publicarse más?

## ⚡ Acciones Prioritarias
Lista de 5 acciones concretas y ordenadas por impacto, con explicación de por qué cada una mejorará los resultados. Distingue entre acciones de pauta y de contenido orgánico.

Sé directo, usa números reales del informe, y no uses frases genéricas. Si detectas algo bueno, destacalo. Si detectas un problema, nombra el problema y da la solución específica."""

    result = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            result += text
    return result


with pg4:
    _BASE_IA = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(20,25,41,0.6)",
        font=dict(family="Inter", color=MUTED, size=11),
        margin=dict(l=10, r=60, t=50, b=10),
        hoverlabel=dict(bgcolor=CARD2, font_color=WHITE),
    )

    def _ia_card(icon, title, body, color, accion=None):
        lbl = {"🚨":"URGENTE","⚡":"ESTA SEMANA","💡":"SUGERENCIA","✅":"BUENA SEÑAL"}.get(icon,"")
        badge = (f'<span style="background:{color}22;color:{color};font-size:.58rem;font-weight:700;'
                 f'padding:.1rem .45rem;border-radius:20px;letter-spacing:.1em;margin-right:.4rem">{lbl}</span>'
                 if lbl else "")
        act = (f'<div style="background:{color}14;border-left:3px solid {color};border-radius:0 6px 6px 0;'
               f'padding:.45rem .8rem;margin-top:.55rem;font-size:.73rem;color:{WHITE}">→ {accion}</div>'
               if accion else "")
        return (f'<div style="background:{CARD2};border-left:4px solid {color};border-radius:0 10px 10px 0;'
                f'padding:.8rem 1.1rem;margin-bottom:.5rem">'
                f'<div style="display:flex;align-items:center;margin-bottom:.28rem">{badge}'
                f'<span style="font-size:.8rem;font-weight:700;color:{WHITE}">{icon} {title}</span></div>'
                f'<div style="font-size:.76rem;color:{MUTED};line-height:1.7">{body}</div>{act}</div>')

    rep_ia   = st.session_state.get("meta_reports", [])
    df_tg_ia = tg.get("df_msg", pd.DataFrame()) if "error" not in tg else pd.DataFrame()
    subs_ia  = tg.get("subscribers", 0) if "error" not in tg else 0
    df_grw_ia= tg.get("df_growth", pd.DataFrame()) if "error" not in tg else pd.DataFrame()
    has_meta = bool(rep_ia)
    has_tg   = not df_tg_ia.empty

    # Header
    _n_rep = len(rep_ia)
    _tg_ok = has_tg
    st.markdown(f"""
<div style="background:linear-gradient(135deg,{CARD2} 0%,{CARD} 100%);
  border:1px solid {BORDER};border-radius:16px;padding:1.2rem 1.6rem;margin-bottom:1rem">
  <div style="font-size:1rem;font-weight:800;color:{WHITE};margin-bottom:.25rem">🧠 Análisis Inteligente</div>
  <div style="font-size:.76rem;color:{MUTED};line-height:1.7">
    Análisis automático de tus datos de
    <strong style="color:{CYANL}">Meta Ads</strong> y
    <strong style="color:{PURPLEL}">Telegram</strong>.
    Detecta patrones, tendencias y genera recomendaciones accionables.
  </div>
</div>
<div style="display:flex;gap:.8rem;margin-bottom:1.2rem;flex-wrap:wrap">
  <div style="background:{CARD2};border:1px solid {'#22c55e44' if _n_rep else BORDER};border-radius:10px;padding:.5rem .9rem;font-size:.73rem">
    {'✅' if _n_rep else '⬜'} <strong style="color:{WHITE if _n_rep else MUTED}">Meta Ads</strong>
    <span style="color:{MUTED}"> · {_n_rep} reporte{'s' if _n_rep!=1 else ''}</span>
  </div>
  <div style="background:{CARD2};border:1px solid {'#22c55e44' if _tg_ok else BORDER};border-radius:10px;padding:.5rem .9rem;font-size:.73rem">
    {'✅' if _tg_ok else '⬜'} <strong style="color:{WHITE if _tg_ok else MUTED}">Telegram</strong>
    <span style="color:{MUTED}"> · {'datos disponibles' if _tg_ok else 'sin conexión'}</span>
  </div>
</div>""", unsafe_allow_html=True)

    if not has_meta and not has_tg:
        st.markdown(f"""
<div style="background:{CARD};border:1px dashed {BORDER};border-radius:12px;
  padding:1.8rem;text-align:center;margin-top:.5rem">
  <div style="font-size:2rem;margin-bottom:.5rem">📭</div>
  <div style="color:{MUTED};font-size:.8rem">
    No hay datos aún. Sube un reporte de Meta Ads o conecta Telegram para activar el análisis.
  </div>
</div>""", unsafe_allow_html=True)
    else:
        urg_cards, sem_cards, sug_cards = [], [], []

        # ── ANÁLISIS TELEGRAM ─────────────────────────────────────────────────
        if has_tg:
            st.markdown(f'<div class="slabel">📲 Contenido Telegram</div>', unsafe_allow_html=True)
            df_s = df_tg_ia.sort_values("fecha").copy()
            if "texto" in df_s.columns:
                df_s["_has_txt"] = df_s["texto"].str.strip().astype(bool)
            else:
                df_s["_has_txt"] = False

            # ── Texto vs multimedia ───────────────────────────────────────────
            con_txt = df_s[df_s["_has_txt"]]
            sin_txt = df_s[~df_s["_has_txt"]]
            if len(con_txt) >= 3 and len(sin_txt) >= 3:
                avg_con = con_txt["vistas"].mean()
                avg_sin = sin_txt["vistas"].mean()
                mejor   = "con texto" if avg_con > avg_sin else "multimedia"
                diff    = abs(avg_con - avg_sin) / min(avg_con, avg_sin) * 100
                col_txt, col_med = (CYANL, MUTED2) if avg_con > avg_sin else (MUTED2, PURPLEL)
                fig_tipo = go.Figure(go.Bar(
                    x=["📝 Posts con texto", "📷 Posts multimedia"],
                    y=[avg_con, avg_sin],
                    marker=dict(color=[col_txt, col_med], opacity=.88),
                    text=[f"{avg_con:.0f}", f"{avg_sin:.0f}"],
                    textposition="outside",
                    textfont=dict(color=WHITE, size=13, weight=700),
                    hovertemplate="%{x}<br><b>%{y:.0f} vistas prom.</b><extra></extra>"
                ))
                fig_tipo.update_layout(**{**_BASE_IA, "height": 230, "margin": dict(l=10,r=10,t=45,b=10)},
                    title=dict(text="Vistas promedio por tipo de post", font=dict(color=WHITE,size=12,weight=700)),
                    showlegend=False,
                    xaxis=dict(showgrid=False, tickfont=dict(color=WHITE,size=12)),
                    yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED,size=9)))
                st.plotly_chart(fig_tipo, use_container_width=True, config={"displayModeBar":False})
                if diff > 8:
                    body = (f"Posts <strong style='color:{WHITE}'>{mejor}</strong> generan "
                            f"<strong style='color:{CYANL}'>{diff:.0f}% más vistas</strong> "
                            f"({avg_con:.0f} vs {avg_sin:.0f} prom.)")
                    if avg_con > avg_sin:
                        sem_cards.append(_ia_card("⚡","El texto genera más alcance",body,CYANL,
                            "Incluye siempre 2-3 líneas de análisis o contexto en tus publicaciones."))
                    else:
                        sem_cards.append(_ia_card("⚡","El contenido visual tiene más alcance",body,CYANL,
                            "Prioriza imágenes y videos. Si publicas texto, acompáñalo siempre de imagen."))

            # ── Mejor día de la semana ────────────────────────────────────────
            if "fecha" in df_s.columns and len(df_s) >= 14:
                dias_es = {"Monday":"Lun","Tuesday":"Mar","Wednesday":"Mié",
                           "Thursday":"Jue","Friday":"Vie","Saturday":"Sáb","Sunday":"Dom"}
                dias_ord= ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                df_s["_dia"] = df_s["fecha"].dt.day_name()
                by_dia = (df_s.groupby("_dia")["vistas"].agg(["mean","count"])
                          .reindex([d for d in dias_ord if d in df_s["_dia"].values])
                          .dropna())
                by_dia.index = [dias_es.get(d,d) for d in by_dia.index]
                if len(by_dia) >= 3:
                    mejor_dia = by_dia["mean"].idxmax()
                    peor_dia  = by_dia["mean"].idxmin()
                    bar_c = [AMBER if d==mejor_dia else (MUTED2 if d==peor_dia else PURPLE)
                             for d in by_dia.index]
                    fig_dia = go.Figure(go.Bar(
                        x=by_dia.index.tolist(), y=by_dia["mean"].values,
                        marker=dict(color=bar_c, opacity=.88),
                        text=[f"{v:.0f}" for v in by_dia["mean"].values],
                        textposition="outside",
                        textfont=dict(color=WHITE, size=11),
                        hovertemplate="%{x}<br><b>%{y:.0f} vistas prom.</b><extra></extra>"
                    ))
                    fig_dia.update_layout(**{**_BASE_IA,"height":230,"margin":dict(l=10,r=10,t=45,b=10)},
                        title=dict(text="Vistas promedio por día de publicación",font=dict(color=WHITE,size=12,weight=700)),
                        showlegend=False,
                        xaxis=dict(showgrid=False,tickfont=dict(color=WHITE,size=12)),
                        yaxis=dict(gridcolor=BORDER,tickfont=dict(color=MUTED,size=9)))
                    st.plotly_chart(fig_dia, use_container_width=True, config={"displayModeBar":False})
                    mv = by_dia.loc[mejor_dia,"mean"]; pv = by_dia.loc[peor_dia,"mean"]
                    sug_cards.append(_ia_card("💡",f"Mejor día para publicar: {mejor_dia}",
                        f"Los posts del <strong style='color:{WHITE}'>{mejor_dia}</strong> promedian "
                        f"<strong style='color:{AMBER}'>{mv:.0f} vistas</strong> vs "
                        f"{pv:.0f} del {peor_dia} (el día más flojo).",
                        AMBER, f"Programa tu contenido más importante para los {mejor_dia}."))

            # ── Frecuencia vs vistas ──────────────────────────────────────────
            if "semana" in df_s.columns:
                fvv = (df_s.groupby("semana")
                       .agg(posts=("id","count"), avg_v=("vistas","mean"))
                       .reset_index())
                fvv = fvv[fvv["posts"] >= 1]
                if len(fvv) >= 5:
                    corr_fv = float(fvv["posts"].corr(fvv["avg_v"]))
                    xs = np.linspace(fvv["posts"].min(), fvv["posts"].max(), 60)
                    z  = np.polyfit(fvv["posts"], fvv["avg_v"], 1)
                    fig_fvv = go.Figure()
                    fig_fvv.add_trace(go.Scatter(
                        x=fvv["posts"], y=fvv["avg_v"], mode="markers",
                        marker=dict(size=9, color=PURPLEL, opacity=.8,
                                    line=dict(color=CYANL,width=1)),
                        hovertemplate="<b>%{x} posts esa semana</b><br>%{y:.0f} vistas prom.<extra></extra>"
                    ))
                    fig_fvv.add_trace(go.Scatter(
                        x=xs, y=np.poly1d(z)(xs), mode="lines",
                        line=dict(color=CYANL,width=2,dash="dot"), showlegend=False
                    ))
                    fig_fvv.update_layout(**{**_BASE_IA,"height":250},
                        title=dict(text=f"Posts/semana vs Vistas promedio  (correlación r={corr_fv:.2f})",
                                   font=dict(color=WHITE,size=12,weight=700)),
                        xaxis=dict(title=dict(text="Posts publicados esa semana",font=dict(color=MUTED,size=9)),
                                   gridcolor=BORDER,tickfont=dict(color=MUTED,size=9),dtick=1),
                        yaxis=dict(title=dict(text="Vistas promedio",font=dict(color=MUTED,size=9)),
                                   gridcolor=BORDER,tickfont=dict(color=MUTED,size=9)))
                    st.plotly_chart(fig_fvv, use_container_width=True, config={"displayModeBar":False})

                    opt_n = int(fvv.groupby("posts")["avg_v"].mean().idxmax())
                    sem_bajas = int((fvv["posts"] <= 1).sum())
                    pct_bajas = sem_bajas * 100 // len(fvv)
                    if corr_fv > 0.25:
                        sem_cards.append(_ia_card("⚡","Publicar más = más vistas",
                            f"Correlación positiva (r={corr_fv:.2f}). Las semanas con "
                            f"<strong style='color:{CYANL}'>{opt_n} posts</strong> tuvieron el mejor rendimiento.",
                            GREEN, f"Apunta a {opt_n} posts por semana de forma constante."))
                    elif corr_fv < -0.25:
                        sug_cards.append(_ia_card("💡","La frecuencia no es el cuello de botella",
                            f"Más posts no genera más vistas (r={corr_fv:.2f}). La calidad importa más que la cantidad.",
                            AMBER,"Enfócate en mejorar la calidad y el gancho de cada publicación."))
                    if pct_bajas > 30:
                        urg_cards.append(_ia_card("🚨",f"{pct_bajas}% de semanas con muy poca actividad",
                            f"<strong style='color:{PINK}'>{sem_bajas} semanas</strong> con 1 post o menos. "
                            f"La irregularidad penaliza el alcance en Telegram.",
                            PINK,"Fija un mínimo de 3-4 posts por semana. Prepara contenido con anticipación para las semanas ocupadas."))

            # ── Engagement rate (reacciones / vistas) ────────────────────────
            if "reacciones" in df_s.columns and len(df_s) >= 10:
                df_eng = df_s[df_s["vistas"] > 0].copy()
                df_eng["eng_rate"] = df_eng["reacciones"] / df_eng["vistas"] * 100
                avg_eng = float(df_eng["eng_rate"].mean())
                top_eng = df_eng.nlargest(3, "eng_rate")
                top_txt = "; ".join(
                    (str(r.get("texto","")).strip()[:50] or f"Post #{r.get('id','')}")
                    for _, r in top_eng.iterrows()
                )
                if avg_eng < 0.3:
                    urg_cards.append(_ia_card("🚨","Engagement muy bajo — los posts no generan reacción",
                        f"Solo el <strong style='color:{PINK}'>{avg_eng:.2f}%</strong> de las vistas termina en una reacción. "
                        f"El contenido se ve pero no genera emoción ni acción en la audiencia.",
                        PINK,"Añade preguntas directas al final de los posts, genera debate o comparte opiniones más directas. "
                             f"Los posts con mejor engagement son: {top_txt}."))
                elif avg_eng < 0.8:
                    sem_cards.append(_ia_card("⚡",f"Engagement mejorable ({avg_eng:.2f}% reacciones/vistas)",
                        f"El canal tiene un engagement promedio de <strong style='color:{WHITE}'>{avg_eng:.2f}%</strong>. "
                        f"Hay margen para generar más interacción con la audiencia.",
                        AMBER,"Cierra algunos posts con una pregunta o invita a compartir. "
                              f"Tus posts con más reacciones tienen en común: {top_txt}."))
                else:
                    sug_cards.append(_ia_card("✅",f"Buen engagement ({avg_eng:.2f}% reacciones/vistas)",
                        f"La audiencia reacciona bien al contenido. "
                        f"Los posts con más engagement son: <em>{top_txt}</em>.",
                        GREEN,"Identifica el tono y formato de esos posts y aplícalo a los demás."))

            # ── Consistencia de vistas ────────────────────────────────────────
            if len(df_s) >= 15:
                cv = float(df_s["vistas"].std() / df_s["vistas"].mean()) if df_s["vistas"].mean() > 0 else 0
                p90 = float(df_s["vistas"].quantile(0.9))
                p10 = float(df_s["vistas"].quantile(0.1))
                ratio_p = p90 / p10 if p10 > 0 else 0
                if cv > 0.6 and ratio_p > 3:
                    sem_cards.append(_ia_card("⚡","Rendimiento muy inconsistente entre posts",
                        f"Los posts varían mucho: el 10% superior promedia "
                        f"<strong style='color:{WHITE}'>{p90:.0f} vistas</strong> vs "
                        f"<strong style='color:{PINK}'>{p10:.0f}</strong> del 10% inferior ({ratio_p:.1f}× diferencia). "
                        f"No hay una fórmula de contenido clara y repetible.",
                        AMBER,"Analiza los 5 posts con más vistas y los 5 con menos. ¿Qué los diferencia en formato, tema y hora? "
                              "Estandariza los elementos de los mejores y descarta los patrones de los peores."))
                elif cv < 0.3:
                    sug_cards.append(_ia_card("💡","Vistas muy estables — poco riesgo, poco techo",
                        f"Las vistas son muy consistentes (variación {cv:.2f}), lo cual es estable pero puede indicar "
                        f"que el canal ya llegó a un techo con el formato actual.",
                        CYANL,"Prueba un formato completamente distinto al menos 1 vez por semana: hilo largo, encuesta, contenido polémico o exclusivo. "
                              "Necesitas un post que rompa el techo para desbloquear un nuevo nivel de alcance."))

            # ── Temas que más enganchan ───────────────────────────────────────
            if "texto" in df_s.columns and len(df_s) >= 15:
                stopwords = {"de","la","el","en","y","a","que","los","las","por","con","del","se","un","una",
                             "es","al","su","lo","más","como","para","ha","si","pero","fue","ya","muy",
                             "le","o","no","me","te","este","esta","son","hay","sobre","entre","también"}
                top20_pct = df_s.nlargest(max(5, len(df_s)//5), "vistas")
                all_words: dict = {}
                for txt in top20_pct["texto"].dropna():
                    for w in str(txt).lower().split():
                        w = w.strip(".,;:!?\"'()[]*/•*#_")
                        if len(w) > 3 and w not in stopwords:
                            all_words[w] = all_words.get(w, 0) + 1
                top_words = sorted(all_words.items(), key=lambda x: x[1], reverse=True)[:6]
                if top_words:
                    kw_html = " · ".join(
                        f"<strong style='color:{CYANL}'>{w}</strong>" for w, _ in top_words
                    )
                    sug_cards.append(_ia_card("💡","Temas que más llaman la atención",
                        f"Las palabras más frecuentes en el top {max(5,len(df_s)//5)} de posts con más vistas: "
                        f"{kw_html}.",
                        CYANL,"Construye más posts alrededor de estos temas. Son las temáticas que tu audiencia más consume."))

            # ── Tendencia de vistas ───────────────────────────────────────────
            if len(df_s) >= 20:
                mitad = len(df_s) // 2
                rec_v = df_s.tail(mitad)["vistas"].mean()
                ant_v = df_s.head(mitad)["vistas"].mean()
                delta = (rec_v - ant_v) / ant_v * 100
                if delta > 10:
                    sem_cards.append(_ia_card("✅",f"Vistas en tendencia alcista (+{delta:.0f}%)",
                        f"Los posts recientes promedian <strong style='color:{GREEN}'>{rec_v:.0f} vistas</strong> "
                        f"vs {ant_v:.0f} en el período anterior. El contenido está ganando tracción.",
                        GREEN,"Analiza qué tienen en común tus últimos posts exitosos y replica esa fórmula."))
                elif delta < -10:
                    urg_cards.append(_ia_card("🚨",f"Vistas en caída ({delta:.0f}%)",
                        f"Los posts recientes promedian <strong style='color:{PINK}'>{rec_v:.0f} vistas</strong> "
                        f"vs {ant_v:.0f} anteriormente. El alcance orgánico está cayendo.",
                        PINK,"Varía formatos y temáticas. Revisa si la frecuencia de publicación bajó en las últimas semanas."))

            # ── Crecimiento suscriptores ──────────────────────────────────────
            if not df_grw_ia.empty and "net" in df_grw_ia.columns:
                neto_t   = int(df_grw_ia["net"].sum())
                dias_neg = int((df_grw_ia["net"] < 0).sum())
                pct_neg  = dias_neg * 100 // max(len(df_grw_ia), 1)
                if pct_neg > 40:
                    urg_cards.append(_ia_card("🚨",f"{pct_neg}% de los días con pérdida de suscriptores",
                        f"El canal pierde suscriptores en <strong style='color:{PINK}'>{dias_neg} de {len(df_grw_ia)} días</strong>. "
                        f"La tasa de abandono supera la de adquisición en muchos períodos.",
                        PINK,"El contenido puede no estar cumpliendo expectativas. Revisa qué posts coinciden con los días de más salidas."))
                elif neto_t > 0:
                    sug_cards.append(_ia_card("✅",f"Crecimiento neto positivo (+{neto_t:,} suscriptores)",
                        f"El canal tiene un balance neto de <strong style='color:{GREEN}'>+{neto_t:,}</strong> suscriptores en el período analizado.",
                        GREEN))

        if False and has_meta:  # sección removida

            # Calcular totales de inversión y resultados entre todos los reportes
            total_spend = 0.0; total_results = 0.0
            date_min = None; date_max = None
            for r in rep_ia:
                df_r = r["df"]; c = r["cols"]
                if c.get("spend"):  total_spend   += float(df_r[c["spend"]].sum())
                if c.get("results"):total_results += float(df_r[c["results"]].sum())
                if r.get("date_start"):
                    date_min = r["date_start"] if not date_min else min(date_min, r["date_start"])
                if r.get("date_end"):
                    date_max = r["date_end"]   if not date_max else max(date_max, r["date_end"])

            # Crecimiento de suscriptores en el período de los reportes
            subs_en_periodo = None
            if not df_grw_ia.empty and date_min and date_max and "net" in df_grw_ia.columns:
                mask = ((df_grw_ia["fecha"].dt.date >= date_min) &
                        (df_grw_ia["fecha"].dt.date <= date_max))
                subs_en_periodo = int(df_grw_ia.loc[mask, "net"].sum())

            # KPIs pauta → canal
            cpr_val  = total_spend / total_results if total_results > 0 else None
            cps_val  = (total_spend / subs_en_periodo
                        if subs_en_periodo and subs_en_periodo > 0 else None)

            k1, k2, k3 = st.columns(3)
            k1.markdown(kcard("Inversión total pauta", f"${total_spend:,.0f}", "pu","pu"), unsafe_allow_html=True)
            k2.markdown(kcard("Costo por resultado", f"${cpr_val:,.0f}" if cpr_val else "—", "cy","cy"), unsafe_allow_html=True)
            k3.markdown(kcard("Costo est. por suscriptor",
                               f"${cps_val:,.0f}" if cps_val else "—",
                               "gn" if (cps_val and cps_val < 5000) else "pk",
                               "gn" if (cps_val and cps_val < 5000) else "pk"),
                        unsafe_allow_html=True)

            st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

            # Gráfico pauta vs crecimiento (si hay datos de crecimiento semanales)
            if not df_grw_ia.empty and "net" in df_grw_ia.columns and has_tg:
                df_grw_w = (df_grw_ia.copy()
                            .assign(semana=lambda x: x["fecha"].dt.to_period("W").apply(lambda p: p.start_time.date()))
                            .groupby("semana")["net"].sum().reset_index())
                df_tg_w  = (df_tg_ia.groupby("semana")["vistas"].mean().reset_index()
                            if "semana" in df_tg_ia.columns else pd.DataFrame())

                if len(df_grw_w) >= 4 and not df_tg_w.empty:
                    df_tg_w["semana"] = pd.to_datetime(df_tg_w["semana"]).dt.date
                    merged = df_grw_w.merge(df_tg_w, on="semana", how="inner")
                    if len(merged) >= 4:
                        fig_pv = make_subplots(specs=[[{"secondary_y": True}]])
                        fig_pv.add_trace(go.Bar(
                            x=pd.to_datetime(merged["semana"]), y=merged["net"],
                            name="Suscriptores neto",
                            marker=dict(color=[GREEN if v>=0 else PINK for v in merged["net"]], opacity=.8),
                            hovertemplate="%{x|%d/%m}<br><b>%{y:+,d} subs</b><extra></extra>"
                        ), secondary_y=False)
                        fig_pv.add_trace(go.Scatter(
                            x=pd.to_datetime(merged["semana"]), y=merged["vistas"],
                            name="Vistas prom.", mode="lines+markers",
                            line=dict(color=PURPLEL, width=2),
                            marker=dict(size=5, color=PURPLEL),
                            hovertemplate="%{x|%d/%m}<br><b>%{y:.0f} vistas</b><extra></extra>"
                        ), secondary_y=True)
                        fig_pv.update_layout(
                            **{k:v for k,v in _BASE_IA.items() if k != "margin"},
                            margin=dict(l=10,r=10,t=50,b=10), height=270,
                            title=dict(text="Crecimiento de suscriptores vs Vistas orgánicas por semana",
                                       font=dict(color=WHITE,size=12,weight=700)),
                            legend=dict(orientation="h",yanchor="bottom",y=1.02,
                                        font=dict(color=MUTED,size=10),bgcolor="rgba(0,0,0,0)"))
                        fig_pv.update_xaxes(gridcolor=BORDER, tickfont=dict(color=MUTED,size=8))
                        fig_pv.update_yaxes(gridcolor=BORDER, tickfont=dict(color=MUTED,size=8), secondary_y=False,
                                            title_text="Subs neto", title_font=dict(color=MUTED,size=9))
                        fig_pv.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=PURPLEL,size=8),
                                            secondary_y=True, title_text="Vistas",
                                            title_font=dict(color=PURPLEL,size=9))
                        st.plotly_chart(fig_pv, use_container_width=True, config={"displayModeBar":False})

                        # Correlación pauta->crecimiento vs vistas orgánicas
                        corr_sv = float(merged["net"].corr(merged["vistas"]))
                        if corr_sv > 0.4:
                            sug_cards.append(_ia_card("✅","El crecimiento del canal y las vistas van de la mano",
                                f"Correlación positiva (r={corr_sv:.2f}) entre nuevos suscriptores y vistas orgánicas. "
                                f"Las semanas donde el canal crece también son las de mayor alcance.",
                                GREEN,"Mantén consistencia en publicaciones: las semanas activas benefician tanto el crecimiento como el alcance orgánico."))
                        elif corr_sv < -0.2:
                            sem_cards.append(_ia_card("⚡","Los nuevos suscriptores no están viendo el contenido",
                                f"Correlación negativa (r={corr_sv:.2f}): semanas con más suscriptores nuevos tienen menos vistas promedio. "
                                f"Los suscriptores que llega la pauta pueden no estar enganchados con el contenido.",
                                AMBER,"Asegúrate de que el contenido del canal esté alineado con lo que prometen los anuncios. Publica un post de bienvenida fijo."))

            # Retención: si la pauta atrae subs pero el neto es bajo
            if subs_en_periodo is not None and total_results > 0:
                retencion_pct = subs_en_periodo / total_results * 100
                if retencion_pct < 30:
                    urg_cards.append(_ia_card("🚨","Baja retención: la pauta atrae pero el canal no retiene",
                        f"De los <strong style='color:{WHITE}'>{total_results:,.0f} resultados</strong> generados por la pauta, "
                        f"el canal solo retuvo <strong style='color:{PINK}'>{subs_en_periodo:,} suscriptores netos</strong> "
                        f"({retencion_pct:.0f}%). Muchos entran y salen rápido.",
                        PINK,"El contenido del canal no está cumpliendo las expectativas de los anuncios. Revisa que el tono, tema y frecuencia de publicación coincidan con lo que ofrece la pauta."))
                elif retencion_pct > 60:
                    sug_cards.append(_ia_card("✅","Buena retención de suscriptores",
                        f"El <strong style='color:{GREEN}'>{retencion_pct:.0f}%</strong> de los resultados de pauta se traduce en suscriptores netos reales. El canal está reteniendo bien a quienes llegan.",
                        GREEN,"Continúa con la misma línea de contenido. La pauta y el canal están alineados."))

        # ── ACCIONES PRIORITARIAS ─────────────────────────────────────────────
        st.markdown(f'<div class="slabel">⚡ Acciones prioritarias</div>', unsafe_allow_html=True)
        if not urg_cards and not sem_cards and not sug_cards:
            st.markdown(f"""
<div style="background:{CARD2};border:1px dashed {BORDER};border-radius:12px;padding:1.2rem;
  text-align:center;color:{MUTED};font-size:.8rem">
  No hay suficientes datos para generar recomendaciones. Sube reportes de Meta Ads con más historial.
</div>""", unsafe_allow_html=True)
        else:
            if urg_cards:
                st.markdown(f'<div style="font-size:.68rem;font-weight:700;color:{PINK};'
                            f'letter-spacing:.15em;margin:.5rem 0 .4rem 0">🚨 URGENTE — ATENDER HOY</div>',
                            unsafe_allow_html=True)
                st.markdown("".join(urg_cards), unsafe_allow_html=True)
            if sem_cards:
                st.markdown(f'<div style="font-size:.68rem;font-weight:700;color:{AMBER};'
                            f'letter-spacing:.15em;margin:.9rem 0 .4rem 0">⚡ ESTA SEMANA</div>',
                            unsafe_allow_html=True)
                st.markdown("".join(sem_cards), unsafe_allow_html=True)
            if sug_cards:
                st.markdown(f'<div style="font-size:.68rem;font-weight:700;color:{CYANL};'
                            f'letter-spacing:.15em;margin:.9rem 0 .4rem 0">💡 SUGERENCIAS</div>',
                            unsafe_allow_html=True)
                st.markdown("".join(sug_cards), unsafe_allow_html=True)

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
