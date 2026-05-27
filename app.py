"""
대한민국 지역별 인구 현황 대시보드
출처: 행정안전부 주민등록 인구현황 (2024년 12월 기준)
"""

import json
import os
import sys

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

# 데이터 모듈 경로 추가
sys.path.insert(0, os.path.dirname(__file__))
from data.population_data import (
    MUNICIPALITY_KO,
    MUNICIPALITY_POPULATION,
    PROVINCE_KO,
    PROVINCE_POPULATION,
)

# ──────────────────────────────────────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="대한민국 인구 현황",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────────────────────
# 전역 CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* 전체 배경 */
    [data-testid="stAppViewContainer"] { background: #0f1117; color: #e8eaf0; }
    [data-testid="stHeader"] { background: transparent; }

    /* 헤더 */
    .main-header {
        text-align: center;
        padding: 1.2rem 0 0.5rem;
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4fc3f7, #81d4fa, #e1f5fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .sub-header {
        text-align: center;
        color: #90a4ae;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }

    /* 지표 카드 */
    .metric-card {
        background: linear-gradient(135deg, #1a1f2e, #1e2535);
        border: 1px solid #2a3450;
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); }
    .metric-label { color: #78909c; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 0.3rem; }
    .metric-value { color: #e3f2fd; font-size: 1.6rem; font-weight: 800; }
    .metric-sub   { color: #4fc3f7; font-size: 0.82rem; margin-top: 0.2rem; }

    /* 섹션 제목 */
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #b3e5fc;
        border-left: 4px solid #4fc3f7;
        padding-left: 0.75rem;
        margin: 1rem 0 0.6rem;
    }

    /* 선택된 지역 배지 */
    .selected-badge {
        display: inline-block;
        background: linear-gradient(135deg, #0277bd, #01579b);
        color: #e1f5fe;
        border-radius: 20px;
        padding: 0.3rem 1rem;
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    /* Streamlit 기본 스타일 재정의 */
    .stMarkdown h3 { color: #b3e5fc; }
    div[data-testid="stHorizontalBlock"] { gap: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# 데이터 로드 (캐시)
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)


@st.cache_data
def load_geojson(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def prepare_province_geo(path: str) -> dict:
    """GeoJSON을 로드하고 한국어 이름·인구 데이터를 미리 주입해 캐싱.
    원본 객체를 수정하지 않고 새 dict 을 반환한다."""
    raw = load_geojson(path)
    pop_map = PROVINCE_POPULATION
    features = []
    for f in raw["features"]:
        props = dict(f["properties"])   # 얕은 복사로 원본 보호
        name_en = props.get("NAME_1", "")
        pop = pop_map.get(name_en, 0)
        props["name_ko"] = PROVINCE_KO.get(name_en, name_en)
        props["population_fmt"] = f"{pop:,} 명"
        props["population_10k"] = f"{pop / 10_000:.1f} 만 명"
        features.append({**f, "properties": props})
    return {"type": "FeatureCollection", "features": features}


@st.cache_data
def prepare_muni_geo(path: str, province_en: str) -> dict:
    """시도에 해당하는 시군구 GeoJSON만 필터링하고 데이터 주입 후 캐싱."""
    raw = load_geojson(path)
    features = []
    for f in raw["features"]:
        if f["properties"].get("NAME_1", "") != province_en:
            continue
        props = dict(f["properties"])
        name_en2 = props.get("NAME_2", "")
        pop = MUNICIPALITY_POPULATION.get((province_en, name_en2), 0)
        props["name_ko"] = MUNICIPALITY_KO.get((province_en, name_en2), name_en2)
        props["population_fmt"] = f"{pop:,} 명"
        props["population_10k"] = f"{pop / 10_000:.1f} 만 명"
        features.append({**f, "properties": props})
    return {"type": "FeatureCollection", "features": features}


@st.cache_data
def build_province_df() -> pd.DataFrame:
    rows = []
    for name_en, pop in PROVINCE_POPULATION.items():
        rows.append(
            {
                "name_en": name_en,
                "name_ko": PROVINCE_KO.get(name_en, name_en),
                "population": pop,
            }
        )
    df = pd.DataFrame(rows)
    df = df.sort_values("population", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    df["pop_fmt"] = df["population"].apply(lambda x: f"{x:,}")
    df["pop_10k"] = (df["population"] / 10_000).round(1)
    return df


@st.cache_data
def build_municipality_df(province_en: str) -> pd.DataFrame:
    rows = []
    for (prov, muni), pop in MUNICIPALITY_POPULATION.items():
        if prov == province_en:
            rows.append(
                {
                    "province_en": prov,
                    "name_en": muni,
                    "name_ko": MUNICIPALITY_KO.get((prov, muni), muni),
                    "population": pop,
                }
            )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = df.sort_values("population", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    df["pop_fmt"] = df["population"].apply(lambda x: f"{x:,}")
    df["pop_10k"] = (df["population"] / 10_000).round(1)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Folium 지도 생성 함수
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def make_province_map(geo_path: str, selected: str | None) -> folium.Map:
    """시도별 인구 Choropleth + 클릭/호버 GeoJson 레이어.
    @st.cache_resource 사용 → folium.Map 직렬화 없이 캐싱.
    인자를 경로 문자열로만 받아 해시 가능하게 처리."""
    province_geo = prepare_province_geo(geo_path)
    m = folium.Map(
        location=[36.5, 127.8],
        zoom_start=7,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    pop_map = PROVINCE_POPULATION
    max_pop = max(pop_map.values())

    def style_fn(feature):
        name = feature["properties"].get("NAME_1", "")
        pop = pop_map.get(name, 0)
        ratio = pop / max_pop if max_pop > 0 else 0
        if ratio > 0.7:   fill = "#0d47a1"
        elif ratio > 0.5: fill = "#1565c0"
        elif ratio > 0.35:fill = "#1976d2"
        elif ratio > 0.2: fill = "#1e88e5"
        elif ratio > 0.1: fill = "#42a5f5"
        elif ratio > 0.05:fill = "#90caf9"
        else:             fill = "#bbdefb"
        if name == selected:
            return {"fillColor": "#f4d03f", "color": "#f39c12",
                    "weight": 3, "fillOpacity": 0.85}
        return {"fillColor": fill, "color": "#263238",
                "weight": 1, "fillOpacity": 0.75}

    def highlight_fn(feature):
        return {"fillOpacity": 1.0, "weight": 3, "color": "#ffffff"}

    folium.GeoJson(
        province_geo,
        name="시도별 인구",
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["name_ko", "population_10k", "population_fmt"],
            aliases=["📍 지역", "👥 인구 (만)", "🔢 상세"],
            localize=True,
            sticky=False,
            style=(
                "background-color: #1a2035; color: #e3f2fd; "
                "font-family: 'Noto Sans KR', sans-serif; "
                "font-size: 13px; padding: 8px 12px; "
                "border-radius: 8px; border: 1px solid #3a4a6a;"
            ),
        ),
        popup=folium.GeoJsonPopup(
            fields=["name_ko", "population_fmt"],
            aliases=["지역:", "인구:"],
        ),
    ).add_to(m)

    return m


@st.cache_resource
def make_municipality_map(
    geo_path: str,
    province_en: str,
) -> folium.Map:
    """선택된 시도의 시군구별 인구 지도.
    @st.cache_resource 사용 → folium.Map 직렬화 없이 캐싱.
    인자를 경로·문자열로만 받아 해시 가능하게 처리."""
    muni_geo = prepare_muni_geo(geo_path, province_en)
    if not muni_geo["features"]:
        return None

    pop_map = {f["properties"].get("NAME_2", ""): MUNICIPALITY_POPULATION.get(
        (province_en, f["properties"].get("NAME_2", "")), 0)
        for f in muni_geo["features"]}
    max_pop = max(pop_map.values()) if pop_map else 1

    # 중심 좌표 계산
    all_coords = []
    for f in muni_geo["features"]:
        geom = f["geometry"]
        if geom["type"] == "Polygon":
            all_coords.extend(geom["coordinates"][0])
        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                all_coords.extend(poly[0])
    avg_lat = sum(c[1] for c in all_coords) / len(all_coords) if all_coords else 36.5
    avg_lon = sum(c[0] for c in all_coords) / len(all_coords) if all_coords else 127.8

    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=9,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    def style_fn(feature):
        name = feature["properties"].get("NAME_2", "")
        pop = pop_map.get(name, 0)
        ratio = pop / max_pop if max_pop > 0 else 0
        if ratio > 0.7:
            fill = "#b71c1c"
        elif ratio > 0.5:
            fill = "#c62828"
        elif ratio > 0.35:
            fill = "#d32f2f"
        elif ratio > 0.2:
            fill = "#e53935"
        elif ratio > 0.1:
            fill = "#ef5350"
        elif ratio > 0.05:
            fill = "#ef9a9a"
        else:
            fill = "#ffcdd2"
        return {"fillColor": fill, "color": "#263238", "weight": 1, "fillOpacity": 0.75}

    def highlight_fn(feature):
        return {"fillOpacity": 1.0, "weight": 2.5, "color": "#ffffff"}

    folium.GeoJson(
        muni_geo,
        name="시군구별 인구",
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["name_ko", "population_10k", "population_fmt"],
            aliases=["📍 시군구", "👥 인구 (만)", "🔢 상세"],
            localize=True,
            sticky=False,
            style=(
                "background-color: #1a2035; color: #ffe0e0; "
                "font-family: 'Noto Sans KR', sans-serif; "
                "font-size: 13px; padding: 8px 12px; "
                "border-radius: 8px; border: 1px solid #6a2a2a;"
            ),
        ),
    ).add_to(m)

    return m


# ──────────────────────────────────────────────────────────────────────────────
# 메인 UI
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # 헤더
    st.markdown('<div class="main-header">🗺️ 대한민국 인구 현황</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">출처: 행정안전부 주민등록 인구현황 (2024년 12월 기준) · '
        '지도를 클릭하면 해당 시도의 시군구별 인구를 확인할 수 있습니다.</div>',
        unsafe_allow_html=True,
    )

    # 경로 (make_province_map/make_municipality_map 에 직접 전달)
    province_geo_path = os.path.join(BASE_DIR, "data", "provinces.geojson")
    muni_geo_path     = os.path.join(BASE_DIR, "data", "municipalities.geojson")
    province_df = build_province_df()

    # 세션 상태 초기화
    if "selected_province" not in st.session_state:
        st.session_state.selected_province = None
    if "_last_map_click" not in st.session_state:
        st.session_state._last_map_click = None   # 클릭 중복 방지용

    # ── 상단 집계 지표 ──────────────────────────────────────────────────────
    total_pop = province_df["population"].sum()
    top_prov = province_df.iloc[0]
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">전국 총 인구</div>'
            f'<div class="metric-value">{total_pop / 10_000:,.0f}<small style="font-size:1rem"> 만</small></div>'
            f'<div class="metric-sub">{total_pop:,} 명</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_m2:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">인구 최다 시도</div>'
            f'<div class="metric-value">{top_prov["name_ko"]}</div>'
            f'<div class="metric-sub">{top_prov["pop_10k"]:,} 만 명</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_m3:
        bottom_prov = province_df.iloc[-1]
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">인구 최소 시도</div>'
            f'<div class="metric-value">{bottom_prov["name_ko"]}</div>'
            f'<div class="metric-sub">{bottom_prov["pop_10k"]:,} 만 명</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_m4:
        avg_pop = province_df["population"].mean()
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">시도 평균 인구</div>'
            f'<div class="metric-value">{avg_pop / 10_000:,.0f}<small style="font-size:1rem"> 만</small></div>'
            f'<div class="metric-sub">16개 시도 기준</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── 시도 드롭다운 선택 (지도 클릭 대안) ────────────────────────────────
    province_options = ["전체 보기"] + [
        f"{row['name_ko']} ({row['name_en']})" for _, row in province_df.iterrows()
    ]
    sel_idx = 0
    if st.session_state.selected_province:
        try:
            name_ko = PROVINCE_KO.get(st.session_state.selected_province, "")
            name_en = st.session_state.selected_province
            match = f"{name_ko} ({name_en})"
            if match in province_options:
                sel_idx = province_options.index(match)
        except Exception:
            pass

    selected_label = st.selectbox(
        "🔍 시도 직접 선택 (또는 아래 지도를 클릭)",
        province_options,
        index=sel_idx,
        key="selectbox_province",
    )
    if selected_label != "전체 보기":
        # "서울특별시 (Seoul)" → "Seoul"
        name_en = selected_label.split("(")[-1].rstrip(")")
        st.session_state.selected_province = name_en
    else:
        if selected_label == "전체 보기":
            st.session_state.selected_province = None

    # ── 메인 지도 + 시도별 차트 ──────────────────────────────────────────
    col_map, col_chart = st.columns([3, 2], gap="medium")

    with col_map:
        st.markdown('<div class="section-title">📌 시도별 인구 분포 지도</div>', unsafe_allow_html=True)
        st.caption("지도 위에 마우스를 올리면 인구가 표시되고, 클릭하면 해당 시도를 선택합니다.")

        prov_map = make_province_map(
            province_geo_path,
            st.session_state.selected_province,
        )
        map_data = st_folium(
            prov_map,
            width="100%",
            height=520,
            returned_objects=["last_object_clicked_popup"],
            key="province_map",
        )

        # ── 클릭 이벤트 처리 (st.rerun() 제거 → 무한 루프 방지) ──────────
        clicked = map_data.get("last_object_clicked_popup")
        if clicked and clicked != st.session_state._last_map_click:
            # 이번 클릭이 이전과 다를 때만 처리 (중복 방지)
            st.session_state._last_map_click = clicked
            for name_en, name_ko in PROVINCE_KO.items():
                if name_ko in str(clicked):
                    st.session_state.selected_province = name_en
                    # selectbox index 동기화를 위해 selectbox key 리셋
                    break

    with col_chart:
        st.markdown('<div class="section-title">📊 시도별 인구 순위</div>', unsafe_allow_html=True)

        fig_bar = px.bar(
            province_df.sort_values("population"),
            x="population",
            y="name_ko",
            orientation="h",
            text="pop_10k",
            color="population",
            color_continuous_scale="Blues",
            labels={"population": "인구 수", "name_ko": "시도"},
            height=520,
        )
        fig_bar.update_traces(
            texttemplate="%{text:.0f}만",
            textposition="outside",
            marker_line_width=0,
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,17,23,0.6)",
            font=dict(color="#cfd8dc", size=11),
            coloraxis_showscale=False,
            margin=dict(l=10, r=60, t=10, b=10),
            xaxis=dict(gridcolor="#263238", gridwidth=0.5, zeroline=False),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        # 선택된 지역 강조 색상
        if st.session_state.selected_province:
            sel = st.session_state.selected_province
            colors = [
                "#f4d03f" if row["name_en"] == sel else "#1565c0"
                for _, row in province_df.sort_values("population").iterrows()
            ]
            # coloraxis는 layout에서 제거, trace에는 marker_color만 설정
            fig_bar.update_traces(marker_color=colors)
            fig_bar.update_layout(coloraxis=None)

        st.plotly_chart(fig_bar, use_container_width=True)

    # ── 파이차트 ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🥧 수도권 vs 비수도권 인구 비율</div>', unsafe_allow_html=True)
    cap_provinces = {"Seoul", "Incheon", "Gyeonggi-do"}
    cap_pop = sum(v for k, v in PROVINCE_POPULATION.items() if k in cap_provinces)
    non_cap_pop = total_pop - cap_pop

    col_pie, col_treemap = st.columns(2)
    with col_pie:
        fig_pie = px.pie(
            names=["수도권\n(서울·인천·경기)", "비수도권"],
            values=[cap_pop, non_cap_pop],
            color_discrete_sequence=["#1e88e5", "#546e7a"],
            hole=0.42,
        )
        fig_pie.update_traces(
            textinfo="label+percent",
            textfont_size=13,
            pull=[0.05, 0],
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cfd8dc"),
            showlegend=False,
            margin=dict(l=10, r=10, t=20, b=10),
            height=320,
            annotations=[
                dict(
                    text=f"<b>{cap_pop / total_pop * 100:.1f}%</b>",
                    x=0.5, y=0.5, font_size=22, font_color="#4fc3f7",
                    showarrow=False,
                )
            ],
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_treemap:
        fig_tree = px.treemap(
            province_df,
            path=["name_ko"],
            values="population",
            color="population",
            color_continuous_scale="Blues",
            custom_data=["pop_10k"],
        )
        fig_tree.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[0]:.0f}만",
            textfont_size=12,
            marker_line_width=1,
            marker_line_color="#0f1117",
        )
        fig_tree.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cfd8dc"),
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=10, b=0),
            height=320,
        )
        st.plotly_chart(fig_tree, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════
    # 시군구 상세 섹션 (선택된 시도가 있을 때)
    # ══════════════════════════════════════════════════════════════════════
    if st.session_state.selected_province:
        sel_en = st.session_state.selected_province
        sel_ko = PROVINCE_KO.get(sel_en, sel_en)
        muni_df = build_municipality_df(sel_en)

        st.markdown("---")
        st.markdown(
            f'<div class="section-title">🔎 {sel_ko} · 시군구별 상세 현황</div>',
            unsafe_allow_html=True,
        )

        if muni_df.empty:
            st.info(f"{sel_ko}의 시군구 데이터가 없습니다.")
        else:
            muni_total = muni_df["population"].sum()

            # 시군구 집계 지표
            cm1, cm2, cm3, cm4 = st.columns(4)
            with cm1:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">{sel_ko} 총 인구</div>'
                    f'<div class="metric-value">{muni_total / 10_000:,.0f}<small style="font-size:1rem"> 만</small></div>'
                    f'<div class="metric-sub">{muni_total:,} 명</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with cm2:
                top_m = muni_df.iloc[0]
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">최다 인구 시군구</div>'
                    f'<div class="metric-value">{top_m["name_ko"]}</div>'
                    f'<div class="metric-sub">{top_m["pop_10k"]:,} 만 명</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with cm3:
                bot_m = muni_df.iloc[-1]
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">최소 인구 시군구</div>'
                    f'<div class="metric-value">{bot_m["name_ko"]}</div>'
                    f'<div class="metric-sub">{bot_m["pop_10k"]:,} 만 명</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with cm4:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">시군구 수</div>'
                    f'<div class="metric-value">{len(muni_df)}<small style="font-size:1rem"> 개</small></div>'
                    f'<div class="metric-sub">전국 대비 {muni_total / total_pop * 100:.1f}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            col_mmap, col_mchart = st.columns([3, 2], gap="medium")

            with col_mmap:
                st.markdown(
                    f'<div class="section-title">🗺️ {sel_ko} 시군구 지도</div>',
                    unsafe_allow_html=True,
                )
                muni_map = make_municipality_map(muni_geo_path, sel_en)
                if muni_map:
                    st_folium(muni_map, width="100%", height=460, key="municipality_map")
                else:
                    st.warning("해당 시도의 지도 데이터를 불러올 수 없습니다.")

            with col_mchart:
                st.markdown(
                    f'<div class="section-title">📊 {sel_ko} 시군구별 인구</div>',
                    unsafe_allow_html=True,
                )
                fig_mbar = px.bar(
                    muni_df.sort_values("population"),
                    x="population",
                    y="name_ko",
                    orientation="h",
                    text="pop_10k",
                    color="population",
                    color_continuous_scale="Reds",
                    labels={"population": "인구 수", "name_ko": "시군구"},
                    height=460,
                )
                fig_mbar.update_traces(
                    texttemplate="%{text:.1f}만",
                    textposition="outside",
                    marker_line_width=0,
                )
                fig_mbar.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,17,23,0.6)",
                    font=dict(color="#cfd8dc", size=10),
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=60, t=10, b=10),
                    xaxis=dict(gridcolor="#263238", gridwidth=0.5, zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig_mbar, use_container_width=True)

            # 시군구 상세 테이블
            st.markdown(
                f'<div class="section-title">📋 {sel_ko} 시군구별 인구 상세표</div>',
                unsafe_allow_html=True,
            )
            table_df = muni_df[["rank", "name_ko", "pop_fmt", "pop_10k"]].copy()
            table_df.columns = ["순위", "시군구명", "인구 (명)", "인구 (만 명)"]
            table_df["인구 비율"] = (muni_df["population"] / muni_total * 100).map("{:.1f}%".format)
            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True,
                height=min(400, len(table_df) * 38 + 42),
            )

    # ── 전체 시도 표 ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-title">📋 전국 시도별 인구 현황표</div>', unsafe_allow_html=True)
    full_table = province_df[["rank", "name_ko", "pop_fmt", "pop_10k"]].copy()
    full_table.columns = ["순위", "시도명", "인구 (명)", "인구 (만 명)"]
    full_table["전국 비율"] = (province_df["population"] / total_pop * 100).map("{:.2f}%".format)
    st.dataframe(full_table, use_container_width=True, hide_index=True)

    # 푸터
    st.markdown(
        """
        <div style="text-align:center; color:#546e7a; font-size:0.78rem; margin-top:2rem; padding:1rem 0;">
            📊 데이터 출처: 행정안전부 주민등록 인구현황 (2024년 12월 기준) ·
            지도: southkorea/southkorea-maps (CC BY 3.0)
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
