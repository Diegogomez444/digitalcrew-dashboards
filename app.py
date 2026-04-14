import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import date, timedelta, datetime

# ── CONFIG ─────────────────────────────────────────────────────────────────────
# Lee desde secrets de Streamlit Cloud; si no existen usa los valores por defecto
SHEET_ID    = st.secrets.get("SHEET_ID",    "1KszbEw3CX5jWtWxqE_Oy7Bi17IA5ZJr6FfOkCRJ4zH4")
GID_GENERAL = st.secrets.get("GID_GENERAL", "0")
GID_TG      = st.secrets.get("GID_TG",      "859239310")
CLIENTE     = st.secrets.get("CLIENTE",     "La Fiera Analista")

# ── PALETTE ────────────────────────────────────────────────────────────────────
BG       = "#0B0F1A"
CARD     = "#141929"
CARD2    = "#1C2338"
BORDER   = "#252D45"
PURPLE   = "#7C3AED"
PURPLEL  = "#A855F7"
PINK     = "#EC4899"
CYAN     = "#06B6D4"
CYANL    = "#22D3EE"
GREEN    = "#10B981"
RED      = "#EF4444"
AMBER    = "#F59E0B"
WHITE    = "#FFFFFF"
MUTED    = "#94A3B8"
MUTED2   = "#374151"

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

def fetch_csv(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    return pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

def delta_pct(current, prev):
    if prev and prev != 0:
        return (current - prev) / abs(prev) * 100
    return None

# ── DATA LOADERS ───────────────────────────────────────────────────────────────
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
            if c == "P.Restante"   and j+1 < len(row) and "p_restante" not in s:
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
  padding:0 0 1.4rem 0;border-bottom:1px solid {BORDER};margin-bottom:1.6rem;}}
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

/* ── Filter buttons ── */
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

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{{
  background:{CARD};border-radius:11px;padding:4px;gap:3px;border:1px solid {BORDER};}}
.stTabs [data-baseweb="tab"]{{
  color:{MUTED};background:transparent;border-radius:8px;
  font-size:.76rem;font-weight:500;padding:.35rem 1rem;}}
.stTabs [aria-selected="true"]{{
  background:linear-gradient(135deg,{PURPLE},{CYAN})!important;
  color:#fff!important;font-weight:700!important;
  box-shadow:0 2px 12px rgba(124,58,237,.4)!important;}}

/* ── DataFrame ── */
[data-testid="stDataFrame"]{{border:1px solid {BORDER};border-radius:14px;overflow:hidden;}}
</style>
""", unsafe_allow_html=True)

# ── LOAD DATA ──────────────────────────────────────────────────────────────────
summ   = load_summary()
df_all = load_daily()

if df_all is None:
    st.error("No se pudieron cargar los datos. Verifica que el Sheet sea público.")
    st.stop()

# ── HEADER ─────────────────────────────────────────────────────────────────────
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

# ── DATE FILTERS ───────────────────────────────────────────────────────────────
min_d = df_all["Fecha"].dt.date.min()
max_d = df_all["Fecha"].dt.date.max()

if "ds" not in st.session_state: st.session_state.ds = min_d
if "de" not in st.session_state: st.session_state.de = max_d

st.markdown('<div class="slabel">Período de análisis</div>', unsafe_allow_html=True)

b1,b2,b3,b4,b5 = st.columns(5)
if b1.button("Últimos 3 días",  use_container_width=True):
    st.session_state.ds = max_d - timedelta(days=2); st.session_state.de = max_d
if b2.button("Últimos 7 días",  use_container_width=True):
    st.session_state.ds = max_d - timedelta(days=6); st.session_state.de = max_d
if b3.button("Últimos 15 días", use_container_width=True):
    st.session_state.ds = max_d - timedelta(days=14); st.session_state.de = max_d
if b4.button("Este mes",        use_container_width=True):
    st.session_state.ds = date.today().replace(day=1); st.session_state.de = max_d
if b5.button("Todo el período", use_container_width=True):
    st.session_state.ds = min_d; st.session_state.de = max_d

dc1, dc2 = st.columns(2)
d_start = dc1.date_input("Desde", value=st.session_state.ds, min_value=min_d, max_value=max_d)
d_end   = dc2.date_input("Hasta", value=st.session_state.de, min_value=min_d, max_value=max_d)

df  = df_all[(df_all["Fecha"].dt.date >= d_start) & (df_all["Fecha"].dt.date <= d_end)].copy()
dfv = df[df["Gasto"].notna() & (df["Gasto"] > 0)].copy()

# Delta helper (last 3 days vs prev 3 days)
def get_delta(col):
    valid = df_all[df_all[col].notna() & (df_all[col] > 0)] if col == "Gasto" else df_all[df_all[col].notna()]
    if len(valid) < 6: return None
    last3 = valid.tail(3)[col].mean()
    prev3 = valid.iloc[-6:-3][col].mean()
    return delta_pct(last3, prev3)

def delta_html(val, inverse=False):
    if val is None: return ""
    good = val < 0 if inverse else val > 0
    arrow = "▲" if val > 0 else "▼"
    cls   = "kc-up" if good else "kc-dn"
    return f'<span class="{cls}">{arrow} {abs(val):.1f}%</span>'

# ── SECTION 1: PRESUPUESTO GENERAL ────────────────────────────────────────────
st.markdown('<div class="slabel">Presupuesto del período</div>', unsafe_allow_html=True)

inv_pauta   = parse_cop(summ.get("inv_pauta","0"))
inv_bot     = parse_cop(summ.get("inv_bot","0"))
inv_total   = parse_cop(summ.get("inv_total","0"))
cxr_obj     = parse_cop(summ.get("cxr_obj","0"))
leads_p     = parse_num(summ.get("leads","0"))
dias_p      = parse_num(summ.get("dias_pauta","31"))
pdia        = parse_cop(summ.get("presup_dia","0"))
gasto_act   = parse_cop(summ.get("gasto_actual","0"))
p_rest      = parse_cop(summ.get("p_restante","0"))

def kcard(label, value, style="plain", color="", sub="", delta=""):
    return f"""<div class="kc kc-{style}">
      <div class="kc-lbl">{label}</div>
      <div class="kc-val {color}">{value}</div>
      {"<div class='kc-sub'>"+sub+"</div>" if sub else ""}
      {"<div style='margin-top:.3rem'>"+delta+"</div>" if delta else ""}
    </div>"""

r1c1,r1c2,r1c3,r1c4,r1c5,r1c6,r1c7 = st.columns(7)
r1c1.markdown(kcard("Inv. Pauta",   fmt_cop(inv_pauta),  "plain"), unsafe_allow_html=True)
r1c2.markdown(kcard("Inv. Bot",     fmt_cop(inv_bot),    "plain"), unsafe_allow_html=True)
r1c3.markdown(kcard("Inv. Total",   fmt_cop(inv_total),  "pu","pu"), unsafe_allow_html=True)
r1c4.markdown(kcard("CxR Obj. TG",  fmt_cop(cxr_obj),   "cy","cy"), unsafe_allow_html=True)
r1c5.markdown(kcard("Leads presup.",fmt_num(leads_p),    "plain"), unsafe_allow_html=True)
r1c6.markdown(kcard("Días en pauta",str(int(dias_p)) if dias_p else "—","plain"), unsafe_allow_html=True)
r1c7.markdown(kcard("Presup./Día",  fmt_cop(pdia),       "plain"), unsafe_allow_html=True)

st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)

pct = min((gasto_act / inv_pauta * 100) if inv_pauta else 0, 100)
st.markdown(f"""
<div class="prog-wrap">
  <div class="prog-row">
    <span class="prog-title">Ejecución de presupuesto de pauta</span>
    <span class="prog-pct">{pct:.1f}%</span>
  </div>
  <div class="prog-track"><div class="prog-fill" style="width:{pct}%"></div></div>
  <div class="prog-stats">
    <div class="ps"><span>Gastado</span><br><strong>{fmt_cop(gasto_act)}</strong></div>
    <div class="ps" style="text-align:center"><span>Restante</span><br><strong>{fmt_cop(p_rest)}</strong></div>
    <div class="ps" style="text-align:right"><span>Total</span><br><strong>{fmt_cop(inv_pauta)}</strong></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── SECTION 2: MÉTRICAS DEL PERÍODO ───────────────────────────────────────────
st.markdown('<div class="slabel">Métricas del período seleccionado</div>', unsafe_allow_html=True)

def safe_sum(col): return dfv[col].sum() if col in dfv.columns else 0
def safe_mean(col): return dfv[col].mean() if col in dfv.columns and dfv[col].notna().any() else 0

t_gasto   = safe_sum("Gasto")
t_result  = safe_sum("Resultado")
avg_cxrfb = safe_mean("CxResultado FB")
avg_cxrtg = safe_mean("CxResultado+ TG")
t_impr    = safe_sum("Impresiones")
t_clics   = safe_sum("Clics")
avg_ctr   = safe_mean("CTR")
avg_cxclic= safe_mean("CxClic")
t_tg      = safe_sum("TG Tracking")
avg_cw    = safe_mean("Conv Web")
avg_cargw = safe_mean("Cargar Web")

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
m6.markdown(kcard("Impresiones",    fmt_num(t_impr),    "plain"), unsafe_allow_html=True)
m7.markdown(kcard("Clics totales",  fmt_num(t_clics),   "plain",
    delta=delta_html(get_delta("Clics"))), unsafe_allow_html=True)
m8.markdown(kcard("CTR promedio",   f"{avg_ctr:.2f}%",  "gn","gn",
    delta=delta_html(get_delta("CTR"))), unsafe_allow_html=True)
m9.markdown(kcard("CxClic prom.",   fmt_cop(avg_cxclic),"plain"), unsafe_allow_html=True)
m10.markdown(kcard("Conv. Web",     f"{avg_cw:.2f}%",   "plain","",
    sub=f"Cargar Web: {avg_cargw:.1f}%"), unsafe_allow_html=True)

# ── SECTION 3: GAUGES ─────────────────────────────────────────────────────────
st.markdown('<div class="slabel">Indicadores de rendimiento</div>', unsafe_allow_html=True)

def make_gauge(value, title, max_val, thresholds, colors_g, suffix="$", fmt_fn=None):
    display = fmt_fn(value) if fmt_fn and value else f"{suffix}{value:,.0f}" if value else "—"
    steps = []
    prev = 0
    for (thresh, col) in zip(thresholds, colors_g[:-1]):
        steps.append(dict(range=[prev, thresh], color=col))
        prev = thresh
    steps.append(dict(range=[prev, max_val], color=colors_g[-1]))
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value if value else 0,
        number={"valueformat": ",.0f", "prefix": "$" if suffix=="$" else "",
                "suffix": suffix if suffix!="$" else "",
                "font": {"size": 22, "color": WHITE, "family": "Inter"}},
        title={"text": title, "font": {"size": 11, "color": MUTED, "family": "Inter"}},
        gauge={
            "axis": {"range": [0, max_val], "tickfont": {"color": MUTED, "size": 9},
                     "tickcolor": MUTED, "gridcolor": BORDER},
            "bar": {"color": PURPLEL, "thickness": 0.25},
            "bgcolor": CARD2,
            "bordercolor": BORDER,
            "steps": steps,
            "threshold": {"line": {"color": WHITE, "width": 3}, "value": value or 0}
        }
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter"}, height=200,
        margin=dict(l=20, r=20, t=40, b=10)
    )
    return fig

last_cxr  = dfv["CxResultado FB"].dropna().iloc[-1] if len(dfv) > 0 and "CxResultado FB" in dfv.columns else 0
last_ctr  = dfv["CTR"].dropna().iloc[-1]             if len(dfv) > 0 and "CTR" in dfv.columns else 0
last_cw   = dfv["Conv Web"].dropna().iloc[-1]         if len(dfv) > 0 and "Conv Web" in dfv.columns else 0
last_carw = dfv["Cargar Web"].dropna().iloc[-1]       if len(dfv) > 0 and "Cargar Web" in dfv.columns else 0

g1,g2,g3,g4 = st.columns(4)
with g1:
    st.plotly_chart(make_gauge(
        last_cxr, "CxResultado FB (último día)", 2500,
        [750, 1125, 1500, 1875],
        [GREEN, "#84CC16", AMBER, "#F97316", RED]
    ), use_container_width=True, config={"displayModeBar": False})
    st.markdown(f"""<div style='text-align:center;margin-top:-1rem'>
      <span style='font-size:.6rem;color:{MUTED};letter-spacing:.15em;text-transform:uppercase'>
      V1 Excelente &lt;$750 &nbsp;·&nbsp; V3 Objetivo $1.500 &nbsp;·&nbsp; V5 Apagar &gt;$1.875</span>
    </div>""", unsafe_allow_html=True)

with g2:
    st.plotly_chart(make_gauge(
        last_ctr, "CTR (último día)", 5,
        [1.5, 2.5, 3.5],
        [RED, AMBER, GREEN, CYANL],
        suffix="%", fmt_fn=None
    ), use_container_width=True, config={"displayModeBar": False})

with g3:
    st.plotly_chart(make_gauge(
        last_cw, "Conv. Web (último día)", 50,
        [15, 25, 35],
        [RED, AMBER, GREEN, CYANL],
        suffix="%"
    ), use_container_width=True, config={"displayModeBar": False})

with g4:
    st.plotly_chart(make_gauge(
        last_carw, "Cargar Web (último día)", 100,
        [70, 80, 90],
        [RED, AMBER, GREEN, CYANL],
        suffix="%"
    ), use_container_width=True, config={"displayModeBar": False})

# ── SECTION 4: CHARTS ──────────────────────────────────────────────────────────
st.markdown('<div class="slabel">Análisis visual</div>', unsafe_allow_html=True)

BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=f"rgba(20,25,41,0.6)",
    font=dict(family="Inter", color=MUTED, size=11),
    margin=dict(l=10, r=10, t=45, b=10), height=340,
    hovermode="x unified", hoverlabel=dict(bgcolor=CARD2, font_color=WHITE),
    xaxis=dict(gridcolor=BORDER, showgrid=True, zeroline=False,
               tickfont=dict(color=MUTED, size=10)),
    yaxis=dict(gridcolor=BORDER, showgrid=True, zeroline=False,
               tickfont=dict(color=MUTED, size=10)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                font=dict(color=MUTED, size=10), bgcolor="rgba(0,0,0,0)")
)

tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "📊 Gasto y Resultados","💰 Costos","📈 Tráfico y CTR",
    "🎯 Ejecución vs Ideal","📲 Telegram"
])

with tab1:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x = dfv["Fecha"]
    # Area chart gasto
    fig.add_trace(go.Scatter(
        x=x, y=dfv["Gasto"], name="Gasto",
        line=dict(color=PURPLEL, width=2.5),
        fill="tozeroy", fillcolor="rgba(168,85,247,0.15)",
        mode="lines", hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>Gasto</extra>"
    ), secondary_y=False)
    # Line resultados
    if "Resultado" in dfv.columns:
        fig.add_trace(go.Scatter(
            x=x, y=dfv["Resultado"], name="Resultados",
            line=dict(color=CYANL, width=2.5),
            mode="lines+markers", marker=dict(size=5, color=CYANL,
            line=dict(color=BG, width=1.5)),
            hovertemplate="%{x|%d/%m}<br><b>%{y}</b><extra>Resultados</extra>"
        ), secondary_y=True)
    fig.update_layout(**BASE, title=dict(text="Gasto Diario vs Resultados",
        font=dict(color=WHITE, size=13, weight=700)))
    fig.update_yaxes(title_text="Gasto (COP)", secondary_y=False,
        gridcolor=BORDER, tickfont=dict(color=MUTED, size=10))
    fig.update_yaxes(title_text="Resultados", secondary_y=True,
        gridcolor=BORDER, tickfont=dict(color=MUTED, size=10))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with tab2:
    fig = go.Figure()
    if "CxResultado FB" in dfv.columns:
        fig.add_trace(go.Scatter(
            x=dfv["Fecha"], y=dfv["CxResultado FB"], name="CxResultado FB",
            line=dict(color=PURPLEL, width=2.5),
            fill="tozeroy", fillcolor="rgba(168,85,247,0.1)",
            mode="lines+markers", marker=dict(size=5, color=PURPLEL,
            line=dict(color=BG, width=1.5)),
            hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>CxR FB</extra>"
        ))
    if "CxResultado+ TG" in dfv.columns:
        fig.add_trace(go.Scatter(
            x=dfv["Fecha"], y=dfv["CxResultado+ TG"], name="CxResultado + TG",
            line=dict(color=CYANL, width=2, dash="dot"),
            mode="lines+markers", marker=dict(size=4, color=CYANL),
            hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>CxR+TG</extra>"
        ))
    # V-tier reference lines
    tiers = [(750,"V1 Excelente",GREEN),(1125,"V2 Optimizar","#84CC16"),
             (1500,"V3 Objetivo",AMBER),(1875,"V4 Alerta","#F97316")]
    for val,lbl,col in tiers:
        fig.add_hline(y=val, line_dash="dash", line_color=col, opacity=0.5,
            annotation_text=f"  {lbl}  ${val:,}", annotation_position="right",
            annotation_font=dict(color=col, size=9))
    fig.update_layout(**BASE, title=dict(text="Costo por Resultado · Referencias V1–V4",
        font=dict(color=WHITE, size=13, weight=700)))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with tab3:
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Clics e Impresiones","CTR Diario (%)"),
        column_widths=[0.55,0.45])
    # Clics bars
    if "Clics" in dfv.columns:
        fig.add_trace(go.Bar(
            x=dfv["Fecha"], y=dfv["Clics"], name="Clics",
            marker=dict(color=PURPLEL, opacity=0.85,
                line=dict(color="rgba(0,0,0,0)", width=0)),
            hovertemplate="%{x|%d/%m}<br><b>%{y:,.0f} clics</b><extra></extra>"
        ), row=1, col=1)
    if "Visitas Pag" in dfv.columns:
        fig.add_trace(go.Scatter(
            x=dfv["Fecha"], y=dfv["Visitas Pag"], name="Visitas Pág.",
            line=dict(color=CYANL, width=2), mode="lines+markers",
            marker=dict(size=4, color=CYANL),
            hovertemplate="%{x|%d/%m}<br><b>%{y:,.0f} visitas</b><extra></extra>"
        ), row=1, col=1)
    if "CTR" in dfv.columns:
        fig.add_trace(go.Scatter(
            x=dfv["Fecha"], y=dfv["CTR"], name="CTR %",
            line=dict(color=GREEN, width=2.5),
            fill="tozeroy", fillcolor="rgba(16,185,129,0.12)",
            mode="lines+markers", marker=dict(size=5, color=GREEN,
            line=dict(color=BG, width=1.5)),
            hovertemplate="%{x|%d/%m}<br><b>%{y:.2f}%</b><extra>CTR</extra>"
        ), row=1, col=2)
    fig.update_layout(**BASE, title=dict(text="Tráfico y Tasa de Clics",
        font=dict(color=WHITE, size=13, weight=700)))
    fig.update_xaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
    fig.update_yaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
    for ann in fig.layout.annotations:
        ann.font.color = MUTED; ann.font.size = 11
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with tab4:
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
    if "Dif Gasto" in dfv.columns:
        dif = df_real["Dif Gasto"].dropna()
        cols_bar = [GREEN if v >= 0 else RED for v in dif]
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

with tab5:
    fig = make_subplots(rows=1, cols=2,
        subplot_titles=("TG Tracking diario ($)", "Meta Telegram acumulada vs Real"),
        column_widths=[0.45, 0.55])
    if "TG Tracking" in dfv.columns:
        tg_vals = dfv["TG Tracking"].fillna(0)
        tg_colors = [CYANL if v > 0 else MUTED2 for v in tg_vals]
        fig.add_trace(go.Bar(
            x=dfv["Fecha"], y=tg_vals, name="TG Tracking",
            marker=dict(color=tg_colors, opacity=0.85,
                line=dict(color="rgba(0,0,0,0)", width=0)),
            hovertemplate="%{x|%d/%m}<br><b>$%{y:,.0f}</b><extra>TG Tracking</extra>"
        ), row=1, col=1)
    df_tg = df_all[df_all["Meta Telegram"].notna()].copy()
    df_tg_r = df_all[df_all["Meta VS Real"].notna()].copy()
    if len(df_tg) > 0:
        fig.add_trace(go.Scatter(
            x=df_tg["Fecha"], y=df_tg["Meta Telegram"], name="Meta TG",
            line=dict(color=MUTED2, width=2, dash="dash"),
            hovertemplate="%{x|%d/%m}<br><b>%{y:,.0f}</b><extra>Meta</extra>"
        ), row=1, col=2)
    if len(df_tg_r) > 0:
        meta_vs = df_tg_r["Meta VS Real"]
        col_mv = [GREEN if v >= 0 else RED for v in meta_vs]
        fig.add_trace(go.Scatter(
            x=df_tg_r["Fecha"], y=meta_vs, name="Meta VS Real",
            line=dict(color=CYANL, width=2.5),
            mode="lines+markers",
            marker=dict(size=5, color=col_mv, line=dict(color=BG, width=1)),
            hovertemplate="%{x|%d/%m}<br><b>%{y:,.0f}</b><extra>VS Real</extra>"
        ), row=1, col=2)
    fig.update_layout(**BASE, title=dict(text="Seguimiento Telegram",
        font=dict(color=WHITE, size=13, weight=700)))
    fig.update_xaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
    fig.update_yaxes(gridcolor=BORDER, tickfont=dict(color=MUTED, size=9))
    for ann in fig.layout.annotations:
        ann.font.color = MUTED; ann.font.size = 11
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── SECTION 5: DATA TABLE ─────────────────────────────────────────────────────
st.markdown('<div class="slabel">Detalle diario</div>', unsafe_allow_html=True)

show_cols = ["Fecha","Gasto","Resultado","CxResultado FB","CxResultado+ TG",
             "Impresiones","Clics","CxClic","CTR","Cargar Web","Conv Web","TG Tracking"]
show_cols = [c for c in show_cols if c in dfv.columns]
tbl = dfv[show_cols].copy()
tbl["Fecha"] = tbl["Fecha"].dt.strftime("%d/%m/%Y")
tbl = tbl.set_index("Fecha")

fmt = {}
for c in tbl.columns:
    if c in ["Gasto","CxResultado FB","CxResultado+ TG","CxClic","TG Tracking"]:
        fmt[c] = "${:,.0f}"
    elif c in ["CTR","Cargar Web","Conv Web"]:
        fmt[c] = "{:.2f}%"
    elif c in ["Resultado","Impresiones","Clics"]:
        fmt[c] = "{:,.0f}"

st.dataframe(tbl.style.format(fmt, na_rep="—"), use_container_width=True, height=380)

# ── FOOTER ────────────────────────────────────────────────────────────────────
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
