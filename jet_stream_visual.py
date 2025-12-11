#!/usr/bin/env python3
"""
Jet Stream Visualization for Hurricane Sandy FTLE Perturbation Test

Creates visualization showing:
- 250 hPa wind speed (jet stream)
- FTLE field at 500 hPa (steering level)
- Perturbation sites
- TC initialization location

Compares baseline vs seeded forecasts to see how perturbations interact with jet stream.

Author: Jet stream analysis for FTLE-guided TC perturbation
Date: 2025-12-04
"""

import sys
from pathlib import Path
import torch
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime, timedelta

# Add paths for importing utilities
control_dir = Path(__file__).parent
sys.path.insert(0, str(control_dir))

print("=" * 80)
print("  Jet Stream Visualization - Hurricane Sandy 2012")
print("=" * 80)
print()

# =========================================================================
# CONFIGURATION
# =========================================================================
results_dir = Path("/scratch/qhuang62/control_AR_FZ_TC/sandy_ftle_test_output")
pred_baseline_path = results_dir / "preds_baseline.pt"
pred_seeded_path = results_dir / "preds_seeded.pt"

output_dir = results_dir / "jet_stream_analysis"
output_dir.mkdir(exist_ok=True)

# Sandy initialization
TC_INIT_LAT = 12.6
TC_INIT_LON = 281.6

# Perturbation sites (from sandy_ftle_perturbation_test.py output)
# These are the 3 sites that achieved 321.6 km track deviation
SEEDING_LOCATIONS = [
    {'lat': 5.50, 'lon': 277.75, 'radius_km': 300},
    {'lat': 8.25, 'lon': 278.50, 'radius_km': 300},
    {'lat': 14.25, 'lon': 269.00, 'radius_km': 300}
]

# Map extent: 0°N to 55°N, 120°W to 55°W
# Convert to 0-360°E: 120°W = 240°E, 55°W = 305°E
MAP_EXTENT = [240, 305, 0, 55]  # [lon_min, lon_max, lat_min, lat_max]

# =========================================================================
# LOAD PREDICTIONS
# =========================================================================
print("Loading saved predictions...")

if not pred_baseline_path.exists():
    print(f"❌ Baseline predictions not found: {pred_baseline_path}")
    print("   Run sandy_ftle_perturbation_test.py first!")
    sys.exit(1)

if not pred_seeded_path.exists():
    print(f"❌ Seeded predictions not found: {pred_seeded_path}")
    print("   Run sandy_ftle_perturbation_test.py first!")
    sys.exit(1)

preds_baseline = torch.load(pred_baseline_path, map_location='cpu')
preds_seeded = torch.load(pred_seeded_path, map_location='cpu')

print(f"✓ Baseline: {len(preds_baseline)} timesteps")
print(f"✓ Seeded: {len(preds_seeded)} timesteps")
print()

# Extract metadata
lats = preds_baseline[0].metadata.lat.cpu().numpy()
lons = preds_baseline[0].metadata.lon.cpu().numpy()
pressure_levels = list(preds_baseline[0].metadata.atmos_levels)

print(f"Grid: {len(lats)} lats × {len(lons)} lons")
print(f"Pressure levels: {pressure_levels}")
print()

# Find pressure level indices
idx_250 = pressure_levels.index(250.0)
idx_500 = pressure_levels.index(500.0)

print(f"Using 250 hPa (index {idx_250}) for jet stream")
print(f"Using 500 hPa (index {idx_500}) for FTLE/steering level comparison")
print()

# =========================================================================
# LOAD TC TRACKS FOR ANIMATION
# =========================================================================
print("Extracting TC tracks from predictions...")

# Extract TC positions by finding minimum MSL pressure at each timestep
baseline_track_lats = []
baseline_track_lons = []
seeded_track_lats = []
seeded_track_lons = []

for t in range(len(preds_baseline)):
    # Extract minimum MSL pressure location as TC center proxy
    msl_base = preds_baseline[t].surf_vars['msl'][0, 0].cpu().numpy()
    msl_seed = preds_seeded[t].surf_vars['msl'][0, 0].cpu().numpy()

    # Find minimum pressure location
    idx_base = np.unravel_index(np.argmin(msl_base), msl_base.shape)
    idx_seed = np.unravel_index(np.argmin(msl_seed), msl_seed.shape)

    baseline_track_lats.append(lats[idx_base[0]])
    baseline_track_lons.append(lons[idx_base[1]])
    seeded_track_lats.append(lats[idx_seed[0]])
    seeded_track_lons.append(lons[idx_seed[1]])

print(f"✓ Extracted {len(baseline_track_lats)} track positions")
print(f"  Baseline: {baseline_track_lats[0]:.1f}°N, {baseline_track_lons[0]:.1f}°E → {baseline_track_lats[-1]:.1f}°N, {baseline_track_lons[-1]:.1f}°E")
print(f"  Seeded:   {seeded_track_lats[0]:.1f}°N, {seeded_track_lons[0]:.1f}°E → {seeded_track_lats[-1]:.1f}°N, {seeded_track_lons[-1]:.1f}°E")
print()

# =========================================================================
# PLOTTING FUNCTION
# =========================================================================

def plot_jet_comparison_3panel(wind_baseline, wind_seeded, lats, lons,
                                baseline_track_lats, baseline_track_lons,
                                seeded_track_lats, seeded_track_lons,
                                seeding_locs, tc_init_lat, tc_init_lon,
                                timestep, hours, save_path, extent,
                                wind_vmin, wind_vmax, diff_vmin, diff_vmax):
    """
    Create 3-panel comparison:
    - Left: Baseline forecast (jet + full track)
    - Middle: FTLE-Seeded forecast (jet + progressive track up to current timestep)
    - Right: Difference (jet speed difference)

    Parameters
    ----------
    wind_vmin, wind_vmax : float
        Fixed color scale limits for wind speed plots (baseline and seeded)
    diff_vmin, diff_vmax : float
        Fixed color scale limits for difference plot (computed globally)
    """

    fig = plt.figure(figsize=(24, 8))
    proj = ccrs.PlateCarree()

    LON, LAT = np.meshgrid(lons, lats)

    # Use fixed wind speed levels based on global min/max
    jet_levels = np.linspace(wind_vmin, wind_vmax, 17)  # 17 levels for smooth contours

    # -------------------------------------------------------------------------
    # Panel 1: Baseline Forecast
    # -------------------------------------------------------------------------
    ax1 = plt.subplot(1, 3, 1, projection=proj)
    ax1.set_extent(extent, crs=proj)
    ax1.coastlines(resolution='50m', linewidth=0.8)
    ax1.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)

    # Grid labels: bottom and left only
    gl1 = ax1.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
    gl1.top_labels = False
    gl1.right_labels = False

    ax1.set_title('Baseline Forecast', fontsize=12, fontweight='bold')

    # Jet stream filled contours with FIXED scale
    im1 = ax1.contourf(LON, LAT, wind_baseline,
                      levels=jet_levels, cmap='plasma', vmin=wind_vmin, vmax=wind_vmax,
                      transform=proj, extend='both')

    # Jet contours
    cs1 = ax1.contour(LON, LAT, wind_baseline,
                     levels=[30, 50, 70], colors='white', linewidths=1.5,
                     transform=proj)
    ax1.clabel(cs1, inline=True, fontsize=9, fmt='%d m/s')

    # FULL baseline track (static)
    ax1.plot(baseline_track_lons, baseline_track_lats,
            'o-', color='purple', linewidth=2.5, markersize=5,
            transform=proj, label='Baseline Track (Full)', zorder=11)

    # TC initial position
    ax1.plot(tc_init_lon, tc_init_lat, '*', markersize=15, color='green',
            markeredgecolor='black', markeredgewidth=1.5, transform=proj,
            label='TC Init', zorder=12)

    # Perturbation sites
    for i, loc in enumerate(seeding_locs):
        ax1.plot(loc['lon'], loc['lat'], '*', markersize=12, color='black',
                markeredgecolor='yellow', markeredgewidth=1.5, transform=proj,
                label=f'Site {i+1}' if i == 0 else '', zorder=10)

    plt.colorbar(im1, ax=ax1, shrink=0.7, label='Wind Speed (m/s)')
    ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)

    # -------------------------------------------------------------------------
    # Panel 2: FTLE-Seeded Perturbed
    # -------------------------------------------------------------------------
    ax2 = plt.subplot(1, 3, 2, projection=proj)
    ax2.set_extent(extent, crs=proj)
    ax2.coastlines(resolution='50m', linewidth=0.8)
    ax2.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)

    # Grid labels: bottom and left only
    gl2 = ax2.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
    gl2.top_labels = False
    gl2.right_labels = False

    ax2.set_title('FTLE-Seeded Perturbed', fontsize=12, fontweight='bold')

    # Jet stream filled contours with FIXED scale
    im2 = ax2.contourf(LON, LAT, wind_seeded,
                      levels=jet_levels, cmap='plasma', vmin=wind_vmin, vmax=wind_vmax,
                      transform=proj, extend='both')

    # Jet contours
    cs2 = ax2.contour(LON, LAT, wind_seeded,
                     levels=[30, 50, 70], colors='white', linewidths=1.5,
                     transform=proj)
    ax2.clabel(cs2, inline=True, fontsize=9, fmt='%d m/s')

    # Baseline track (static, full) - lighter color for reference
    ax2.plot(baseline_track_lons, baseline_track_lats,
            'o-', color='purple', linewidth=2, markersize=4, alpha=0.5,
            transform=proj, label='Baseline (ref)', zorder=9)

    # PROGRESSIVE perturbed track (only up to current timestep)
    current_idx = timestep + 1  # Include current timestep
    ax2.plot(seeded_track_lons[:current_idx], seeded_track_lats[:current_idx],
            '*-', color='red', linewidth=2.5, markersize=8,
            transform=proj, label='Perturbed (animated)', zorder=11)

    # TC initial position
    ax2.plot(tc_init_lon, tc_init_lat, '*', markersize=15, color='green',
            markeredgecolor='black', markeredgewidth=1.5, transform=proj,
            label='TC Init', zorder=12)

    # Perturbation sites
    for i, loc in enumerate(seeding_locs):
        ax2.plot(loc['lon'], loc['lat'], '*', markersize=12, color='black',
                markeredgecolor='yellow', markeredgewidth=1.5, transform=proj,
                label=f'Site {i+1}' if i == 0 else '', zorder=10)

    plt.colorbar(im2, ax=ax2, shrink=0.7, label='Wind Speed (m/s)')
    ax2.legend(loc='upper left', fontsize=9, framealpha=0.9)

    # -------------------------------------------------------------------------
    # Panel 3: Difference (Perturbed - Baseline) with FIXED scale
    # -------------------------------------------------------------------------
    ax3 = plt.subplot(1, 3, 3, projection=proj)
    ax3.set_extent(extent, crs=proj)
    ax3.coastlines(resolution='50m', linewidth=0.8)
    ax3.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)

    # Grid labels: bottom and left only
    gl3 = ax3.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
    gl3.top_labels = False
    gl3.right_labels = False

    ax3.set_title('Difference (Perturbed - Baseline)', fontsize=12, fontweight='bold')

    diff = wind_seeded - wind_baseline

    # Use FIXED symmetric color scale (computed globally)
    diff_levels = np.linspace(diff_vmin, diff_vmax, 21)

    # Use PuOr colormap (purple for low, white for 0, orange for high)
    im3 = ax3.contourf(LON, LAT, diff,
                      levels=diff_levels, cmap='PuOr',
                      transform=proj, extend='both')

    # Zero contour (black line)
    ax3.contour(LON, LAT, diff,
               levels=[0], colors='black', linewidths=2,
               transform=proj)

    # Baseline track (reference)
    ax3.plot(baseline_track_lons, baseline_track_lats,
            'o-', color='purple', linewidth=2, markersize=4, alpha=0.5,
            transform=proj, zorder=9)

    # Perturbed track (progressive)
    ax3.plot(seeded_track_lons[:current_idx], seeded_track_lats[:current_idx],
            '*-', color='red', linewidth=2.5, markersize=8,
            transform=proj, zorder=11)

    # TC initial position
    ax3.plot(tc_init_lon, tc_init_lat, '*', markersize=15, color='green',
            markeredgecolor='black', markeredgewidth=1.5, transform=proj, zorder=12)

    # Perturbation sites
    for loc in seeding_locs:
        ax3.plot(loc['lon'], loc['lat'], '*', markersize=12, color='black',
                markeredgecolor='yellow', markeredgewidth=1.5, transform=proj, zorder=10)

    plt.colorbar(im3, ax=ax3, shrink=0.7, label='Δ Wind Speed (m/s)')

    # -------------------------------------------------------------------------
    # Overall title
    # -------------------------------------------------------------------------
    fig.suptitle(f'250 hPa Jet Stream - Timestep {timestep} (+{hours}h)',
                fontsize=14, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save_path, dpi=120, bbox_inches='tight')
    plt.close()

    return diff


# =========================================================================
# FIRST PASS: COMPUTE GLOBAL SCALES (WIND SPEED AND DIFFERENCE)
# =========================================================================

print("First pass: Computing global min/max for wind speed and difference across all timesteps...")
print("(This ensures consistent color scales in all plots for GIF animation)")
print()

n_timesteps = len(preds_baseline)

# Crop wind fields to map extent for faster processing
def crop_field_to_extent(field, lats, lons, extent):
    """Crop 2D field to map extent."""
    lat_mask = (lats >= extent[2]) & (lats <= extent[3])
    lon_mask = (lons >= extent[0]) & (lons <= extent[1])

    lats_crop = lats[lat_mask]
    lons_crop = lons[lon_mask]

    # Use numpy indexing with meshgrid
    field_crop = field[np.ix_(lat_mask, lon_mask)]

    return field_crop, lats_crop, lons_crop


# Track global min/max for wind speed (for baseline and seeded plots)
global_wind_min = np.inf
global_wind_max = -np.inf

# Track global min/max for difference (for difference plot)
global_diff_min = np.inf
global_diff_max = -np.inf

for t in range(n_timesteps):
    # Extract 250 hPa winds
    u_250_base = preds_baseline[t].atmos_vars['u'][0, 0, idx_250].cpu().numpy()
    v_250_base = preds_baseline[t].atmos_vars['v'][0, 0, idx_250].cpu().numpy()
    u_250_seed = preds_seeded[t].atmos_vars['u'][0, 0, idx_250].cpu().numpy()
    v_250_seed = preds_seeded[t].atmos_vars['v'][0, 0, idx_250].cpu().numpy()

    # Calculate wind speed
    wind_250_base = np.sqrt(u_250_base**2 + v_250_base**2)
    wind_250_seed = np.sqrt(u_250_seed**2 + v_250_seed**2)

    # Crop to map extent
    wind_base_crop, _, _ = crop_field_to_extent(wind_250_base, lats, lons, MAP_EXTENT)
    wind_seed_crop, _, _ = crop_field_to_extent(wind_250_seed, lats, lons, MAP_EXTENT)

    # Update global wind speed min/max
    global_wind_min = min(global_wind_min, np.min(wind_base_crop), np.min(wind_seed_crop))
    global_wind_max = max(global_wind_max, np.max(wind_base_crop), np.max(wind_seed_crop))

    # Compute difference
    diff = wind_seed_crop - wind_base_crop

    # Update global difference min/max
    global_diff_min = min(global_diff_min, np.min(diff))
    global_diff_max = max(global_diff_max, np.max(diff))

# Make difference scale symmetric around zero
diff_scale = max(abs(global_diff_min), abs(global_diff_max))
global_diff_min = -diff_scale
global_diff_max = diff_scale

print(f"Global wind speed range: [{global_wind_min:.2f}, {global_wind_max:.2f}] m/s")
print(f"Global difference range: [{global_diff_min:.2f}, {global_diff_max:.2f}] m/s")
print()

# =========================================================================
# SECOND PASS: CREATE PLOTS WITH FIXED SCALE
# =========================================================================

print("Second pass: Creating plots with fixed difference scale...")
print(f"Processing all {n_timesteps} timesteps for GIF animation...")
print()

# Statistics tracking
jet_stats = {
    'timestep': [],
    'hours': [],
    'baseline_max': [],
    'seeded_max': [],
    'diff_max': [],
    'diff_mean': []
}

for t in range(n_timesteps):
    hours = t * 6
    print(f"Timestep {t:2d} (+{hours:3d}h)...", end=' ')

    # Extract 250 hPa winds
    u_250_base = preds_baseline[t].atmos_vars['u'][0, 0, idx_250].cpu().numpy()
    v_250_base = preds_baseline[t].atmos_vars['v'][0, 0, idx_250].cpu().numpy()
    u_250_seed = preds_seeded[t].atmos_vars['u'][0, 0, idx_250].cpu().numpy()
    v_250_seed = preds_seeded[t].atmos_vars['v'][0, 0, idx_250].cpu().numpy()

    # Calculate wind speed (magnitude: sqrt(u^2 + v^2))
    wind_250_base = np.sqrt(u_250_base**2 + v_250_base**2)
    wind_250_seed = np.sqrt(u_250_seed**2 + v_250_seed**2)

    # Crop to map extent
    wind_base_crop, lats_crop, lons_crop = crop_field_to_extent(
        wind_250_base, lats, lons, MAP_EXTENT
    )
    wind_seed_crop, _, _ = crop_field_to_extent(
        wind_250_seed, lats, lons, MAP_EXTENT
    )

    # Create 3-panel comparison with FIXED scales
    diff = plot_jet_comparison_3panel(
        wind_base_crop, wind_seed_crop, lats_crop, lons_crop,
        baseline_track_lats, baseline_track_lons,
        seeded_track_lats, seeded_track_lons,
        SEEDING_LOCATIONS, TC_INIT_LAT, TC_INIT_LON,
        t, hours,
        output_dir / f'jet_comparison_t{t:03d}.png',
        MAP_EXTENT,
        global_wind_min, global_wind_max,
        global_diff_min, global_diff_max
    )

    # Track statistics
    jet_stats['timestep'].append(t)
    jet_stats['hours'].append(hours)
    jet_stats['baseline_max'].append(np.max(wind_base_crop))
    jet_stats['seeded_max'].append(np.max(wind_seed_crop))
    jet_stats['diff_max'].append(np.max(np.abs(diff)))
    jet_stats['diff_mean'].append(np.mean(np.abs(diff)))

    print(f"✓ Max diff: {jet_stats['diff_max'][-1]:.2f} m/s")

print()

# =========================================================================
# CREATE SUMMARY PLOT
# =========================================================================

print("Creating summary statistics plot...")

fig, axes = plt.subplots(2, 1, figsize=(12, 10))

# Plot 1: Max jet stream speed
axes[0].plot(jet_stats['hours'], jet_stats['baseline_max'],
            'o-', color='purple', linewidth=2.5, markersize=8,
            label='Baseline Forecast')
axes[0].plot(jet_stats['hours'], jet_stats['seeded_max'],
            '*-', color='red', linewidth=2.5, markersize=10,
            label='FTLE-Seeded Perturbed')
axes[0].set_xlabel('Forecast Hour', fontweight='bold', fontsize=12)
axes[0].set_ylabel('Max 250 hPa Wind Speed (m/s)', fontweight='bold', fontsize=12)
axes[0].set_title('Jet Stream Maximum Speed Evolution', fontweight='bold', fontsize=13)
axes[0].grid(True, alpha=0.3)
axes[0].legend(fontsize=11, loc='best')

# Plot 2: Difference statistics
axes[1].plot(jet_stats['hours'], jet_stats['diff_max'],
            'o-', color='darkblue', linewidth=2.5, markersize=8,
            label='Max |Difference|')
axes[1].plot(jet_stats['hours'], jet_stats['diff_mean'],
            's-', color='steelblue', linewidth=2.5, markersize=7,
            label='Mean |Difference|')
axes[1].set_xlabel('Forecast Hour', fontweight='bold', fontsize=12)
axes[1].set_ylabel('Wind Speed Difference (m/s)', fontweight='bold', fontsize=12)
axes[1].set_title('Jet Stream Perturbation Magnitude', fontweight='bold', fontsize=13)
axes[1].grid(True, alpha=0.3)
axes[1].legend(fontsize=11, loc='best')
axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)

plt.suptitle('250 hPa Jet Stream Analysis: FTLE-Seeded vs Baseline\nHurricane Sandy 2012',
            fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(output_dir / 'jet_stream_summary.png', dpi=150, bbox_inches='tight')
plt.close()

print(f"✓ Saved: {output_dir / 'jet_stream_summary.png'}")
print()

# =========================================================================
# CREATE GIF ANIMATION
# =========================================================================

print("=" * 80)
print("  Creating GIF Animation")
print("=" * 80)
print()

from PIL import Image

# Collect all PNG files in order
png_files = sorted([output_dir / f'jet_comparison_t{t:03d}.png' for t in range(n_timesteps)])

# Load images
images = []
for png_file in png_files:
    images.append(Image.open(png_file))

# Save as GIF
gif_path = output_dir / 'jet_stream_evolution.gif'
images[0].save(
    gif_path,
    save_all=True,
    append_images=images[1:],
    duration=500,  # 500 ms per frame (0.5 seconds)
    loop=0  # Loop forever
)

print(f"✓ Created GIF: {gif_path}")
print(f"  Frames: {len(images)}")
print(f"  Duration: 500 ms per frame")
print()

# =========================================================================
# SUMMARY
# =========================================================================

print("=" * 80)
print("  ✓ Jet Stream Visualization Complete!")
print("=" * 80)
print()
print(f"Output directory: {output_dir}")
print(f"Total plots created: {n_timesteps} comparison plots + 1 summary + 1 GIF")
print()
print("Visualization files:")
print(f"  • jet_comparison_t###.png  - 3-panel jet stream comparison (28 files)")
print(f"  • jet_stream_evolution.gif - Animated GIF showing TC track evolution")
print(f"  • jet_stream_summary.png   - Summary statistics")
print()
print("Key findings:")
print(f"  • Baseline max jet speed: {max(jet_stats['baseline_max']):.1f} m/s")
print(f"  • Seeded max jet speed:   {max(jet_stats['seeded_max']):.1f} m/s")
print(f"  • Max perturbation:       {max(jet_stats['diff_max']):.1f} m/s at +{jet_stats['hours'][jet_stats['diff_max'].index(max(jet_stats['diff_max']))]:3d}h")
print(f"  • Mean perturbation:      {np.mean(jet_stats['diff_mean']):.2f} m/s (averaged across timesteps)")
print()
print("Fixed color scales:")
print(f"  • Wind speed (baseline & seeded): [{global_wind_min:.2f}, {global_wind_max:.2f}] m/s")
print(f"  • Difference: [{global_diff_min:.2f}, {global_diff_max:.2f}] m/s")
print(f"  • Difference colormap: PuOr (purple=negative, white=zero, orange=positive)")
print()
print("Animation details:")
print("  • Baseline track: Full track shown in all frames (static reference)")
print("  • Perturbed track: Progressive animation (grows with each timestep)")
print("  • Effect: Shows TC divergence from baseline forecast over time")
print()
print("Wind speed calculation confirmed:")
print("  ✓ Wind speed = √(u² + v²)  [NOT wind²]")
print("  ✓ This is the magnitude of the wind vector")
print()
