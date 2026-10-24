from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# KONFIGURASI HALAMAN & TEMA MERAH
# ------------------------------------------------------------------
st.set_page_config(page_title="Dashboard Penjualan Shopify", page_icon="🛍️", layout="wide")

RED_DARK, RED, RED_SOFT, ROSE = "#7A0C1E", "#C1121F", "#E5383B", "#FFB3B3"
RED_SCALE = ["#7A0C1E", "#A4161A", "#C1121F", "#E5383B", "#F4777F", "#FFB3B3"]

st.markdown(
    f"""
    <style>
    .stApp {{background: #FFF8F6; color: #3B0A0F;}}
    [data-testid="stSidebar"] {{background: #FDE8E8;}}
    span[data-baseweb="tag"] {{background-color: {RED} !important; color: white !important;}}
    .banner {{background: linear-gradient(120deg, {RED_DARK}, {RED} 60%, {RED_SOFT});
        padding: 26px 32px; border-radius: 18px; color: white; margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(193,18,31,.25);}}
    .banner h1 {{margin: 0; font-size: 2rem; color: white;}}
    .banner p {{margin: 4px 0 0; opacity: .9;}}
    .kpi {{background: white; border-radius: 16px; padding: 18px 20px;
        border-left: 7px solid {RED}; box-shadow: 0 4px 14px rgba(122,12,30,.12);}}
    .kpi .label {{font-size: .78rem; letter-spacing: .08em; color: #8a4b50; font-weight: 700;}}
    .kpi .value {{font-size: 1.9rem; font-weight: 800; color: {RED_DARK}; line-height: 1.2;}}
    .kpi .icon {{float: right; font-size: 1.6rem;}}
    div[data-testid="stPlotlyChart"] {{background: white; border-radius: 16px; padding: 8px;
        box-shadow: 0 4px 14px rgba(122,12,30,.10);}}
    h3 {{color: {RED_DARK};}}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# LOAD DATA (file Excel .xlsx)
# ------------------------------------------------------------------
DATA_FILE = Path(__file__).parent / "dataset_penjualan.xlsx"


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0, engine="openpyxl")
    df["order_date"] = pd.to_datetime(df["order_date"], dayfirst=True)
    return df


df = load_data(DATA_FILE)

# ------------------------------------------------------------------
# SLICER (SIDEBAR)
# ------------------------------------------------------------------
st.sidebar.markdown("## 🔴 Slicer")

min_d, max_d = df["order_date"].min().date(), df["order_date"].max().date()
date_range = st.sidebar.date_input("Rentang Tanggal", (min_d, max_d), min_value=min_d, max_value=max_d)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
else:
    start, end = min_d, max_d


def multi(label, col):
    opts = sorted(df[col].unique())
    return st.sidebar.multiselect(label, opts, default=opts)


sel_country = multi("Negara", "customer_country")
sel_cat = multi("Kategori Produk", "product_category")
sel_pay = multi("Metode Pembayaran", "payment_method")
sel_traffic = multi("Sumber Traffic", "traffic_source")

mask = (
    df["order_date"].between(pd.Timestamp(start), pd.Timestamp(end))
    & df["customer_country"].isin(sel_country)
    & df["product_category"].isin(sel_cat)
    & df["payment_method"].isin(sel_pay)
    & df["traffic_source"].isin(sel_traffic)
)
data = df[mask]

# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------
st.markdown(
    """<div class="banner"><h1>🛍️ Dashboard Penjualan Shopify</h1>
    <p>Ringkasan order, revenue, profit, dan kuantitas penjualan</p></div>""",
    unsafe_allow_html=True,
)

if data.empty:
    st.warning("Tidak ada data untuk kombinasi slicer ini. Longgarkan filter di sidebar.")
    st.stop()

# ------------------------------------------------------------------
# KPI
# ------------------------------------------------------------------
def fmt(x: float) -> str:
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= limit:
            return f"{x / limit:,.2f}{suffix}"
    return f"{x:,.0f}"


kpis = [
    ("TOTAL ORDER", fmt(data["order_id"].nunique()), "🧾"),
    ("TOTAL REVENUE", fmt(data["revenue_baru"].sum()), "💰"),
    ("TOTAL PROFIT", fmt(data["provit_baru"].sum()), "📈"),
    ("TOTAL PRODUK TERJUAL", fmt(data["quantity"].sum()), "📦"),
]
for col, (label, value, icon) in zip(st.columns(4), kpis):
    col.markdown(
        f'<div class="kpi"><span class="icon">{icon}</span>'
        f'<div class="label">{label}</div><div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ------------------------------------------------------------------
# HELPER AGREGASI
# ------------------------------------------------------------------
METRICS = {
    "Revenue": ("revenue_baru", "sum"),
    "Profit": ("provit_baru", "sum"),
    "Total Order": ("order_id", "nunique"),
    "Kuantitas": ("quantity", "sum"),
}


def aggregate(frame: pd.DataFrame, by, metric: str) -> pd.DataFrame:
    col, how = METRICS[metric]
    return frame.groupby(by, as_index=False).agg(nilai=(col, how))


def style(fig, height=380):
    fig.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#3B0A0F"),
        margin=dict(l=20, r=20, t=50, b=20),
        title_font=dict(size=17, color=RED_DARK),
    )
    return fig


# ------------------------------------------------------------------
# 1. TREN PENJUALAN BULANAN (LINE CHART)
# ------------------------------------------------------------------
m_line = st.radio("Metrik tren bulanan", list(METRICS), horizontal=True, key="m_line")
tmp = data.assign(bulan=data["order_date"].dt.to_period("M").dt.to_timestamp())
monthly = aggregate(tmp, "bulan", m_line)
fig = px.line(monthly, x="bulan", y="nilai", markers=True,
              title=f"Tren Penjualan Bulanan ({m_line})",
              labels={"bulan": "Bulan", "nilai": m_line})
fig.update_traces(line=dict(color=RED, width=3), marker=dict(size=8, color=RED_DARK),
                  fill="tozeroy", fillcolor="rgba(229,56,59,0.12)")
st.plotly_chart(style(fig, 400))

# ------------------------------------------------------------------
# 2. TOP 5 NEGARA (BAR HORIZONTAL)   &   3. TOP 5 KATEGORI (PIE)
# ------------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    m_ctry = st.selectbox("Top 5 Negara berdasarkan", list(METRICS), key="m_ctry")
    top_c = aggregate(data, "customer_country", m_ctry).nlargest(5, "nilai")
    fig = px.bar(top_c, x="nilai", y="customer_country", orientation="h", text_auto=".3s",
                 title=f"Top 5 Negara ({m_ctry})",
                 labels={"nilai": m_ctry, "customer_country": "Negara"},
                 color="nilai", color_continuous_scale=["#FFB3B3", RED, RED_DARK])
    fig.update_layout(yaxis=dict(categoryorder="total ascending"), coloraxis_showscale=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(style(fig))

with c2:
    m_cat = st.selectbox("Top 5 Kategori berdasarkan", list(METRICS), key="m_cat")
    top_k = aggregate(data, "product_category", m_cat).nlargest(5, "nilai")
    fig = px.pie(top_k, names="product_category", values="nilai", hole=0.4,
                 title=f"Top 5 Kategori Produk ({m_cat})",
                 color_discrete_sequence=RED_SCALE)
    fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="white", width=2)))
    st.plotly_chart(style(fig))

# ------------------------------------------------------------------
# 4. HEATMAP RATING vs DISKON   &   5. PAYMENT METHOD (BAR VERTIKAL)
# ------------------------------------------------------------------
c3, c4 = st.columns(2)

with c3:
    st.caption("Warna lebih gelap = jumlah order lebih banyak. Rating dikelompokkan per 0,5.")
    edges = np.arange(1, 5.5, 0.5)
    labels = [f"{a:.1f}–{b:.1f}" for a, b in zip(edges[:-1], edges[1:])]
    tmp = data.assign(rating_bin=pd.cut(data["rating"], bins=edges, labels=labels, include_lowest=True))
    heat = (tmp.pivot_table(index="discount_percent", columns="rating_bin", values="order_id",
                            aggfunc="count", fill_value=0, observed=False)
               .sort_index(ascending=False))
    fig = px.imshow(heat, text_auto=True, aspect="auto",
                    color_continuous_scale=["#FFF0F0", "#FFB3B3", RED, RED_DARK],
                    labels=dict(x="Rating", y="Diskon (%)", color="Jumlah Order"),
                    title="Heatmap Rating vs Diskon (%)")
    fig.update_yaxes(type="category")
    st.plotly_chart(style(fig))

with c4:
    m_pay = st.selectbox("Payment Method berdasarkan", list(METRICS), key="m_pay")
    pay = aggregate(data, "payment_method", m_pay).sort_values("nilai", ascending=False)
    fig = px.bar(pay, x="payment_method", y="nilai", text_auto=".3s",
                 title=f"Metode Pembayaran ({m_pay})",
                 labels={"payment_method": "Metode Pembayaran", "nilai": m_pay},
                 color="nilai", color_continuous_scale=["#FFB3B3", RED, RED_DARK])
    fig.update_layout(coloraxis_showscale=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(style(fig))

st.caption(f"Menampilkan {len(data):,} dari {len(df):,} baris data.")
