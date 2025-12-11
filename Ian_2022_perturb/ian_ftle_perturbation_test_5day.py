#!/usr/bin/env python3
"""
Hurricane Ian 2022 - FTLE-Guided Cloud Seeding Perturbation Test (5-DAY LEAD)

Extended lead time test: 5 days instead of 3 days.
This provides more time for perturbation effects to propagate and influence TC track.

Initialization: 5-day lead time (Sep 23, 2022 18:00 UTC)
Target: Sep 28, 2022 landfall (Florida)

Key differences from 3-day test:
- Longer forecast (19 steps = 114 hours vs 11 steps = 66 hours)
- TC initialized at earlier position (14.60°N, 289.40°E)
- More time for steering flow modifications to develop

Author: Adapted from ian_ftle_perturbation_test.py (3-day)
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
from seeding_location_selection import select_seeding_candidates, create_seeding_locations_from_candidates, print_seeding_locations
from cloud_seeding_perturbation import (
    create_seeding_mask,
    apply_physically_consistent_cloud_seeding,
    print_diagnostics
)

from shared.data_loading import load_era5_data, create_aurora_batch
from shared.forecasting import run_forecast
from aurora import Aurora, Tracker
from TC.TC_utils import extract_track_from_tracker, load_ibtracs_track


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


def plot_seeding_locations_map(seeding_locations, ftle_field, ftle_lats, ftle_lons,
                               tc_init_lat, tc_init_lon, save_path):
    """Create map showing FTLE field, seeding locations, and TC initial position."""
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

    tc_init_lon_W = 360 - tc_init_lon if tc_init_lon > 180 else -tc_init_lon
    ax.plot(tc_init_lon, tc_init_lat,
           'g*', markersize=25, markeredgecolor='black', markeredgewidth=2,
           transform=ccrs.PlateCarree(),
           label=f'TC Initial Position\n({tc_init_lat:.1f}°N, {abs(tc_init_lon_W):.1f}°W)',
           zorder=10)

    if len(seeding_locations) > 0:
        coord_text = '\n'.join([f"  {loc['lat_center']:.2f}°N, {360 - loc['lon_center']:.2f}°W"
                                for loc in seeding_locations])
        legend_label = f"Perturbation Sites:\n{coord_text}"
    else:
        legend_label = "Perturbation Sites"

    for i, loc in enumerate(seeding_locations, 1):
        ax.plot(loc['lon_center'], loc['lat_center'],
               'k*', markersize=15, markeredgecolor='yellow', markeredgewidth=2,
               transform=ccrs.PlateCarree(),
               label=legend_label if i == 1 else '',
               zorder=11)

        n_points = 100
        lat_center = loc['lat_center']
        lon_center = loc['lon_center']
        radius_km = loc['radius_km']

        radius_lat = radius_km / 111.0
        radius_lon = radius_km / (111.0 * np.cos(np.deg2rad(lat_center)))

        theta = np.linspace(0, 2*np.pi, n_points)
        circle_lons = lon_center + radius_lon * np.cos(theta)
        circle_lats = lat_center + radius_lat * np.sin(theta)

        ax.plot(circle_lons, circle_lats,
               color='black', linewidth=2, linestyle='--',
               transform=ccrs.PlateCarree(), zorder=10)

        ax.text(loc['lon_center'], loc['lat_center'] + 1.5,
               f"#{i}", fontsize=10, fontweight='bold',
               ha='center', va='bottom',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8),
               transform=ccrs.PlateCarree(), zorder=12)

    ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax.set_title('Ian 2022 (5-day lead) - FTLE Field with Seeding Locations',
                fontsize=13, fontweight='bold', pad=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

    return


def plot_custom_track_comparison(forecast_tracks, obs_track, tc_init_lat, tc_init_lon,
                                  title, save_path, extent=None, seeding_locations=None):
    """Create custom track comparison plot."""
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    fig = plt.figure(figsize=(14, 10))
    ax = plt.subplot(1, 1, 1, projection=ccrs.PlateCarree())

    if extent is not None:
        ax.set_extent(extent, crs=ccrs.PlateCarree())

    ax.coastlines(resolution='50m', linewidth=1.0)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, alpha=0.5)
    ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue', alpha=0.2)

    gl = ax.gridlines(draw_labels=True, dms=False, x_inline=False, y_inline=False,
                     linewidth=0.5, alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False

    tc_init_lon_W = 360 - tc_init_lon if tc_init_lon > 180 else -tc_init_lon
    ax.plot(tc_init_lon, tc_init_lat,
           'g*', markersize=20, markeredgecolor='black', markeredgewidth=2,
           transform=ccrs.PlateCarree(),
           label=f'TC Initial Position\n({tc_init_lat:.1f}°N, {abs(tc_init_lon_W):.1f}°W)',
           zorder=10)

    if obs_track is not None:
        ax.plot(obs_track['lon'], obs_track['lat'],
               'o-', color='#3498DB', markersize=6, linewidth=2.5,
               transform=ccrs.PlateCarree(),
               label='Observation (IBTrACS)',
               zorder=8)

    track_styles = {
        'Baseline Forecast': {'color': '#9B59B6', 'marker': 'o', 'markersize': 6, 'zorder': 6},
        'FTLE-Seeded Perturbed': {'color': '#E74C3C', 'marker': '*', 'markersize': 10, 'zorder': 7}
    }

    for label, track in forecast_tracks.items():
        style = track_styles.get(label, {'color': 'gray', 'marker': 'o', 'markersize': 6, 'zorder': 5})
        ax.plot(track['lon'], track['lat'],
               marker=style['marker'], markersize=style['markersize'],
               color=style['color'], linewidth=2,
               transform=ccrs.PlateCarree(),
               label=label,
               zorder=style['zorder'])

    if seeding_locations is not None and len(seeding_locations) > 0:
        for i, loc in enumerate(seeding_locations):
            ax.plot(loc['lon_center'], loc['lat_center'],
                   '*', markersize=12, color='black',
                   markeredgecolor='yellow', markeredgewidth=1.5,
                   transform=ccrs.PlateCarree(),
                   label='Perturbation Sites' if i == 0 else '',
                   zorder=9)

    ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
    ax.legend(loc='upper left', fontsize=11, framealpha=0.95)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

    return


def main():
    print("=" * 80)
    print("  Hurricane Ian 2022 - FTLE-Guided Cloud Seeding Test (5-DAY LEAD)")
    print("=" * 80)
    print()
    print("Strategy: Extended lead time for better perturbation propagation")
    print("Method: FTLE-targeted cloud seeding (heating + moisture removal)")
    print()

    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    CONFIG = {
        'init_date': '2022-09-23',
        'init_hour': '18',
        'init_lat': 14.60,  # IBTrACS: Sep 23 18:00 UTC
        'init_lon': 289.40,  # -70.60°W = 289.40°E
        'steps': 19,  # 5 days (5*4 - 1 = 19 steps)
        'data_path': Path("/scratch/qhuang62/aurora-extreme-predictability/research/TC/data/era5_ian_2022"),
        'output_dir': Path("/scratch/qhuang62/control_AR_FZ_TC/Ian_2022_perturb/ian_ftle_test_output_5day"),
    }

    CONFIG['output_dir'].mkdir(exist_ok=True, parents=True)

    # TC-adapted seeding configuration
    SEEDING_CONFIG_IAN = {
        'layers_mb': [700.0, 500.0, 300.0],
        'freeze_efficiency': 0.60,
        'fallout_fraction': 0.80,
        'max_removal_fraction': 0.50,
        'energy_method': 'net_realistic',
        'vertical_coupling': False,
        'coupling_factor': 0.3
    }

    # Geographic bounds
    BOUNDS_IAN = {
        'lat': (10, 35),
        'lon': (270, 300)
    }

    print(f"Initialization: {CONFIG['init_date']} {CONFIG['init_hour']}:00 UTC")
    print(f"Ian position: {CONFIG['init_lat']}°N, {CONFIG['init_lon']}°E")
    print(f"Forecast length: {CONFIG['steps']} steps ({CONFIG['steps']*6} hours = {CONFIG['steps']/4:.1f} days)")
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

        # time_idx=11 for Sep 23 18:00 UTC (from ian_stage1_lead_day.py)
        time_idx = 11
    else:
        print("Using single-day ERA5 files...")
        static_ds, surf_ds, atmos_ds = load_era5_data(
            CONFIG['data_path'],
            CONFIG['init_date']
        )
        time_idx = 0

    # Convert longitude if needed
    if surf_ds.longitude.values.min() < 0:
        print("Converting longitude from [-180, 180] to [0, 360]...")
        lon_converted = (surf_ds.longitude.values + 360) % 360
        lon_sort_idx = np.argsort(lon_converted)
        lon_sorted = lon_converted[lon_sort_idx]

        surf_ds = surf_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)
        atmos_ds = atmos_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)
        static_ds = static_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)

        print(f"✓ Longitude range: [{surf_ds.longitude.values.min():.1f}, {surf_ds.longitude.values.max():.1f}]")

    # Filter to Aurora's standard 13 pressure levels
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
    # SELECT PERTURBATION LOCATIONS
    # =========================================================================
    print("=" * 80)
    print("  Step 2: Select FTLE-Guided Perturbation Locations")
    print("=" * 80)
    print()

    selected_lats, selected_lons, selected_scores = select_seeding_candidates(
        ftle_crop, lats_crop, lons_crop,
        ftle_percentile=85,
        geographic_bounds=BOUNDS_IAN,
        min_separation_km=300,
        max_candidates=10
    )

    if len(selected_lats) == 0:
        print("⚠️  No FTLE candidates found! Exiting...")
        return

    from shared.metrics import calculate_distance

    filtered_lats = []
    filtered_lons = []
    filtered_scores = []

    print(f"\nFiltering by distance from TC ({CONFIG['init_lat']}°N, {CONFIG['init_lon']}°E):")
    print(f"  Target range: 500-1500 km (environmental steering region)")

    for lat, lon, score in zip(selected_lats, selected_lons, selected_scores):
        dist = calculate_distance(CONFIG['init_lat'], CONFIG['init_lon'], lat, lon)
        if 500 <= dist <= 1500:
            filtered_lats.append(lat)
            filtered_lons.append(lon)
            filtered_scores.append(score)
            print(f"    ✓ Keep: {lat:.2f}°N, {lon:.2f}°E (distance: {dist:.0f} km)")
        else:
            print(f"    ✗ Skip: {lat:.2f}°N, {lon:.2f}°E (distance: {dist:.0f} km, outside range)")

    selected_lats = filtered_lats[:5]
    selected_lons = filtered_lons[:5]
    selected_scores = filtered_scores[:5]

    if len(selected_lats) == 0:
        print("\n⚠️  No candidates within 500-1500 km of TC! Exiting...")
        return

    print(f"\n✓ Selected {len(selected_lats)} locations within environmental steering region")

    seeding_locations = create_seeding_locations_from_candidates(
        selected_lats, selected_lons,
        selected_indices=list(range(1, len(selected_lats)+1)),
        radius_km=300
    )

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
    print("  Step 4: Run Baseline Forecast (No Perturbation)")
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
        name="Ian Baseline (5-day)",
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
    print("  Step 5: Apply FTLE-Guided Cloud Seeding Perturbation")
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
    print("  Step 6: Run Perturbed Forecast (FTLE-Seeded)")
    print("=" * 80)
    print()

    tracker_seeded = Tracker(
        init_lat=CONFIG['init_lat'],
        init_lon=CONFIG['init_lon'],
        init_time=init_time
    )

    print("Running perturbed forecast...")
    preds_seeded = run_forecast(
        model, batch_seeded, tracker_seeded,
        steps=CONFIG['steps'],
        name="Ian FTLE-Seeded (5-day)",
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

    from shared.metrics import calculate_distance

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

    print("Track Deviations (Baseline vs FTLE-Seeded Perturbed):")
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

    forecast_tracks = {
        'Baseline Forecast': forecast_track_baseline,
        'FTLE-Seeded Perturbed': forecast_track_seeded
    }

    track_plot = CONFIG['output_dir'] / "ian_ftle_track_comparison_5day.png"
    plot_custom_track_comparison(
        forecast_tracks=forecast_tracks,
        obs_track=obs_track_truncated,
        tc_init_lat=CONFIG['init_lat'],
        tc_init_lon=CONFIG['init_lon'],
        title="Ian 2022 - FTLE-Guided Perturbation Test (5-Day Lead)",
        save_path=track_plot,
        extent=[270, 300, 10, 35],
        seeding_locations=seeding_locations
    )
    print(f"✓ Saved track comparison: {track_plot}")

    print("\nCreating seeding location visualization...")
    try:
        plot_seeding_locations_map(
            seeding_locations,
            ftle_crop,
            lats_crop,
            lons_crop,
            CONFIG['init_lat'],
            CONFIG['init_lon'],
            save_path=CONFIG['output_dir'] / "seeding_locations_map_5day.png"
        )
        print(f"✓ Saved seeding map: {CONFIG['output_dir'] / 'seeding_locations_map_5day.png'}")
    except Exception as e:
        print(f"⚠️  Could not create seeding map: {e}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("  ✓ Test Complete!")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • Lead time: 5 days (114 hours)")
    print(f"  • FTLE candidates: {len(seeding_locations)}")
    print(f"  • Seeded area: {seeding_mask.sum()} grid cells")
    print(f"  • Max track deviation: {max(deviations):.1f} km")
    print(f"  • Final track deviation: {deviations[-1]:.1f} km")
    print()

    if deviations[-1] > 50:
        print("✓ SUCCESS: Significant track deviation achieved!")
        print("  Extended lead time allowed perturbation effects to propagate.")
    else:
        print("⚠️  LIMITED SUCCESS: Small track deviation")
        print("  Consider trying:")
        print("    - 7-day lead time (like Sandy)")
        print("    - Different perturbation site selection criteria")
        print("    - Closer perturbation sites (300-800 km from TC)")
    print()


if __name__ == "__main__":
    main()
