# -*- coding: utf-8 -*-
"""GeoJSON 단순화 스크립트 - tolerance=0.005"""
import geopandas as gpd
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TOLERANCE = 0.005

def simplify(src, dst):
    print(f"읽기: {src}")
    gdf = gpd.read_file(src)
    before = os.path.getsize(src) / 1024 / 1024
    print(f"  원본 크기: {before:.1f} MB, 피처 수: {len(gdf)}")

    # 단순화 (preserve_topology=True: 인접 경계 유지)
    gdf["geometry"] = gdf["geometry"].simplify(TOLERANCE, preserve_topology=True)

    gdf.to_file(dst, driver="GeoJSON")
    after = os.path.getsize(dst) / 1024 / 1024
    print(f"  단순화 후 크기: {after:.1f} MB ({after/before*100:.0f}%)")
    print(f"  저장: {dst}")

simplify(
    os.path.join(DATA_DIR, "provinces.geojson"),
    os.path.join(DATA_DIR, "provinces_simple.geojson"),
)
simplify(
    os.path.join(DATA_DIR, "municipalities.geojson"),
    os.path.join(DATA_DIR, "municipalities_simple.geojson"),
)
print("\n완료!")
