#!/usr/bin/env python3
"""
Analyze Hurricane Ian FTLE Perturbation - Field Evolution

This script extracts and visualizes atmospheric fields at every timestep
to understand the physical mechanisms behind the track deviation.

Focuses on:
1. Mean sea level pressure (MSL) - TC center and steering
2. 500 hPa geopotential height - steering flow and Rossby waves
3. 700 hPa temperature - diabatic heating from perturbation
4. 850 hPa relative humidity - moisture changes
5. 300 hPa wind speed - jet stream location and strength

Key difference from Sandy: Uses Gulf/Caribbean/Florida map extent and
global min/max for difference plot scaling (for GIF consistency).

Author: Adapted from analyze_sandy_perturbation_fields.py
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

print("=" * 80)
print("  Analyzing Ian FTLE Perturbation - Field Evolution")
print("=" * 80)
print()

# =========================================================================
# CONFIGURATION
# =========================================================================
results_dir = Path("/scratch/qhuang62/control_AR_FZ_TC/Ian_2022_perturb/ian_ftle_test_output_targeted") #change to see targeted changes
pred_ctrl_path = results_dir / "preds_baseline.pt"
pred_seed_path = results_dir / "preds_seeded.pt"

output_dir = results_dir / "field_analysis"
output_dir.mkdir(exist_ok=True)

# =========================================================================
# LOAD PREDICTIONS
# =========================================================================
print("Loading saved predictions...")
print(f"Directory: {results_dir}")
print()

if not pred_ctrl_path.exists():
    print(f"❌ Baseline predictions not found: {pred_ctrl_path}")
    print("   Run ian_ftle_perturbation_test.py first!")
    sys.exit(1)

if not pred_seed_path.exists():
    print(f"❌ Seeded predictions not found: {pred_seed_path}")
    print("   Run ian_ftle_perturbation_test.py first!")
    sys.exit(1)

preds_baseline = torch.load(pred_ctrl_path)
preds_seeded = torch.load(pred_seed_path)

print(f"✓ Baseline: {len(preds_baseline)} timesteps")
print(f"✓ Seeded: {len(preds_seeded)} timesteps")
print()

# Extract metadata from first prediction
lats = preds_baseline[0].metadata.lat.cpu().numpy()
lons = preds_baseline[0].metadata.lon.cpu().numpy()
pressure_levels = list(preds_baseline[0].metadata.atmos_levels)

print(f"Grid: {len(lats)} lats × {len(lons)} lons")
print(f"Pressure levels: {pressure_levels}")
print()

# Find level indices
idx_300 = pressure_levels.index(300.0)
idx_500 = pressure_levels.index(500.0)
idx_700 = pressure_levels.index(700.0)
idx_850 = pressure_levels.index(850.0)

# =========================================================================
# PLOTTING FUNCTION
# =========================================================================

def plot_field_comparison(field_ctrl, field_seed, lats, lons,
                          field_name, units, timestep, hours,
                          save_path, extent=None,
                          vmin=None, vmax=None, cmap='viridis',
                          contour_levels=None, diff_vmin=None, diff_vmax=None,
                          diff_cmap=None):
    """Create 3-panel comparison: Baseline, Perturbed, Difference.

    Uses same colormap for baseline/perturbed, optionally different for difference.

    Parameters
    ----------
    diff_vmin, diff_vmax : float, optional
        Fixed color scale limits for difference plot (computed globally).
    diff_cmap : str, optional
        Colormap for difference plot. If None, uses same as cmap.
    """

    if extent is None:
        extent = [270, 300, 10, 35]  # Gulf/Caribbean/Florida

    fig = plt.figure(figsize=(20, 6))
    proj = ccrs.PlateCarree()

    LON, LAT = np.meshgrid(lons, lats)

    # Panel 1: Baseline Forecast
    ax1 = plt.subplot(1, 3, 1, projection=proj)
    ax1.set_extent(extent, crs=proj)
    ax1.coastlines(resolution='50m', linewidth=0.8)
    ax1.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
    ax1.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
    ax1.set_title('Baseline Forecast', fontsize=12, fontweight='bold')

    im1 = ax1.contourf(LON, LAT, field_ctrl,
                       levels=contour_levels if contour_levels is not None else 20,
                       cmap=cmap, vmin=vmin, vmax=vmax,
                       transform=proj, extend='both')
    plt.colorbar(im1, ax=ax1, shrink=0.8, label=units)

    # Panel 2: FTLE-Seeded Perturbed
    ax2 = plt.subplot(1, 3, 2, projection=proj)
    ax2.set_extent(extent, crs=proj)
    ax2.coastlines(resolution='50m', linewidth=0.8)
    ax2.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
    ax2.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
    ax2.set_title('FTLE-Seeded Perturbed', fontsize=12, fontweight='bold')

    im2 = ax2.contourf(LON, LAT, field_seed,
                       levels=contour_levels if contour_levels is not None else 20,
                       cmap=cmap, vmin=vmin, vmax=vmax,
                       transform=proj, extend='both')
    plt.colorbar(im2, ax=ax2, shrink=0.8, label=units)

    # Panel 3: Difference (Perturbed - Baseline)
    ax3 = plt.subplot(1, 3, 3, projection=proj)
    ax3.set_extent(extent, crs=proj)
    ax3.coastlines(resolution='50m', linewidth=0.8)
    ax3.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.3)
    ax3.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
    ax3.set_title('Difference (Perturbed - Baseline)', fontsize=12, fontweight='bold')

    diff = field_seed - field_ctrl

    # Use fixed symmetric scaling if provided, otherwise dynamic
    if diff_vmin is not None and diff_vmax is not None:
        use_vmin = diff_vmin
        use_vmax = diff_vmax
    else:
        # Dynamic: symmetric around zero
        diff_scale = np.max(np.abs(diff))
        use_vmin = -diff_scale
        use_vmax = diff_scale

    # Use explicit level boundaries for fixed color scale
    diff_levels = np.linspace(use_vmin, use_vmax, 21)

    # Use different colormap for difference if specified
    diff_colormap = diff_cmap if diff_cmap is not None else cmap

    im3 = ax3.contourf(LON, LAT, diff,
                       levels=diff_levels, cmap=diff_colormap,
                       transform=proj, extend='both')
    plt.colorbar(im3, ax=ax3, shrink=0.8, label=f'Δ{units}')

    fig.suptitle(f'{field_name} - Timestep {timestep} (+{hours}h)',
                fontsize=14, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save_path, dpi=120, bbox_inches='tight')
    plt.close()

    return diff


# =========================================================================
# ANALYZE EACH TIMESTEP
# =========================================================================

print("Analyzing fields at each timestep...")
print("This will create 5 plots per timestep (MSL, Z500, T700, RH850, WIND300)")
print()

n_timesteps = min(len(preds_baseline), len(preds_seeded))
extent = [270, 300, 10, 35]  # Gulf/Caribbean/Florida (from Ian prediction study)

# Statistics tracking
stats = {
    'timestep': [],
    'hours': [],
    'msl_max_diff': [],
    'z500_max_diff': [],
    't700_max_diff': [],
    'rh850_max_diff': [],
    'wind300_max_diff': []
}

# =========================================================================
# FIRST PASS: Compute global min and max differences across all timesteps
# =========================================================================
print("First pass: Computing global min/max differences across all timesteps...")
print("(This ensures consistent color scales in difference plots for GIF animation)")
print()

global_diff_range = {
    'msl': {'min': np.inf, 'max': -np.inf},
    'z500': {'min': np.inf, 'max': -np.inf},
    't700': {'min': np.inf, 'max': -np.inf},
    'rh850': {'min': np.inf, 'max': -np.inf},
    'wind300': {'min': np.inf, 'max': -np.inf}
}

for t in range(n_timesteps):
    pred_ctrl = preds_baseline[t]
    pred_seed = preds_seeded[t]

    # MSL Pressure
    msl_ctrl = pred_ctrl.surf_vars['msl'][0, 0].cpu().numpy() / 100
    msl_seed = pred_seed.surf_vars['msl'][0, 0].cpu().numpy() / 100
    diff_msl = msl_seed - msl_ctrl
    global_diff_range['msl']['min'] = min(global_diff_range['msl']['min'], np.min(diff_msl))
    global_diff_range['msl']['max'] = max(global_diff_range['msl']['max'], np.max(diff_msl))

    # 500 hPa Geopotential Height
    z500_ctrl = pred_ctrl.atmos_vars['z'][0, 0, idx_500].cpu().numpy() / 9.81
    z500_seed = pred_seed.atmos_vars['z'][0, 0, idx_500].cpu().numpy() / 9.81
    diff_z500 = z500_seed - z500_ctrl
    global_diff_range['z500']['min'] = min(global_diff_range['z500']['min'], np.min(diff_z500))
    global_diff_range['z500']['max'] = max(global_diff_range['z500']['max'], np.max(diff_z500))

    # 700 hPa Temperature
    t700_ctrl = pred_ctrl.atmos_vars['t'][0, 0, idx_700].cpu().numpy() - 273.15
    t700_seed = pred_seed.atmos_vars['t'][0, 0, idx_700].cpu().numpy() - 273.15
    diff_t700 = t700_seed - t700_ctrl
    global_diff_range['t700']['min'] = min(global_diff_range['t700']['min'], np.min(diff_t700))
    global_diff_range['t700']['max'] = max(global_diff_range['t700']['max'], np.max(diff_t700))

    # 850 hPa Relative Humidity
    t850_ctrl = pred_ctrl.atmos_vars['t'][0, 0, idx_850].cpu().numpy()
    q850_ctrl = pred_ctrl.atmos_vars['q'][0, 0, idx_850].cpu().numpy()
    t850_seed = pred_seed.atmos_vars['t'][0, 0, idx_850].cpu().numpy()
    q850_seed = pred_seed.atmos_vars['q'][0, 0, idx_850].cpu().numpy()

    P_850 = 850 * 100
    e_sat_ctrl = 611.2 * np.exp(17.67 * (t850_ctrl - 273.15) / (t850_ctrl - 29.65))
    q_sat_ctrl = 0.622 * e_sat_ctrl / P_850
    rh_ctrl = np.clip((q850_ctrl / q_sat_ctrl) * 100, 0, 100)

    e_sat_seed = 611.2 * np.exp(17.67 * (t850_seed - 273.15) / (t850_seed - 29.65))
    q_sat_seed = 0.622 * e_sat_seed / P_850
    rh_seed = np.clip((q850_seed / q_sat_seed) * 100, 0, 100)

    diff_rh850 = rh_seed - rh_ctrl
    global_diff_range['rh850']['min'] = min(global_diff_range['rh850']['min'], np.min(diff_rh850))
    global_diff_range['rh850']['max'] = max(global_diff_range['rh850']['max'], np.max(diff_rh850))

    # 300 hPa Wind Speed
    u300_ctrl = pred_ctrl.atmos_vars['u'][0, 0, idx_300].cpu().numpy()
    v300_ctrl = pred_ctrl.atmos_vars['v'][0, 0, idx_300].cpu().numpy()
    u300_seed = pred_seed.atmos_vars['u'][0, 0, idx_300].cpu().numpy()
    v300_seed = pred_seed.atmos_vars['v'][0, 0, idx_300].cpu().numpy()

    wind300_ctrl = np.sqrt(u300_ctrl**2 + v300_ctrl**2)
    wind300_seed = np.sqrt(u300_seed**2 + v300_seed**2)

    diff_wind300 = wind300_seed - wind300_ctrl
    global_diff_range['wind300']['min'] = min(global_diff_range['wind300']['min'], np.min(diff_wind300))
    global_diff_range['wind300']['max'] = max(global_diff_range['wind300']['max'], np.max(diff_wind300))

print("Global difference ranges across all timesteps:")
print(f"  MSL:     {global_diff_range['msl']['min']:.2f} to {global_diff_range['msl']['max']:.2f} hPa")
print(f"  Z500:    {global_diff_range['z500']['min']:.1f} to {global_diff_range['z500']['max']:.1f} m")
print(f"  T700:    {global_diff_range['t700']['min']:.3f} to {global_diff_range['t700']['max']:.3f} °C")
print(f"  RH850:   {global_diff_range['rh850']['min']:.2f} to {global_diff_range['rh850']['max']:.2f} %")
print(f"  WIND300: {global_diff_range['wind300']['min']:.2f} to {global_diff_range['wind300']['max']:.2f} m/s")
print()
print("Second pass: Creating plots with fixed difference scales...")
print()

# =========================================================================
# SECOND PASS: Create plots with fixed difference scales
# =========================================================================

for t in range(n_timesteps):
    hours = t * 6
    print(f"Timestep {t:2d} (+{hours:3d}h)...", end=' ')

    pred_ctrl = preds_baseline[t]
    pred_seed = preds_seeded[t]

    # 1. MSL Pressure
    msl_ctrl = pred_ctrl.surf_vars['msl'][0, 0].cpu().numpy() / 100  # Pa to hPa
    msl_seed = pred_seed.surf_vars['msl'][0, 0].cpu().numpy() / 100

    diff_msl = plot_field_comparison(
        msl_ctrl, msl_seed, lats, lons,
        'Mean Sea Level Pressure', 'hPa', t, hours,
        output_dir / f'msl_t{t:03d}.png',
        extent=extent, vmin=980, vmax=1020, cmap='RdYlBu_r',
        contour_levels=np.arange(980, 1021, 2),
        diff_vmin=global_diff_range['msl']['min'], diff_vmax=global_diff_range['msl']['max']
    )

    # 2. 500 hPa Geopotential Height
    z500_ctrl = pred_ctrl.atmos_vars['z'][0, 0, idx_500].cpu().numpy() / 9.81
    z500_seed = pred_seed.atmos_vars['z'][0, 0, idx_500].cpu().numpy() / 9.81

    diff_z500 = plot_field_comparison(
        z500_ctrl, z500_seed, lats, lons,
        '500 hPa Geopotential Height', 'm', t, hours,
        output_dir / f'z500_t{t:03d}.png',
        extent=extent, cmap='PRGn',  # Purple-Green for all panels
        contour_levels=np.arange(5200, 6000, 40),
        diff_vmin=global_diff_range['z500']['min'], diff_vmax=global_diff_range['z500']['max']
    )

    # 3. 700 hPa Temperature
    t700_ctrl = pred_ctrl.atmos_vars['t'][0, 0, idx_700].cpu().numpy() - 273.15
    t700_seed = pred_seed.atmos_vars['t'][0, 0, idx_700].cpu().numpy() - 273.15

    diff_t700 = plot_field_comparison(
        t700_ctrl, t700_seed, lats, lons,
        '700 hPa Temperature', '°C', t, hours,
        output_dir / f't700_t{t:03d}.png',
        extent=extent, cmap='RdYlBu_r',
        contour_levels=np.arange(-10, 26, 2),
        diff_vmin=global_diff_range['t700']['min'], diff_vmax=global_diff_range['t700']['max']
    )

    # 4. 850 hPa Relative Humidity
    t850_ctrl = pred_ctrl.atmos_vars['t'][0, 0, idx_850].cpu().numpy()
    q850_ctrl = pred_ctrl.atmos_vars['q'][0, 0, idx_850].cpu().numpy()
    t850_seed = pred_seed.atmos_vars['t'][0, 0, idx_850].cpu().numpy()
    q850_seed = pred_seed.atmos_vars['q'][0, 0, idx_850].cpu().numpy()

    # Calculate RH
    P_850 = 850 * 100
    e_sat_ctrl = 611.2 * np.exp(17.67 * (t850_ctrl - 273.15) / (t850_ctrl - 29.65))
    q_sat_ctrl = 0.622 * e_sat_ctrl / P_850
    rh_ctrl = np.clip((q850_ctrl / q_sat_ctrl) * 100, 0, 100)

    e_sat_seed = 611.2 * np.exp(17.67 * (t850_seed - 273.15) / (t850_seed - 29.65))
    q_sat_seed = 0.622 * e_sat_seed / P_850
    rh_seed = np.clip((q850_seed / q_sat_seed) * 100, 0, 100)

    diff_rh850 = plot_field_comparison(
        rh_ctrl, rh_seed, lats, lons,
        '850 hPa Relative Humidity', '%', t, hours,
        output_dir / f'rh850_t{t:03d}.png',
        extent=extent, vmin=0, vmax=100, cmap='BrBG',
        contour_levels=np.linspace(0, 100, 11),
        diff_vmin=global_diff_range['rh850']['min'], diff_vmax=global_diff_range['rh850']['max']
    )

    # 5. 300 hPa Wind Speed
    u300_ctrl = pred_ctrl.atmos_vars['u'][0, 0, idx_300].cpu().numpy()
    v300_ctrl = pred_ctrl.atmos_vars['v'][0, 0, idx_300].cpu().numpy()
    u300_seed = pred_seed.atmos_vars['u'][0, 0, idx_300].cpu().numpy()
    v300_seed = pred_seed.atmos_vars['v'][0, 0, idx_300].cpu().numpy()

    wind300_ctrl = np.sqrt(u300_ctrl**2 + v300_ctrl**2)
    wind300_seed = np.sqrt(u300_seed**2 + v300_seed**2)

    diff_wind300 = plot_field_comparison(
        wind300_ctrl, wind300_seed, lats, lons,
        '300 hPa Wind Speed', 'm/s', t, hours,
        output_dir / f'wind300_t{t:03d}.png',
        extent=extent, vmin=0, vmax=80, cmap='PuOr',  # Purple-Orange for all panels
        contour_levels=np.arange(0, 81, 5),
        diff_vmin=global_diff_range['wind300']['min'], diff_vmax=global_diff_range['wind300']['max']
    )

    # Track statistics
    stats['timestep'].append(t)
    stats['hours'].append(hours)
    stats['msl_max_diff'].append(np.max(np.abs(diff_msl)))
    stats['z500_max_diff'].append(np.max(np.abs(diff_z500)))
    stats['t700_max_diff'].append(np.max(np.abs(diff_t700)))
    stats['rh850_max_diff'].append(np.max(np.abs(diff_rh850)))
    stats['wind300_max_diff'].append(np.max(np.abs(diff_wind300)))

    print(f"✓ MSL:{stats['msl_max_diff'][-1]:.1f}hPa Z500:{stats['z500_max_diff'][-1]:.0f}m "
          f"T700:{stats['t700_max_diff'][-1]:.2f}°C RH850:{stats['rh850_max_diff'][-1]:.1f}% "
          f"W300:{stats['wind300_max_diff'][-1]:.1f}m/s")

print()
print("=" * 80)
print("  Creating Summary Plots")
print("=" * 80)
print()

# =========================================================================
# SUMMARY TIME SERIES
# =========================================================================

fig, axes = plt.subplots(3, 2, figsize=(14, 14))
axes = axes.flatten()

# MSL
axes[0].plot(stats['hours'], stats['msl_max_diff'], 'b-o', linewidth=2, markersize=4)
axes[0].set_xlabel('Forecast Hour', fontweight='bold')
axes[0].set_ylabel('Max |ΔMSL| (hPa)', fontweight='bold')
axes[0].set_title('MSL Pressure Difference Evolution', fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].axhline(y=0, color='gray', linestyle='--', alpha=0.5)

# 500 hPa Height
axes[1].plot(stats['hours'], stats['z500_max_diff'], 'g-o', linewidth=2, markersize=4)
axes[1].set_xlabel('Forecast Hour', fontweight='bold')
axes[1].set_ylabel('Max |ΔZ500| (m)', fontweight='bold')
axes[1].set_title('500 hPa Height Difference Evolution', fontweight='bold')
axes[1].grid(True, alpha=0.3)
axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)

# 700 hPa Temperature
axes[2].plot(stats['hours'], stats['t700_max_diff'], 'r-o', linewidth=2, markersize=4)
axes[2].set_xlabel('Forecast Hour', fontweight='bold')
axes[2].set_ylabel('Max |ΔT700| (°C)', fontweight='bold')
axes[2].set_title('700 hPa Temperature Difference Evolution', fontweight='bold')
axes[2].grid(True, alpha=0.3)
axes[2].axhline(y=0, color='gray', linestyle='--', alpha=0.5)

# 850 hPa RH
axes[3].plot(stats['hours'], stats['rh850_max_diff'], 'm-o', linewidth=2, markersize=4)
axes[3].set_xlabel('Forecast Hour', fontweight='bold')
axes[3].set_ylabel('Max |ΔRH850| (%)', fontweight='bold')
axes[3].set_title('850 hPa RH Difference Evolution', fontweight='bold')
axes[3].grid(True, alpha=0.3)
axes[3].axhline(y=0, color='gray', linestyle='--', alpha=0.5)

# 300 hPa Wind Speed
axes[4].plot(stats['hours'], stats['wind300_max_diff'], 'orange', marker='o', linewidth=2, markersize=4)
axes[4].set_xlabel('Forecast Hour', fontweight='bold')
axes[4].set_ylabel('Max |ΔWind300| (m/s)', fontweight='bold')
axes[4].set_title('300 hPa Wind Speed Difference Evolution', fontweight='bold')
axes[4].grid(True, alpha=0.3)
axes[4].axhline(y=0, color='gray', linestyle='--', alpha=0.5)

# Remove unused subplot
axes[5].axis('off')

plt.suptitle('Atmospheric Field Differences: FTLE-Seeded Perturbed vs Baseline Forecast\nHurricane Ian 2022',
            fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(output_dir / 'field_differences_timeseries.png', dpi=150, bbox_inches='tight')
plt.close()

print(f"✓ Saved time series: {output_dir / 'field_differences_timeseries.png'}")
print()

# =========================================================================
# SUMMARY
# =========================================================================

print("=" * 80)
print("  ✓ Field Analysis Complete!")
print("=" * 80)
print()
print(f"Output directory: {output_dir}")
print(f"Total plots created: {n_timesteps * 5} field plots + 1 summary")
print()
print("Field plots by timestep (###=000 to {:03d}):".format(n_timesteps-1))
print(f"  • msl_t###.png     - Mean sea level pressure (TC center)")
print(f"  • z500_t###.png    - 500 hPa geopotential height (steering flow)")
print(f"  • t700_t###.png    - 700 hPa temperature (diabatic heating)")
print(f"  • rh850_t###.png   - 850 hPa relative humidity (moisture)")
print(f"  • wind300_t###.png - 300 hPa wind speed (jet stream)")
print()
print("Summary plot:")
print(f"  • field_differences_timeseries.png - Evolution of all fields")
print()
print("Peak differences:")
print(f"  MSL:     {max(stats['msl_max_diff']):6.1f} hPa  at +{stats['hours'][stats['msl_max_diff'].index(max(stats['msl_max_diff']))]:3d}h")
print(f"  Z500:    {max(stats['z500_max_diff']):6.0f} m    at +{stats['hours'][stats['z500_max_diff'].index(max(stats['z500_max_diff']))]:3d}h")
print(f"  T700:    {max(stats['t700_max_diff']):6.2f} °C  at +{stats['hours'][stats['t700_max_diff'].index(max(stats['t700_max_diff']))]:3d}h")
print(f"  RH850:   {max(stats['rh850_max_diff']):6.1f} %   at +{stats['hours'][stats['rh850_max_diff'].index(max(stats['rh850_max_diff']))]:3d}h")
print(f"  WIND300: {max(stats['wind300_max_diff']):6.1f} m/s at +{stats['hours'][stats['wind300_max_diff'].index(max(stats['wind300_max_diff']))]:3d}h")
print()
print("Next steps:")
print("  1. Examine individual timestep plots to see field evolution")
print("  2. Look for steering flow changes in Z500 difference fields")
print("  3. Check if T700 warming persists or dissipates")
print("  4. Compare results with Sandy to identify common mechanisms")
print()
