#!/usr/bin/env python3
"""
Hurricane Ian 2022 - FTLE-Guided Cloud Seeding (TARGETED CLUSTER)

Based on 5-day test findings: Site 2 showed promise (37.3 km deviation).
This script creates a denser cluster of perturbation sites around the effective region.

Strategy:
1. Identify effective FTLE region from 5-day test
2. Create multiple perturbation sites in that cluster
3. Use closer distance range (300-800 km from TC)
4. Test if concentrated seeding amplifies the effect

Initialization: 5-day lead time (Sep 23, 2022 18:00 UTC)
Target: Sep 28, 2022 landfall (Florida)

Author: Adapted from ian_ftle_perturbation_test_5day.py
Date: 2025-12-04
"""

import sys
from pathlib import Path
import torch
import numpy as np
from datetime import datetime
import xarray as xr

# Add paths
control_dir = Path(__file__).parent.parent
sys.path.insert(0, str(control_dir))
research_dir = Path("/scratch/qhuang62/aurora-extreme-predictability/research")
sys.path.insert(0, str(research_dir))

# Import utilities
from ftle_calculation import calculate_ftle_from_winds, crop_region
from seeding_location_selection import create_seeding_locations_from_candidates, print_seeding_locations
from cloud_seeding_perturbation import (
    create_seeding_mask,
    apply_physically_consistent_cloud_seeding,
    print_diagnostics
)

from shared.data_loading import load_era5_data, create_aurora_batch
from shared.forecasting import run_forecast
from aurora import Aurora, Tracker
from TC.TC_utils import extract_track_from_tracker, load_ibtracs_track
from shared.metrics import calculate_distance


def clone_batch(batch):
    """Create a deep copy of Aurora batch for perturbation."""
    from aurora import Batch
    batch_cloned = Batch(
        surf_vars={k: v.clone() for k, v in batch.surf_vars.items()},
        atmos_vars={k: v.clone() for k, v in batch.atmos_vars.items()},
        static_vars={k: v.clone() for k, v in batch.static_vars.items()},
        metadata=batch.metadata
    ).to(batch.surf_vars['2t'].device)
    return batch_cloned


def create_targeted_cluster(center_lat, center_lon, ftle_field, lats_ftle, lons_ftle,
                            tc_lat, tc_lon, cluster_radius_km=400, n_sites=5):
    """
    Create a cluster of perturbation sites around an effective center location.

    Parameters
    ----------
    center_lat, center_lon : float
        Center of the effective region (from previous test)
    ftle_field : ndarray
        FTLE field for scoring
    lats_ftle, lons_ftle : ndarray
        Coordinate arrays for FTLE field
    tc_lat, tc_lon : float
        TC position for distance filtering
    cluster_radius_km : float
        Radius to search for cluster sites
    n_sites : int
        Number of sites to create in cluster

    Returns
    -------
    list of dicts
        Seeding locations
    """

    print(f"Creating targeted cluster around: {center_lat:.2f}°N, {center_lon:.2f}°E")
    print(f"  Cluster radius: {cluster_radius_km} km")
    print(f"  Number of sites: {n_sites}")
    print()

    # Find all grid points within cluster radius
    cluster_lats = []
    cluster_lons = []
    cluster_scores = []

    for i, lat in enumerate(lats_ftle):
        for j, lon in enumerate(lons_ftle):
            dist_from_center = calculate_distance(center_lat, center_lon, lat, lon)

            if dist_from_center <= cluster_radius_km:
                # Distance from TC
                dist_from_tc = calculate_distance(tc_lat, tc_lon, lat, lon)

                # Keep if within 300-1000 km from TC
                if 300 <= dist_from_tc <= 1000:
                    ftle_score = ftle_field[i, j]
                    if not np.isnan(ftle_score):
                        cluster_lats.append(lat)
                        cluster_lons.append(lon)
                        cluster_scores.append(ftle_score)

    print(f"  Found {len(cluster_lats)} candidate points in cluster")

    if len(cluster_lats) == 0:
        print("  ⚠️  No valid points found in cluster!")
        return []

    # Sort by FTLE score (highest first)
    sorted_idx = np.argsort(cluster_scores)[::-1]

    # Select top n_sites with minimum separation
    selected_lats = []
    selected_lons = []
    min_sep = 150  # km (half of normal separation for denser cluster)

    for idx in sorted_idx:
        lat = cluster_lats[idx]
        lon = cluster_lons[idx]

        # Check separation from already selected sites
        too_close = False
        for sel_lat, sel_lon in zip(selected_lats, selected_lons):
            if calculate_distance(lat, lon, sel_lat, sel_lon) < min_sep:
                too_close = True
                break

        if not too_close:
            selected_lats.append(lat)
            selected_lons.append(lon)
            dist_from_tc = calculate_distance(tc_lat, tc_lon, lat, lon)
            dist_from_center = calculate_distance(center_lat, center_lon, lat, lon)
            print(f"    Site {len(selected_lats)}: {lat:.2f}°N, {lon:.2f}°E "
                  f"(TC: {dist_from_tc:.0f} km, Center: {dist_from_center:.0f} km)")

            if len(selected_lats) >= n_sites:
                break

    print()

    # Create seeding locations with smaller radius (200 km for denser coverage)
    seeding_locations = create_seeding_locations_from_candidates(
        selected_lats, selected_lons,
        selected_indices=list(range(1, len(selected_lats)+1)),
        radius_km=200  # Smaller radius for denser cluster
    )

    return seeding_locations


def plot_seeding_locations_map(seeding_locations, ftle_field, ftle_lats, ftle_lons,
                               tc_init_lat, tc_init_lon, save_path, center_lat=None, center_lon=None):
    """Create map showing FTLE field, seeding cluster, and effective center."""
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    fig = plt.figure(figsize=(16, 10))
    ax = plt.subplot(1, 1, 1, projection=ccrs.PlateCarree())

    extent = [270, 300, 10, 35]
    ax.set_extent(extent, crs=ccrs.PlateCarree())

    ax.coastlines(resolution='50m', linewidth=1.0)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, alpha=0.5)
    ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.5)
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue', alpha=0.2)

    gl = ax.gridlines(draw_labels=True, dms=False, x_inline=False, y_inline=False,
                     linewidth=0.5, alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False

    LON_FTLE, LAT_FTLE = np.meshgrid(ftle_lons, ftle_lats)
    ftle_plot = ax.contourf(LON_FTLE, LAT_FTLE, ftle_field,
                            levels=20, cmap='YlOrRd', alpha=0.4,
                            transform=ccrs.PlateCarree(),
                            extend='both')
    cbar = plt.colorbar(ftle_plot, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label('FTLE (day⁻¹)', fontsize=11, fontweight='bold')

    # TC position
    tc_init_lon_W = 360 - tc_init_lon if tc_init_lon > 180 else -tc_init_lon
    ax.plot(tc_init_lon, tc_init_lat,
           'g*', markersize=25, markeredgecolor='black', markeredgewidth=2,
           transform=ccrs.PlateCarree(),
           label=f'TC Initial Position\n({tc_init_lat:.1f}°N, {abs(tc_init_lon_W):.1f}°W)',
           zorder=10)

    # Effective center (if provided)
    if center_lat is not None and center_lon is not None:
        ax.plot(center_lon, center_lat,
               'r*', markersize=20, markeredgecolor='white', markeredgewidth=2,
               transform=ccrs.PlateCarree(),
               label=f'Cluster Center\n({center_lat:.1f}°N, {360-center_lon:.1f}°W)',
               zorder=11)

    # Seeding cluster
    for i, loc in enumerate(seeding_locations, 1):
        ax.plot(loc['lon_center'], loc['lat_center'],
               'k*', markersize=12, markeredgecolor='yellow', markeredgewidth=1.5,
               transform=ccrs.PlateCarree(),
               label='Seeding Cluster' if i == 1 else '',
               zorder=11)

        # Smaller circles for cluster
        n_points = 50
        lat_center = loc['lat_center']
        lon_center = loc['lon_center']
        radius_km = loc['radius_km']

        radius_lat = radius_km / 111.0
        radius_lon = radius_km / (111.0 * np.cos(np.deg2rad(lat_center)))

        theta = np.linspace(0, 2*np.pi, n_points)
        circle_lons = lon_center + radius_lon * np.cos(theta)
        circle_lats = lat_center + radius_lat * np.sin(theta)

        ax.plot(circle_lons, circle_lats,
               color='black', linewidth=1.5, linestyle='--',
               transform=ccrs.PlateCarree(), zorder=10)

        ax.text(loc['lon_center'], loc['lat_center'] + 0.8,
               f"#{i}", fontsize=9, fontweight='bold',
               ha='center', va='bottom',
               bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.8),
               transform=ccrs.PlateCarree(), zorder=12)

    ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax.set_title('Ian 2022 - Targeted Cluster Seeding (Dense Pattern)',
                fontsize=13, fontweight='bold', pad=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def main():
    print("=" * 80)
    print("  Hurricane Ian 2022 - Targeted Cluster Seeding Test")
    print("=" * 80)
    print()
    print("Strategy: Dense cluster around effective region from 5-day test")
    print("Method: Multiple sites with smaller radius (200 km) for amplified effect")
    print()

    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    CONFIG = {
        'init_date': '2022-09-23',
        'init_hour': '18',
        'init_lat': 14.60,
        'init_lon': 289.40,
        'steps': 19,
        'data_path': Path("/scratch/qhuang62/aurora-extreme-predictability/research/TC/data/era5_ian_2022"),
        'output_dir': Path("/scratch/qhuang62/control_AR_FZ_TC/Ian_2022_perturb/ian_ftle_test_output_targeted"),
    }

    CONFIG['output_dir'].mkdir(exist_ok=True, parents=True)

    # Effective region center (UPDATE THIS based on site 2 from 5-day test)
    # You can get this from the 5-day test output
    CLUSTER_CENTER = {
        'lat': 20.0,  # PLACEHOLDER - update with actual site 2 latitude
        'lon': 285.0,  # PLACEHOLDER - update with actual site 2 longitude
    }

    # Seeding configuration
    SEEDING_CONFIG_IAN = {
        'layers_mb': [700.0, 500.0, 300.0],
        'freeze_efficiency': 0.60,
        'fallout_fraction': 0.80,
        'max_removal_fraction': 0.50,
        'energy_method': 'net_realistic',
        'vertical_coupling': False,
        'coupling_factor': 0.3
    }

    BOUNDS_IAN = {
        'lat': (10, 35),
        'lon': (270, 300)
    }

    print(f"Initialization: {CONFIG['init_date']} {CONFIG['init_hour']}:00 UTC")
    print(f"Ian position: {CONFIG['init_lat']}°N, {CONFIG['init_lon']}°E")
    print(f"Forecast length: {CONFIG['steps']} steps ({CONFIG['steps']*6} hours)")
    print()
    print(f"⭐ Cluster center: {CLUSTER_CENTER['lat']}°N, {CLUSTER_CENTER['lon']}°E")
    print(f"   (Update this with actual site 2 coordinates from 5-day test)")
    print()

    # =========================================================================
    # SETUP MODEL
    # =========================================================================
    print("Loading Aurora model...")
    model = Aurora(use_lora=False)
    model.load_checkpoint("microsoft/aurora", "aurora-0.25-pretrained.ckpt")
    model.eval()

    if torch.cuda.is_available():
        try:
            model = model.to("cuda")
            device = "cuda"
            print(f"✓ Model loaded on GPU")
        except torch.cuda.OutOfMemoryError:
            model = model.to("cpu")
            device = "cpu"
            print("⚠ CUDA OOM, using CPU")
    else:
        model = model.to("cpu")
        device = "cpu"
        print("✓ Model loaded on CPU")
    print()

    # =========================================================================
    # LOAD DATA
    # =========================================================================
    print("Loading ERA5 data...")

    surf_file = CONFIG['data_path'] / 'ian_2022_surface_combined.nc'
    atmos_file = CONFIG['data_path'] / 'ian_2022_atmospheric_combined.nc'

    if surf_file.exists() and atmos_file.exists():
        print("Using combined ERA5 files...")
        static_ds, _, _ = load_era5_data(CONFIG['data_path'], '2022-09-23')
        surf_ds = xr.open_dataset(surf_file)
        atmos_ds = xr.open_dataset(atmos_file)
        time_idx = 11
    else:
        print("Using single-day ERA5 files...")
        static_ds, surf_ds, atmos_ds = load_era5_data(CONFIG['data_path'], CONFIG['init_date'])
        time_idx = 0

    if surf_ds.longitude.values.min() < 0:
        print("Converting longitude from [-180, 180] to [0, 360]...")
        lon_converted = (surf_ds.longitude.values + 360) % 360
        lon_sort_idx = np.argsort(lon_converted)
        lon_sorted = lon_converted[lon_sort_idx]
        surf_ds = surf_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)
        atmos_ds = atmos_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)
        static_ds = static_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)
        print(f"✓ Longitude range: [{surf_ds.longitude.values.min():.1f}, {surf_ds.longitude.values.max():.1f}]")

    AURORA_LEVELS = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000]
    print(f"Filtering to Aurora's 13 standard pressure levels...")
    atmos_ds = atmos_ds.sel(pressure_level=AURORA_LEVELS)
    print(f"✓ Using levels: {list(atmos_ds.pressure_level.values)}")

    batch = create_aurora_batch(static_ds, surf_ds, atmos_ds, time_start_idx=time_idx)
    print(f"✓ Batch created: {batch.atmos_vars['t'].shape}")
    print()

    lats = batch.metadata.lat.cpu().numpy()
    lons = batch.metadata.lon.cpu().numpy()
    pressure_levels = list(batch.metadata.atmos_levels)

    print(f"Grid: {len(lats)} lats × {len(lons)} lons")
    print(f"Pressure levels: {len(pressure_levels)} levels")
    print()

    # =========================================================================
    # CALCULATE FTLE
    # =========================================================================
    print("=" * 80)
    print("  Step 1: Calculate FTLE at Steering Level (500 hPa)")
    print("=" * 80)
    print()

    level_500_idx = pressure_levels.index(500.0)

    u_500 = batch.atmos_vars["u"][0, 1, level_500_idx].cpu().numpy()
    v_500 = batch.atmos_vars["v"][0, 1, level_500_idx].cpu().numpy()

    print(f"500 hPa winds: {u_500.shape}")
    print(f"U range: [{np.min(u_500):.1f}, {np.max(u_500):.1f}] m/s")
    print(f"V range: [{np.min(v_500):.1f}, {np.max(v_500):.1f}] m/s")
    print()

    ftle_field, final_positions = calculate_ftle_from_winds(
        u_500, v_500, lats, lons,
        dt_hours=6,
        integration_time_hours=48,
        direction='forward'
    )

    print()

    ftle_crop, lats_crop, lons_crop = crop_region(
        ftle_field, lats, lons,
        lat_range=(BOUNDS_IAN['lat'][0], BOUNDS_IAN['lat'][1]),
        lon_range=(BOUNDS_IAN['lon'][0], BOUNDS_IAN['lon'][1])
    )

    print(f"✓ Cropped to Gulf/Caribbean: {ftle_crop.shape}")
    print(f"  FTLE range in region: [{np.min(ftle_crop):.4f}, {np.max(ftle_crop):.4f}] day⁻¹")
    print()

    # =========================================================================
    # CREATE TARGETED CLUSTER
    # =========================================================================
    print("=" * 80)
    print("  Step 2: Create Targeted Cluster Around Effective Region")
    print("=" * 80)
    print()

    seeding_locations = create_targeted_cluster(
        center_lat=CLUSTER_CENTER['lat'],
        center_lon=CLUSTER_CENTER['lon'],
        ftle_field=ftle_crop,
        lats_ftle=lats_crop,
        lons_ftle=lons_crop,
        tc_lat=CONFIG['init_lat'],
        tc_lon=CONFIG['init_lon'],
        cluster_radius_km=400,  # 400 km radius around effective center
        n_sites=5  # 5 sites in cluster
    )

    if len(seeding_locations) == 0:
        print("⚠️  No cluster sites created! Check cluster center coordinates.")
        print("   Update CLUSTER_CENTER with actual site 2 from 5-day test.")
        return

    print_seeding_locations(seeding_locations)
    print()

    # =========================================================================
    # CREATE SEEDING MASK
    # =========================================================================
    print("=" * 80)
    print("  Step 3: Create Seeding Mask")
    print("=" * 80)
    print()

    seeding_mask = create_seeding_mask(seeding_locations, lats, lons)

    print(f"Mask shape: {seeding_mask.shape}")
    print(f"Seeded grid cells: {seeding_mask.sum()}")
    print(f"Percentage of domain: {seeding_mask.sum() / seeding_mask.size * 100:.2f}%")
    print()

    # =========================================================================
    # RUN BASELINE FORECAST
    # =========================================================================
    print("=" * 80)
    print("  Step 4: Run Baseline Forecast")
    print("=" * 80)
    print()

    batch_baseline = batch

    init_time = datetime.strptime(f"{CONFIG['init_date']} {CONFIG['init_hour']}:00", "%Y-%m-%d %H:%M")
    tracker_baseline = Tracker(
        init_lat=CONFIG['init_lat'],
        init_lon=CONFIG['init_lon'],
        init_time=init_time
    )

    print("Running baseline forecast...")
    preds_baseline = run_forecast(
        model, batch_baseline, tracker_baseline,
        steps=CONFIG['steps'],
        name="Ian Baseline (Targeted)",
        device=device,
        verbose=True
    )

    forecast_track_baseline = extract_track_from_tracker(tracker_baseline, init_time)
    print(f"✓ Baseline track: {len(forecast_track_baseline['time'])} positions")

    final_lat_baseline = forecast_track_baseline['lat'][-1]
    final_lon_baseline = forecast_track_baseline['lon'][-1]
    print(f"  Final position: {final_lat_baseline:.2f}°N, {final_lon_baseline:.2f}°E")

    print("  Saving baseline predictions...")
    torch.save(preds_baseline, CONFIG['output_dir'] / 'preds_baseline.pt')
    print(f"  ✓ Saved: {CONFIG['output_dir'] / 'preds_baseline.pt'}")
    print()

    # =========================================================================
    # APPLY PERTURBATION
    # =========================================================================
    print("=" * 80)
    print("  Step 5: Apply Targeted Cluster Seeding")
    print("=" * 80)
    print()

    batch_seeded = clone_batch(batch_baseline)

    delta_T, delta_q, diagnostics = apply_physically_consistent_cloud_seeding(
        batch_seeded,
        seeding_mask,
        SEEDING_CONFIG_IAN
    )

    print_diagnostics(diagnostics, SEEDING_CONFIG_IAN)

    # =========================================================================
    # RUN PERTURBED FORECAST
    # =========================================================================
    print("=" * 80)
    print("  Step 6: Run Cluster-Seeded Forecast")
    print("=" * 80)
    print()

    tracker_seeded = Tracker(
        init_lat=CONFIG['init_lat'],
        init_lon=CONFIG['init_lon'],
        init_time=init_time
    )

    print("Running cluster-seeded forecast...")
    preds_seeded = run_forecast(
        model, batch_seeded, tracker_seeded,
        steps=CONFIG['steps'],
        name="Ian Cluster-Seeded",
        device=device,
        verbose=True
    )

    forecast_track_seeded = extract_track_from_tracker(tracker_seeded, init_time)
    print(f"✓ Seeded track: {len(forecast_track_seeded['time'])} positions")

    final_lat_seed = forecast_track_seeded['lat'][-1]
    final_lon_seed = forecast_track_seeded['lon'][-1]
    print(f"  Final position: {final_lat_seed:.2f}°N, {final_lon_seed:.2f}°E")

    print("  Saving seeded predictions...")
    torch.save(preds_seeded, CONFIG['output_dir'] / 'preds_seeded.pt')
    print(f"  ✓ Saved: {CONFIG['output_dir'] / 'preds_seeded.pt'}")
    print()

    # =========================================================================
    # COMPUTE TRACK DEVIATION
    # =========================================================================
    print("=" * 80)
    print("  Step 7: Compute Track Deviation")
    print("=" * 80)
    print()

    min_len = min(len(forecast_track_baseline['lat']), len(forecast_track_seeded['lat']))

    deviations = []
    for i in range(min_len):
        dist = calculate_distance(
            forecast_track_baseline['lat'][i],
            forecast_track_baseline['lon'][i],
            forecast_track_seeded['lat'][i],
            forecast_track_seeded['lon'][i]
        )
        deviations.append(dist)

    print("Track Deviations (Baseline vs Cluster-Seeded):")
    if len(deviations) > 4:
        print(f"  24hr (+4 steps): {deviations[4]:.1f} km")
    if len(deviations) > 8:
        print(f"  48hr (+8 steps): {deviations[8]:.1f} km")
    if len(deviations) > 12:
        print(f"  72hr (+12 steps): {deviations[12]:.1f} km")
    if len(deviations) > 16:
        print(f"  96hr (+16 steps): {deviations[16]:.1f} km")
    print(f"  Final: {deviations[-1]:.1f} km")
    print()

    lat_shift = final_lat_seed - final_lat_baseline
    lon_shift = final_lon_seed - final_lon_baseline
    print(f"Final position shift:")
    print(f"  Latitude: {lat_shift:+.2f}° ({abs(lat_shift)*111:.1f} km {'north' if lat_shift>0 else 'south'})")
    print(f"  Longitude: {lon_shift:+.2f}° ({abs(lon_shift)*111*np.cos(np.deg2rad(final_lat_baseline)):.1f} km {'east' if lon_shift>0 else 'west'})")
    print()

    # Compare with 5-day sparse test
    print(f"Comparison with 5-day sparse test (37.3 km):")
    if deviations[-1] > 37.3:
        improvement = deviations[-1] - 37.3
        print(f"  ✓ IMPROVEMENT: +{improvement:.1f} km ({improvement/37.3*100:.1f}% increase)")
    else:
        decrease = 37.3 - deviations[-1]
        print(f"  ⚠️  DECREASE: -{decrease:.1f} km ({decrease/37.3*100:.1f}% reduction)")
    print()

    # =========================================================================
    # VISUALIZATIONS
    # =========================================================================
    print("=" * 80)
    print("  Step 8: Create Visualizations")
    print("=" * 80)
    print()

    try:
        import pandas as pd
        obs_track = load_ibtracs_track('IAN', 2022)
        valid_indices = [i for i, t in enumerate(obs_track['time'])
                        if init_time <= t <= init_time + pd.Timedelta(days=5, hours=12)]
        obs_track_truncated = {
            'time': [obs_track['time'][i] for i in valid_indices],
            'lat': [obs_track['lat'][i] for i in valid_indices],
            'lon': [obs_track['lon'][i] for i in valid_indices]
        }
    except:
        print("⚠️  Could not load observed track")
        obs_track_truncated = None

    print("\nCreating seeding location visualization...")
    try:
        plot_seeding_locations_map(
            seeding_locations,
            ftle_crop,
            lats_crop,
            lons_crop,
            CONFIG['init_lat'],
            CONFIG['init_lon'],
            save_path=CONFIG['output_dir'] / "seeding_locations_map_targeted.png",
            center_lat=CLUSTER_CENTER['lat'],
            center_lon=CLUSTER_CENTER['lon']
        )
        print(f"✓ Saved seeding map: {CONFIG['output_dir'] / 'seeding_locations_map_targeted.png'}")
    except Exception as e:
        print(f"⚠️  Could not create seeding map: {e}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("  ✓ Targeted Cluster Test Complete!")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • Cluster center: {CLUSTER_CENTER['lat']}°N, {CLUSTER_CENTER['lon']}°E")
    print(f"  • Cluster sites: {len(seeding_locations)}")
    print(f"  • Site radius: 200 km (smaller for denser coverage)")
    print(f"  • Seeded area: {seeding_mask.sum()} grid cells")
    print(f"  • Max track deviation: {max(deviations):.1f} km")
    print(f"  • Final track deviation: {deviations[-1]:.1f} km")
    print(f"  • vs 5-day sparse test: {deviations[-1] - 37.3:+.1f} km")
    print()

    if deviations[-1] > 100:
        print("✓ STRONG SUCCESS: Cluster amplified the effect significantly!")
    elif deviations[-1] > 50:
        print("✓ MODERATE SUCCESS: Cluster improved track deviation")
    else:
        print("⚠️  LIMITED SUCCESS: Cluster did not significantly improve results")
        print("   Consider adjusting cluster center or trying 7-day lead time")
    print()


if __name__ == "__main__":
    main()
