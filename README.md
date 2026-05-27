# 🗺️ 대한민국 인구 현황 대시보드

행정안전부 주민등록 인구현황(2024년 12월 기준) 데이터를 활용하여  
대한민국 각 시도 및 시군구별 인구 통계를 인터랙티브 지도와 차트로 시각화합니다.

## ✨ 주요 기능

- **전국 시도별 인구 Choropleth 지도** – 인구 많을수록 진한 색
- **지도 호버(Hover)** – 시도명과 인구 수 툴팁 표시
- **지도 클릭(Click)** – 해당 시도를 선택, 아래 섹션에서 시군구 상세 통계 표시
- **드롭다운 선택** – 지도 외에도 셀렉트박스로 시도 선택 가능
- **시군구별 지도** – 선택한 시도의 구/시/군별 인구 분포 (빨간 계열 Choropleth)
- **수도권 vs 비수도권** 파이차트 & 트리맵
- **시도·시군구별 가로 막대 차트** 및 상세 테이블

## 🚀 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📊 데이터 출처

- 인구 데이터: [행정안전부 주민등록 인구현황](https://jumin.mois.go.kr) (2024년 12월 기준)
- 행정구역 GeoJSON: [southkorea/southkorea-maps](https://github.com/southkorea/southkorea-maps) (CC BY 3.0)

## 🛠️ 기술 스택

| 라이브러리 | 용도 |
|---|---|
| Streamlit | 웹 앱 프레임워크 |
| Folium | 인터랙티브 지도 |
| streamlit-folium | Folium → Streamlit 연동 |
| Plotly | 차트 시각화 |
| Pandas | 데이터 처리 |

## 📁 디렉터리 구조

```
streamlit-korea/
├── app.py                    # 메인 Streamlit 앱
├── requirements.txt
├── README.md
└── data/
    ├── population_data.py    # 시도·시군구 인구 데이터
    ├── provinces.geojson     # 시도 경계 GeoJSON
    └── municipalities.geojson # 시군구 경계 GeoJSON
```
