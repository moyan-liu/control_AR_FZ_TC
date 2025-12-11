#!/usr/bin/env python3
"""
Hurricane Sandy 2012 - FTLE-Guided Cloud Seeding Perturbation Test

Adapts Moyan Liu's AR perturbation methodology to tropical cyclones.
Tests whether FTLE-targeted cloud seeding can modify Sandy's track.

Author: Adapted from Moyan Liu's perturbation_trail_111.ipynb
Date: 2025-12-02
"""

import sys
from pathlib import Path
import torch
import numpy as np
from datetime import datetime
import xarray as xr

# Add paths
control_dir = Path(__file__).parent
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
from ivt_analysis import calculate_ivt_trajectory

from shared.data_loading import load_era5_data, create_aurora_batch
from shared.forecasting import run_forecast
from aurora import Aurora, Tracker
from TC.TC_utils import extract_track_from_tracker, compute_track_error, load_ibtracs_track


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
    """
    Create map showing FTLE field, seeding locations, and TC initial position.

    Focused view on seeding region (0-30°N, 260-300°E).
    """
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    fig = plt.figure(figsize=(16, 10))
    ax = plt.subplot(1, 1, 1, projection=ccrs.PlateCarree())

    # Fixed extent for seeding region: 0-30°N, 260-300°E (100°W-60°W)
    extent = [260, 300, 0, 30]
    ax.set_extent(extent, crs=ccrs.PlateCarree())

    # Map features
    ax.coastlines(resolution='50m', linewidth=1.0)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, alpha=0.5)
    ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.5)
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue', alpha=0.2)

    # Gridlines with labels on bottom and left only
    gl = ax.gridlines(draw_labels=True, dms=False, x_inline=False, y_inline=False,
                     linewidth=0.5, alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False

    # Plot FTLE field (background)
    LON_FTLE, LAT_FTLE = np.meshgrid(ftle_lons, ftle_lats)
    ftle_plot = ax.contourf(LON_FTLE, LAT_FTLE, ftle_field,
                            levels=20, cmap='YlOrRd', alpha=0.4,
                            transform=ccrs.PlateCarree(),
                            extend='both')
    cbar = plt.colorbar(ftle_plot, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label('FTLE (day⁻¹)', fontsize=11, fontweight='bold')

    # Plot TC initial position only (no tracks)
    # Convert longitude to °W for display
    tc_init_lon_W = 360 - tc_init_lon if tc_init_lon > 180 else -tc_init_lon
    ax.plot(tc_init_lon, tc_init_lat,
           'g*', markersize=25, markeredgecolor='black', markeredgewidth=2,
           transform=ccrs.PlateCarree(),
           label=f'TC Initial Position\n({tc_init_lat:.1f}°N, {abs(tc_init_lon_W):.1f}°W)',
           zorder=10)

    # Plot seeding locations
    # Build legend label with all coordinates (convert to °W for display)
    if len(seeding_locations) > 0:
        coord_text = '\n'.join([f"  {loc['lat_center']:.2f}°N, {360 - loc['lon_center']:.2f}°W"
                                for loc in seeding_locations])
        legend_label = f"Perturbation Sites:\n{coord_text}"
    else:
        legend_label = "Perturbation Sites"

    for i, loc in enumerate(seeding_locations, 1):
        # Center marker
        ax.plot(loc['lon_center'], loc['lat_center'],
               'k*', markersize=15, markeredgecolor='yellow', markeredgewidth=2,
               transform=ccrs.PlateCarree(),
               label=legend_label if i == 1 else '',
               zorder=11)

        # Seeding radius circle - use geodesic approximation
        # Create circle points accounting for latitude-dependent longitude scale
        n_points = 100
        lat_center = loc['lat_center']
        lon_center = loc['lon_center']
        radius_km = loc['radius_km']

        # Calculate radius in degrees (latitude)
        radius_lat = radius_km / 111.0

        # Calculate radius in degrees (longitude) accounting for latitude
        radius_lon = radius_km / (111.0 * np.cos(np.deg2rad(lat_center)))

        # Generate circle points
        theta = np.linspace(0, 2*np.pi, n_points)
        circle_lons = lon_center + radius_lon * np.cos(theta)
        circle_lats = lat_center + radius_lat * np.sin(theta)

        # Plot circle as line
        ax.plot(circle_lons, circle_lats,
               color='black', linewidth=2, linestyle='--',
               transform=ccrs.PlateCarree(), zorder=10)

        # Label
        ax.text(loc['lon_center'], loc['lat_center'] + 1.5,
               f"#{i}", fontsize=10, fontweight='bold',
               ha='center', va='bottom',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8),
               transform=ccrs.PlateCarree(), zorder=12)

    # Legend
    ax.legend(loc='upper left', fontsize=10, framealpha=0.9)

    # Title
    ax.set_title('Sandy 2012 - FTLE Field with Seeding Locations',
                fontsize=13, fontweight='bold', pad=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

    return


def plot_custom_track_comparison(forecast_tracks, obs_track, tc_init_lat, tc_init_lon,
                                  title, save_path, extent=None, seeding_locations=None):
    """
    Create custom track comparison plot with specific styling:
    - Observation (IBTrACS): blue line with round dots
    - Baseline Forecast: purple line with round dots
    - FTLE-Seeded Perturbed: red line with star markers
    - TC Initial Position: green star marker
    - Perturbation Sites: black/yellow small stars

    Parameters
    ----------
    forecast_tracks : dict
        {'Baseline Forecast': track_dict, 'FTLE-Seeded Perturbed': track_dict}
    obs_track : dict
        {'lat': [...], 'lon': [...], 'time': [...]}
    tc_init_lat, tc_init_lon : float
        Initial TC position
    title : str
        Plot title
    save_path : Path
        Save path for figure
    extent : list, optional
        [lon_min, lon_max, lat_min, lat_max]
    seeding_locations : list, optional
        List of seeding location dicts with 'lat_center' and 'lon_center'
    """
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    fig = plt.figure(figsize=(14, 10))
    ax = plt.subplot(1, 1, 1, projection=ccrs.PlateCarree())

    # Set extent
    if extent is not None:
        ax.set_extent(extent, crs=ccrs.PlateCarree())

    # Map features
    ax.coastlines(resolution='50m', linewidth=1.0)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, alpha=0.5)
    ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue', alpha=0.2)

    # Gridlines with labels on bottom and left only
    gl = ax.gridlines(draw_labels=True, dms=False, x_inline=False, y_inline=False,
                     linewidth=0.5, alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False

    # Plot TC initial position (green star)
    # Convert longitude to °W for display
    tc_init_lon_W = 360 - tc_init_lon if tc_init_lon > 180 else -tc_init_lon
    ax.plot(tc_init_lon, tc_init_lat,
           'g*', markersize=20, markeredgecolor='black', markeredgewidth=2,
           transform=ccrs.PlateCarree(),
           label=f'TC Initial Position\n({tc_init_lat:.1f}°N, {abs(tc_init_lon_W):.1f}°W)',
           zorder=10)

    # Plot observation track (lighter blue, round dots)
    if obs_track is not None:
        ax.plot(obs_track['lon'], obs_track['lat'],
               'o-', color='#3498DB', markersize=6, linewidth=2.5,
               transform=ccrs.PlateCarree(),
               label='Observation (IBTrACS)',
               zorder=8)

    # Plot forecast tracks with custom colors and markers (lighter palette)
    track_styles = {
        'Baseline Forecast': {'color': '#9B59B6', 'marker': 'o', 'markersize': 6, 'zorder': 6},  # Lighter purple
        'FTLE-Seeded Perturbed': {'color': '#E74C3C', 'marker': '*', 'markersize': 10, 'zorder': 7}  # Lighter red
    }

    for label, track in forecast_tracks.items():
        style = track_styles.get(label, {'color': 'gray', 'marker': 'o', 'markersize': 6, 'zorder': 5})
        ax.plot(track['lon'], track['lat'],
               marker=style['marker'], markersize=style['markersize'],
               color=style['color'], linewidth=2,
               transform=ccrs.PlateCarree(),
               label=label,
               zorder=style['zorder'])

    # Plot perturbation sites (small black/yellow stars)
    if seeding_locations is not None and len(seeding_locations) > 0:
        for i, loc in enumerate(seeding_locations):
            ax.plot(loc['lon_center'], loc['lat_center'],
                   '*', markersize=12, color='black',
                   markeredgecolor='yellow', markeredgewidth=1.5,
                   transform=ccrs.PlateCarree(),
                   label='Perturbation Sites' if i == 0 else '',
                   zorder=9)

    # Title and legend
    ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
    ax.legend(loc='upper left', fontsize=11, framealpha=0.95)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

    return


def plot_track_deviation(deviations, forecast_times, save_path):
    """
    Create track deviation timeseries plot for poster.

    Parameters
    ----------
    deviations : list
        Track deviations in km at each timestep
    forecast_times : list
        Datetime objects for each forecast timestep
    save_path : Path
        Output file path
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, ax = plt.subplots(figsize=(12, 7))

    # Convert times to hours since initialization
    hours = [(t - forecast_times[0]).total_seconds() / 3600 for t in forecast_times]

    # Plot deviation
    ax.plot(hours, deviations, 'o-', color='#E74C3C', linewidth=3,
            markersize=8, markeredgecolor='black', markeredgewidth=1.5,
            label='Track Deviation')

    # Add horizontal grid
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.grid(True, axis='x', alpha=0.2, linestyle=':')

    # Highlight key milestones
    milestones = {
        24: 4,   # 24 hours = 4 steps
        48: 8,   # 48 hours = 8 steps
        72: 12,  # 72 hours = 12 steps
        120: 20, # 120 hours = 20 steps
    }

    for hour, step in milestones.items():
        if step < len(deviations):
            ax.axvline(hour, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            ax.text(hour, ax.get_ylim()[1] * 0.95, f'{hour}h',
                   ha='center', va='top', fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # Labels and title
    ax.set_xlabel('Forecast Lead Time (hours)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Track Deviation (km)', fontsize=12, fontweight='bold')
    ax.set_title('Hurricane Sandy - Track Deviation: Baseline vs FTLE-Seeded Perturbation',
                fontsize=13, fontweight='bold', pad=15)

    # Set x-axis limits and ticks
    ax.set_xlim(0, max(hours))
    ax.set_xticks(range(0, int(max(hours)) + 1, 24))

    # Add legend with max deviation
    max_dev = max(deviations)
    max_dev_hour = hours[deviations.index(max_dev)]
    legend_text = f'Track Deviation\n(Max: {max_dev:.1f} km at +{max_dev_hour:.0f}h)'
    ax.legend([legend_text], loc='upper left', fontsize=11, framealpha=0.95)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

    return


def main():
    print("=" * 80)
    print("  Hurricane Sandy 2012 - FTLE-Guided Cloud Seeding Test")
    print("=" * 80)
    print()
    print("Strategy: Adapt Moyan Liu's AR perturbation method to TCs")
    print("Method: FTLE-targeted cloud seeding (heating + moisture removal)")
    print()

    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    CONFIG = {
        'init_date': '2012-10-23',
        'init_hour': '00',
        'init_lat': 12.6,  # IBTrACS: Oct 23 00:00 UTC
        'init_lon': 281.6,  # -78.4°W = 281.6°E
        'steps': 28,  # 7 days to landfall (Oct 30)
        'data_path': Path("/scratch/qhuang62/aurora-extreme-predictability/research/TC/data/era5_sandy_2012"),
        'output_dir': Path("/scratch/qhuang62/control_AR_FZ_TC/sandy_ftle_925_850_700_rh75_output"),
    }

    CONFIG['output_dir'].mkdir(exist_ok=True, parents=True)

    # TC-adapted seeding configuration (environmental modification)
    SEEDING_CONFIG_SANDY = {
        'layers_mb': [925.0, 850.0, 700.0],  # Steering levels (meteorologically realistic)
        'freeze_efficiency': 0.3,            # original 0.6 now we try 0.3 to see if still work
        'fallout_fraction': 0.80,            # High precipitation
        'max_removal_fraction': 0.50,        # Conservative moisture removal
        'min_RH': 0.75,                      # Only seed where RH > 75% (matches poster)
        'energy_method': 'net_realistic',
        'vertical_coupling': False,          # Independent levels
        'coupling_factor': 0.3
    }

    # Geographic bounds for FTLE analysis (near TC and forecast track)
    # Focus on TC environment for seeding selection (500-1500 km range)
    # Sandy Oct 23: 12.6°N, 281.6°E
    # Extended to cover full visualization extent (0-30°N, 260-300°E for seeding map)
    BOUNDS_SANDY = {
        'lat': (0, 35),       # Full visualization extent to downstream
        'lon': (260, 300)     # -100°W to -60°W (full map extent)
    }

    print(f"Initialization: {CONFIG['init_date']} {CONFIG['init_hour']}:00 UTC")
    print(f"Sandy position: {CONFIG['init_lat']}°N, {CONFIG['init_lon']}°E")
    print(f"Forecast length: {CONFIG['steps']} steps ({CONFIG['steps']*6} hours)")
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
    static_ds, surf_ds, atmos_ds = load_era5_data(
        CONFIG['data_path'],
        CONFIG['init_date']
    )

    # Convert longitude from [-180, 180] to [0, 360] if needed
    if surf_ds.longitude.values.min() < 0:
        print("Converting longitude from [-180, 180] to [0, 360]...")

        # Convert longitude values
        lon_converted = (surf_ds.longitude.values + 360) % 360

        # Sort by new longitude to maintain proper order
        lon_sort_idx = np.argsort(lon_converted)
        lon_sorted = lon_converted[lon_sort_idx]

        # Reorder all datasets
        surf_ds = surf_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)
        atmos_ds = atmos_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)
        static_ds = static_ds.isel(longitude=lon_sort_idx).assign_coords(longitude=lon_sorted)

        print(f"✓ Longitude range: [{surf_ds.longitude.values.min():.1f}, {surf_ds.longitude.values.max():.1f}]")

    # Filter to Aurora's standard 13 pressure levels
    AURORA_LEVELS = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000]

    print(f"Filtering to Aurora's 13 standard pressure levels...")
    print(f"  Original: {len(atmos_ds.pressure_level)} levels")

    # Filter atmospheric dataset to only Aurora's 13 levels
    atmos_ds = atmos_ds.sel(pressure_level=AURORA_LEVELS)

    print(f"  Filtered: {len(atmos_ds.pressure_level)} levels")
    print(f"✓ Using levels: {list(atmos_ds.pressure_level.values)}")

    # Create batch (atmos_ds now only has the 13 Aurora levels)
    batch = create_aurora_batch(static_ds, surf_ds, atmos_ds, time_start_idx=0)
    print(f"✓ Batch created: {batch.atmos_vars['t'].shape}")
    print()

    # Extract metadata
    lats = batch.metadata.lat.cpu().numpy()
    lons = batch.metadata.lon.cpu().numpy()
    pressure_levels = list(batch.metadata.atmos_levels)

    print(f"Grid: {len(lats)} lats × {len(lons)} lons")
    print(f"Pressure levels: {len(pressure_levels)} levels")
    print()

    # =========================================================================
    # CALCULATE FTLE (STEERING LEVEL)
    # =========================================================================
    print("=" * 80)
    print("  Step 1: Calculate FTLE at Steering Level (500 hPa)")
    print("=" * 80)
    print()

    # Find 500 hPa level index
    level_500_idx = pressure_levels.index(500.0)

    # Extract winds at 500 hPa
    u_500 = batch.atmos_vars["u"][0, 1, level_500_idx].cpu().numpy()
    v_500 = batch.atmos_vars["v"][0, 1, level_500_idx].cpu().numpy()

    print(f"500 hPa winds: {u_500.shape}")
    print(f"U range: [{np.min(u_500):.1f}, {np.max(u_500):.1f}] m/s")
    print(f"V range: [{np.min(v_500):.1f}, {np.max(v_500):.1f}] m/s")
    print()

    # Calculate FTLE
    ftle_field, final_positions = calculate_ftle_from_winds(
        u_500, v_500, lats, lons,
        dt_hours=6,
        integration_time_hours=48,  # 2-day integration (TC timescale)
        direction='forward'
    )

    print()

    # Crop to Atlantic basin
    ftle_crop, lats_crop, lons_crop = crop_region(
        ftle_field, lats, lons,
        lat_range=(BOUNDS_SANDY['lat'][0], BOUNDS_SANDY['lat'][1]),
        lon_range=(BOUNDS_SANDY['lon'][0], BOUNDS_SANDY['lon'][1])
    )

    print(f"✓ Cropped to Atlantic basin: {ftle_crop.shape}")
    print(f"  FTLE range in basin: [{np.min(ftle_crop):.4f}, {np.max(ftle_crop):.4f}] day⁻¹")
    print()

    # =========================================================================
    # SELECT PERTURBATION LOCATIONS
    # =========================================================================
    print("=" * 80)
    print("  Step 2: Select FTLE-Guided Perturbation Locations")
    print("=" * 80)
    print()

    # Select candidates
    selected_lats, selected_lons, selected_scores = select_seeding_candidates(
        ftle_crop, lats_crop, lons_crop,
        ftle_percentile=85,  # Top 15% (slightly lower than AR to get more candidates)
        geographic_bounds=BOUNDS_SANDY,
        min_separation_km=300,  # Slightly smaller for TC environment
        max_candidates=10  # Get more candidates, then filter by distance
    )

    if len(selected_lats) == 0:
        print("⚠️  No FTLE candidates found! Exiting...")
        return

    # Filter candidates by distance from TC initial position
    # Keep only locations within 500-1500 km of TC (environmental steering region)
    from shared.metrics import calculate_distance

    filtered_lats = []
    filtered_lons = []
    filtered_scores = []

    print(f"\nFiltering by distance from TC (12.6°N, 281.6°E):")
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

    # Update selected candidates
    selected_lats = filtered_lats[:5]  # Keep top 5 after filtering
    selected_lons = filtered_lons[:5]
    selected_scores = filtered_scores[:5]

    if len(selected_lats) == 0:
        print("\n⚠️  No candidates within 500-1500 km of TC! Exiting...")
        return

    print(f"\n✓ Selected {len(selected_lats)} locations within environmental steering region")

    # Create seeding locations (use all candidates for maximum effect)
    seeding_locations = create_seeding_locations_from_candidates(
        selected_lats, selected_lons,
        selected_indices=list(range(1, len(selected_lats)+1)),
        radius_km=300  # TC environmental scale
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
    # RUN CONTROL FORECAST
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
        name="Sandy Baseline",
        device=device,
        verbose=True
    )

    forecast_track_baseline = extract_track_from_tracker(tracker_baseline, init_time)
    print(f"✓ Baseline track: {len(forecast_track_baseline['time'])} positions")

    # Print final position
    final_lat_baseline = forecast_track_baseline['lat'][-1]
    final_lon_baseline = forecast_track_baseline['lon'][-1]
    print(f"  Final position: {final_lat_baseline:.2f}°N, {final_lon_baseline:.2f}°E")

    # Save predictions for field analysis
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

    # Clone batch for perturbation
    batch_seeded = clone_batch(batch_baseline)

    # Apply cloud seeding
    delta_T, delta_q, diagnostics = apply_physically_consistent_cloud_seeding(
        batch_seeded,
        seeding_mask,
        SEEDING_CONFIG_SANDY
    )

    # Print diagnostics
    print_diagnostics(diagnostics, SEEDING_CONFIG_SANDY)

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
        name="Sandy FTLE-Seeded",
        device=device,
        verbose=True
    )

    forecast_track_seeded = extract_track_from_tracker(tracker_seeded, init_time)
    print(f"✓ Seeded track: {len(forecast_track_seeded['time'])} positions")

    # Print final position
    final_lat_seed = forecast_track_seeded['lat'][-1]
    final_lon_seed = forecast_track_seeded['lon'][-1]
    print(f"  Final position: {final_lat_seed:.2f}°N, {final_lon_seed:.2f}°E")

    # Save predictions for field analysis
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

    # Calculate deviations at each timestep
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
    print(f"  24hr (+4 steps): {deviations[4]:.1f} km" if len(deviations) > 4 else "  24hr: N/A")
    print(f"  48hr (+8 steps): {deviations[8]:.1f} km" if len(deviations) > 8 else "  48hr: N/A")
    print(f"  72hr (+12 steps): {deviations[12]:.1f} km" if len(deviations) > 12 else "  72hr: N/A")
    print(f"  96hr (+16 steps): {deviations[16]:.1f} km" if len(deviations) > 16 else "  96hr: N/A")
    print(f"  120hr (+20 steps): {deviations[20]:.1f} km" if len(deviations) > 20 else "  120hr: N/A")
    print(f"  Final: {deviations[-1]:.1f} km")
    print()

    # Final position shift
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

    # Load observed track
    try:
        obs_track = load_ibtracs_track('SANDY', 2012)

        # Truncate to forecast period + 2 more timesteps (12 hours)
        # 7 days + 12 hours = 7.5 days
        valid_indices = [i for i, t in enumerate(obs_track['time'])
                        if init_time <= t <= init_time + pd.Timedelta(days=7, hours=12)]
        obs_track_truncated = {
            'time': [obs_track['time'][i] for i in valid_indices],
            'lat': [obs_track['lat'][i] for i in valid_indices],
            'lon': [obs_track['lon'][i] for i in valid_indices]
        }
    except:
        print("⚠️  Could not load observed track")
        obs_track_truncated = None

    # Track comparison plot
    forecast_tracks = {
        'Baseline Forecast': forecast_track_baseline,
        'FTLE-Seeded Perturbed': forecast_track_seeded
    }

    # Track comparison plot with custom styling (extent 0-50°N, 260-300°E)
    track_plot = CONFIG['output_dir'] / "sandy_ftle_track_comparison.png"
    plot_custom_track_comparison(
        forecast_tracks=forecast_tracks,
        obs_track=obs_track_truncated,
        tc_init_lat=CONFIG['init_lat'],
        tc_init_lon=CONFIG['init_lon'],
        title="Sandy 2012 - FTLE-Guided Perturbation Test Result",
        save_path=track_plot,
        extent=[260, 300, 0, 50],  # 0-50°N, 260-300°E (100°W-60°W)
        seeding_locations=seeding_locations
    )
    print(f"✓ Saved track comparison: {track_plot}")

    # Create seeding location map
    print("\nCreating seeding location visualization...")
    try:
        plot_seeding_locations_map(
            seeding_locations,
            ftle_crop,
            lats_crop,
            lons_crop,
            CONFIG['init_lat'],
            CONFIG['init_lon'],
            save_path=CONFIG['output_dir'] / "seeding_locations_map.png"
        )
        print(f"✓ Saved seeding map: {CONFIG['output_dir'] / 'seeding_locations_map.png'}")
    except Exception as e:
        print(f"⚠️  Could not create seeding map: {e}")

    # Create track deviation plot
    print("\nCreating track deviation plot...")
    try:
        plot_track_deviation(
            deviations=deviations,
            forecast_times=[init_time + pd.Timedelta(hours=i*6) for i in range(len(deviations))],
            save_path=CONFIG['output_dir'] / "track_deviation_timeseries.png"
        )
        print(f"✓ Saved deviation plot: {CONFIG['output_dir'] / 'track_deviation_timeseries.png'}")
    except Exception as e:
        print(f"⚠️  Could not create deviation plot: {e}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("  ✓ Test Complete!")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • FTLE candidates: {len(seeding_locations)}")
    print(f"  • Seeded area: {seeding_mask.sum()} grid cells")
    print(f"  • Max track deviation: {max(deviations):.1f} km")
    print(f"  • Final track deviation: {deviations[-1]:.1f} km")
    print()
    print("Next steps:")
    print("  1. Analyze physical mechanisms (inspect wind/pressure fields)")
    print("  2. Test different FTLE thresholds and seeding radii")
    print("  3. Compare with your previous grid-based method")
    print("  4. Extend to other TCs if successful")
    print()


if __name__ == "__main__":
    import pandas as pd  # Import needed for time truncation
    main()
