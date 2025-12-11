#!/usr/bin/env python3
"""
Generate only the orthographic projection FTLE map
No forecast needed - just visualization of existing data
"""

import sys
from pathlib import Path
import torch
import numpy as np
from datetime import datetime

# Add paths
control_dir = Path(__file__).parent
sys.path.insert(0, str(control_dir))
research_dir = Path("/scratch/qhuang62/aurora-extreme-predictability/research")
sys.path.insert(0, str(research_dir))

from ftle_calculation import calculate_ftle_from_winds, crop_region
from seeding_location_selection import select_seeding_candidates, create_seeding_locations_from_candidates
from shared.data_loading import load_era5_data, create_aurora_batch
from shared.metrics import calculate_distance


def plot_ftle_orthographic(seeding_locations, ftle_field, ftle_lats, ftle_lons,
                           tc_init_lat, tc_init_lon, save_path):
    """
    Create regional FTLE map with YlOrRd colormap - Atlantic basin only.
    """
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from matplotlib.lines import Line2D

    print("=" * 80)
    print("🗺️  Plotting FTLE Map with 3D Orthographic Projection (SPHERE)")
    print("=" * 80)

    # ========== CREATE FIGURE WITH ORTHOGRAPHIC PROJECTION ==========
    # Same layout as coworker but rotated to face Sandy study region
    # Sandy: 12.6°N, 281.6°E = 78.4°W (Atlantic/Caribbean)
    fig, ax = plt.subplots(figsize=(16, 16),
                          subplot_kw={'projection': ccrs.Orthographic(
                              central_longitude=282,     # 282°E = 78°W (Atlantic, same as coworker's format)
                              central_latitude=30)})     # 30°N (same as coworker)

    # Set global extent (entire visible hemisphere)
    ax.set_global()

    # ========== LAYER 1: FTLE FIELD ==========
    print("  Plotting FTLE field...")
    LON_FTLE, LAT_FTLE = np.meshgrid(ftle_lons, ftle_lats)

    # Use YlOrRd colormap (your original)
    vmin = np.percentile(ftle_field, 5)
    vmax = np.percentile(ftle_field, 95)
    levels_ftle = np.linspace(vmin, vmax, 20)

    cf = ax.contourf(LON_FTLE, LAT_FTLE, ftle_field,
                    levels=levels_ftle, cmap='YlOrRd',
                    vmin=vmin, vmax=vmax, extend='both',
                    alpha=0.4,
                    transform=ccrs.PlateCarree(), zorder=1)

    # ========== LAYER 2: MAP FEATURES ==========
    print("  Adding map features...")
    ax.coastlines(resolution='50m', linewidth=1.0, color='black', zorder=6)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, alpha=0.5, zorder=4)
    ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.5, zorder=3)
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue', alpha=0.2, zorder=2)

    # Add gridlines (no labels on orthographic)
    gl = ax.gridlines(linewidth=0.5, color='gray',
                     alpha=0.3, linestyle='--', zorder=7)

    # ========== LAYER 3: TC INITIAL POSITION ==========
    print("  Plotting TC initial position...")
    tc_init_lon_W = 360 - tc_init_lon if tc_init_lon > 180 else -tc_init_lon
    ax.plot(tc_init_lon, tc_init_lat,
           'g*', markersize=25, markeredgecolor='black', markeredgewidth=2,
           transform=ccrs.PlateCarree(),
           zorder=15)

    # ========== LAYER 4: SEEDING POINTS ==========
    print("  Plotting seeding points...")

    for i, loc in enumerate(seeding_locations, 1):
        # Orange circles
        ax.scatter(loc['lon_center'], loc['lat_center'],
                  s=250,
                  c='orange',
                  edgecolors='black',
                  linewidths=2.5,
                  alpha=0.95,
                  transform=ccrs.PlateCarree(),
                  zorder=10,
                  marker='o')

        # White ID labels
        ax.text(loc['lon_center'], loc['lat_center'],
               f"{i}",
               fontsize=11,
               fontweight='bold',
               ha='center',
               va='center',
               color='white',
               transform=ccrs.PlateCarree(),
               zorder=11)

        # NO radius circles - removed per user request

    # ========== TITLE AND COLORBAR ==========
    ax.set_title('Hurricane Sandy 2012 - FTLE Field @ 500 hPa\nSeeding Site Selection in Study Region',
                fontsize=14, fontweight='bold', pad=15)

    cbar_ftle = plt.colorbar(cf, ax=ax, orientation='horizontal',
                            pad=0.05, shrink=0.6, aspect=30)
    cbar_ftle.set_label('FTLE (day⁻¹)', fontsize=11, fontweight='bold')

    # ========== LEGEND ==========
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='orange',
               markersize=12, markeredgecolor='black', markeredgewidth=2,
               label=f'Seeding Candidates (n={len(seeding_locations)})', linestyle='None'),
        Line2D([0], [0], marker='*', color='green', markersize=15,
               markeredgecolor='black', markeredgewidth=2,
               label=f'TC Initial Position ({tc_init_lat:.1f}°N, {abs(tc_init_lon_W):.1f}°W)',
               linestyle='None'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=11, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

    print()
    print("=" * 80)
    print("✅ Visualization Complete!")
    print("=" * 80)
    print(f"\n📁 Saved: {save_path}")
    print("=" * 80)


def main():
    print("=" * 80)
    print("  FTLE Orthographic Projection - Visualization Only")
    print("=" * 80)
    print()

    # Configuration
    CONFIG = {
        'init_date': '2012-10-23',
        'init_hour': '00',
        'init_lat': 12.6,
        'init_lon': 281.6,
        'data_path': Path("/scratch/qhuang62/aurora-extreme-predictability/research/TC/data/era5_sandy_2012"),
        'output_dir': Path("/scratch/qhuang62/control_AR_FZ_TC/sandy_ftle_test_output"),
    }

    CONFIG['output_dir'].mkdir(exist_ok=True, parents=True)

    BOUNDS_SANDY = {
        'lat': (0, 35),
        'lon': (260, 300)
    }

    print(f"Loading ERA5 data for {CONFIG['init_date']}...")

    # Load data
    static_ds, surf_ds, atmos_ds = load_era5_data(
        CONFIG['data_path'],
        CONFIG['init_date']
    )

    # Convert longitude if needed
    if surf_ds.longitude.values.min() < 0:
        lon_converted = (surf_ds.longitude.values + 360) % 360
        lon_sort_idx = np.argsort(lon_converted)
        lon_sorted = lon_converted[lon_sort_idx]
        surf_ds = surf_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)
        atmos_ds = atmos_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)
        static_ds = static_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)

    # Filter to Aurora levels
    AURORA_LEVELS = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000]
    atmos_ds = atmos_ds.sel(pressure_level=AURORA_LEVELS)

    # Create batch
    batch = create_aurora_batch(static_ds, surf_ds, atmos_ds, time_start_idx=0)

    lats = batch.metadata.lat.cpu().numpy()
    lons = batch.metadata.lon.cpu().numpy()
    pressure_levels = list(batch.metadata.atmos_levels)

    print(f"✓ Grid: {len(lats)} lats × {len(lons)} lons")
    print()

    # Calculate FTLE on GLOBAL domain (whole sphere)
    print("Calculating FTLE at 500 hPa (GLOBAL DOMAIN)...")
    level_500_idx = pressure_levels.index(500.0)
    u_500 = batch.atmos_vars["u"][0, 1, level_500_idx].cpu().numpy()
    v_500 = batch.atmos_vars["v"][0, 1, level_500_idx].cpu().numpy()

    ftle_field_global, final_positions = calculate_ftle_from_winds(
        u_500, v_500, lats, lons,
        dt_hours=6,
        integration_time_hours=48,
        direction='forward'
    )

    print(f"✓ Global FTLE range: [{np.nanmin(ftle_field_global):.4f}, {np.nanmax(ftle_field_global):.4f}] day⁻¹")
    print()

    # Crop ONLY for site selection (Atlantic region)
    print("Cropping Atlantic region for site selection...")
    ftle_crop, lats_crop, lons_crop = crop_region(
        ftle_field_global, lats, lons,
        lat_range=(BOUNDS_SANDY['lat'][0], BOUNDS_SANDY['lat'][1]),
        lon_range=(BOUNDS_SANDY['lon'][0], BOUNDS_SANDY['lon'][1])
    )

    print(f"✓ Atlantic FTLE range: [{np.min(ftle_crop):.4f}, {np.max(ftle_crop):.4f}] day⁻¹")
    print()

    # Select seeding locations from Atlantic region
    print("Selecting seeding locations (from Atlantic region)...")
    selected_lats, selected_lons, selected_scores = select_seeding_candidates(
        ftle_crop, lats_crop, lons_crop,
        ftle_percentile=85,
        geographic_bounds=BOUNDS_SANDY,
        min_separation_km=300,
        max_candidates=10
    )

    # Filter by TC distance
    filtered_lats = []
    filtered_lons = []

    for lat, lon, score in zip(selected_lats, selected_lons, selected_scores):
        dist = calculate_distance(CONFIG['init_lat'], CONFIG['init_lon'], lat, lon)
        if 500 <= dist <= 1500:
            filtered_lats.append(lat)
            filtered_lons.append(lon)

    selected_lats = filtered_lats[:3]
    selected_lons = filtered_lons[:3]

    seeding_locations = create_seeding_locations_from_candidates(
        selected_lats, selected_lons,
        selected_indices=list(range(1, len(selected_lats)+1)),
        radius_km=300
    )

    print(f"✓ Selected {len(seeding_locations)} seeding locations")
    for i, loc in enumerate(seeding_locations, 1):
        print(f"  Site {i}: {loc['lat_center']:.2f}°N, {loc['lon_center']:.2f}°E")
    print()

    # Create plot with GLOBAL FTLE field
    save_path = CONFIG['output_dir'] / "seeding_locations_map_orthographic.png"
    plot_ftle_orthographic(
        seeding_locations,
        ftle_field_global,  # Use GLOBAL field for plotting
        lats,               # Use GLOBAL lats
        lons,               # Use GLOBAL lons
        CONFIG['init_lat'],
        CONFIG['init_lon'],
        save_path
    )


if __name__ == "__main__":
    main()
