"""
Cloud Seeding Perturbation Module

This module implements physically-consistent cloud seeding perturbations
for weather modification experiments. The perturbations simulate ice nucleation
through vapor deposition, including proper thermodynamic calculations.

Physical Process:
- Ice nucleation via deposition (vapor → ice directly)
- Latent heat release (L_d = L_v + L_f = 2.834 MJ/kg)
- Moisture removal and precipitation
- Thermodynamic consistency checks

Author: Adapted from perturbation_trail_111.ipynb
Date: 2025-12-02
"""

import numpy as np
import torch


def calculate_q_sat(T, P):
    """
    Calculate saturation mixing ratio using Clausius-Clapeyron equation.

    Parameters:
    -----------
    T : torch.Tensor
        Temperature in Kelvin
    P : float or torch.Tensor
        Pressure in Pascals

    Returns:
    --------
    q_sat : torch.Tensor
        Saturation mixing ratio (kg/kg)
    """
    # Constants
    epsilon = 0.622  # R_d / R_v (molecular weight ratio)
    e_0 = 611.2      # Pa (saturation vapor pressure at 273.15 K)
    T_0 = 273.15     # K (reference temperature)
    L_v = 2.5e6      # J/kg (latent heat of vaporization)
    R_v = 461.5      # J/(kg·K) (gas constant for water vapor)

    # Saturation vapor pressure (Clausius-Clapeyron)
    e_sat = e_0 * torch.exp((L_v / R_v) * (1/T_0 - 1/T))

    # Saturation mixing ratio
    q_sat = epsilon * e_sat / (P - e_sat)

    return q_sat


def create_seeding_mask(seeding_locations, lat_grid, lon_grid):
    """
    Create a combined 2D mask from multiple circular seeding regions.

    Parameters:
    -----------
    seeding_locations : list of dict
        List of seeding locations with keys:
        - 'lat_center': Center latitude (degrees)
        - 'lon_center': Center longitude (degrees, 0-360)
        - 'radius_km': Radius in kilometers
    lat_grid : array or torch.Tensor (lat,)
        Latitude coordinates
    lon_grid : array or torch.Tensor (lon,)
        Longitude coordinates

    Returns:
    --------
    mask : numpy array (lat, lon)
        Boolean mask, True where seeding should occur
    """

    # Convert to numpy if needed
    if isinstance(lat_grid, torch.Tensor):
        lat_grid = lat_grid.cpu().numpy()
    if isinstance(lon_grid, torch.Tensor):
        lon_grid = lon_grid.cpu().numpy()

    # Create 2D grids
    lon_2d, lat_2d = np.meshgrid(lon_grid, lat_grid)

    # Initialize mask
    mask = np.zeros_like(lat_2d, dtype=bool)

    # Loop through each seeding location
    for location in seeding_locations:
        lat_center = location['lat_center']
        lon_center = location['lon_center']
        radius_km = location['radius_km']

        # Calculate great circle distance
        # Approximate for mid-latitudes using Haversine-like formula
        dlat = lat_2d - lat_center
        dlon = lon_2d - lon_center

        # Handle longitude wrapping
        dlon = np.where(dlon > 180, dlon - 360, dlon)
        dlon = np.where(dlon < -180, dlon + 360, dlon)

        # Distance in km (approximation)
        # More accurate: use Haversine
        lat_rad = np.deg2rad(lat_2d)
        lat_c_rad = np.deg2rad(lat_center)
        dlat_rad = np.deg2rad(dlat)
        dlon_rad = np.deg2rad(dlon)

        a = np.sin(dlat_rad/2)**2 + np.cos(lat_rad) * np.cos(lat_c_rad) * np.sin(dlon_rad/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        distance_km = 6371.0 * c  # Earth radius = 6371 km

        # Add to mask where within radius
        mask |= (distance_km <= radius_km)

    return mask


def apply_physically_consistent_cloud_seeding(batch, seeding_mask_spatial, seeding_params):
    """
    Apply physically-consistent cloud seeding perturbation to atmospheric batch.

    This function modifies temperature and humidity fields to simulate the effects
    of cloud seeding through ice nucleation (vapor deposition process).

    Parameters:
    -----------
    batch : Batch object
        Aurora batch with atmos_vars containing 't' (temperature) and 'q' (humidity)
        Shape: [batch, time, level, lat, lon]
    seeding_mask_spatial : numpy array (lat, lon)
        Boolean or float mask indicating seeding regions
    seeding_params : dict
        Configuration parameters:
        - 'layers_mb': list of pressure levels (hPa) to apply seeding
        - 'freeze_efficiency': fraction of vapor that freezes (0-1)
        - 'fallout_fraction': fraction of frozen water that precipitates (0-1)
        - 'max_removal_fraction': max fraction of vapor to remove (0-1)
        - 'energy_method': 'net_realistic' (recommended)
        - 'vertical_coupling': bool, enable coupling to adjacent levels
        - 'coupling_factor': strength of vertical coupling (0-1)

    Returns:
    --------
    delta_T_applied : torch.Tensor (level, lat, lon)
        Temperature change applied
    delta_q_applied : torch.Tensor (level, lat, lon)
        Humidity change applied
    diagnostics : dict
        Diagnostic information about the perturbation
    """

    # ========== PHYSICAL CONSTANTS ==========
    L_f = 334000    # J/kg (latent heat of fusion)
    L_v = 2500000   # J/kg (latent heat of vaporization)
    L_d = L_v + L_f # J/kg (latent heat of DEPOSITION - vapor to ice)
    C_p = 1004      # J/(kg·K) (specific heat of air at constant pressure)
    epsilon = 0.622 # R_d / R_v (molecular weight ratio)

    # ========== PARAMETERS ==========
    layer_indices = [batch.metadata.atmos_levels.index(lev)
                     for lev in seeding_params['layers_mb']]
    pressure_levels_hPa = list(batch.metadata.atmos_levels)

    device = batch.atmos_vars["t"].device
    mask_torch = torch.from_numpy(seeding_mask_spatial).float().to(device)

    delta_T_applied = torch.zeros_like(batch.atmos_vars["t"][0, 1])
    delta_q_applied = torch.zeros_like(batch.atmos_vars["q"][0, 1])

    # Tracking for diagnostics
    diagnostics = {
        'levels': [],
        'RH_before': [],
        'RH_after': [],
        'q_frozen_mean': [],
        'q_removed_mean': [],
        'delta_T_mean': [],
        'q_precipitated_mean': [],
        'energy_released_mean': [],
        'warnings': []
    }

    for level_idx in layer_indices:
        P_hPa = pressure_levels_hPa[level_idx]

        # ========== INITIAL STATE ==========
        T_old = batch.atmos_vars["t"][0, 1, level_idx].clone()
        q_old = batch.atmos_vars["q"][0, 1, level_idx].clone()
        P_Pa = P_hPa * 100  # hPa → Pa

        # Calculate initial saturation state
        q_sat_old = calculate_q_sat(T_old, P_Pa)
        RH_old = (q_old / (q_sat_old + 1e-10)).clamp(max=1.0)

        # ========== SEEDING: ICE NUCLEATION (DEPOSITION) ==========
        # Physical process: Seeding particles provide nucleation sites
        # Water vapor deposits directly onto ice nuclei (vapor → ice)
        freeze_efficiency = seeding_params.get('freeze_efficiency', 0.30)
        max_removal_fraction = seeding_params.get('max_removal_fraction', 0.80)

        # Calculate potential freezing
        q_frozen_potential = q_old * freeze_efficiency * mask_torch

        # Limit to preserve physical moisture levels
        q_frozen = torch.minimum(q_frozen_potential, q_old * max_removal_fraction)

        # Track where moisture limitation applied
        moisture_limited = (q_frozen < q_frozen_potential).any()
        if moisture_limited and level_idx == layer_indices[0]:
            pct_limited = ((q_frozen < q_frozen_potential).sum() /
                           (mask_torch > 0).sum() * 100).item()
            diagnostics['warnings'].append(
                f"ℹ️  {pct_limited:.1f}% of seeded cells were moisture-limited "
                f"(too dry for full {freeze_efficiency*100:.0f}% efficiency)"
            )

        # ========== LATENT HEAT RELEASE ==========
        # CRITICAL: Vapor → ice is DEPOSITION, not freezing!
        # - Deposition (vapor → ice): releases L_v + L_f = 2.834 MJ/kg
        delta_E = L_d * q_frozen  # J/kg (energy released to air)
        delta_T = delta_E / C_p   # K (temperature increase)

        # ========== MOISTURE REMOVAL ==========
        # ALL frozen vapor leaves the vapor phase
        q_removed = q_frozen  # kg/kg

        # Track precipitation for diagnostics
        fallout_fraction = seeding_params.get('fallout_fraction', 0.40)
        q_precip = q_frozen * fallout_fraction

        # ========== APPLY CHANGES ==========
        T_new = T_old + delta_T
        q_new = q_old - q_removed

        # ========== THERMODYNAMIC CONSISTENCY CHECK ==========
        q_sat_new = calculate_q_sat(T_new, P_Pa)
        RH_new = q_new / (q_sat_new + 1e-10)

        # Check for unphysical states
        if (q_new < 0).any():
            min_q = q_new.min().item()
            diagnostics['warnings'].append(
                f"⚠️  Level {P_hPa:.0f} hPa: Negative q detected! Min q = {min_q:.6f} kg/kg"
            )
            q_new = q_new.clamp(min=0)
            q_removed_actual = q_old - q_new
            q_frozen_actual = q_removed_actual
            delta_T = L_d * q_frozen_actual / C_p
            T_new = T_old + delta_T
            q_sat_new = calculate_q_sat(T_new, P_Pa)
            RH_new = q_new / (q_sat_new + 1e-10)

        if (RH_new > 1.5).any():
            max_rh = RH_new.max().item()
            diagnostics['warnings'].append(
                f"⚠️  Level {P_hPa:.0f} hPa: High supersaturation! Max RH = {max_rh*100:.1f}%"
            )

        if (RH_new < 0.01).any() and (RH_old.mean() > 0.1):
            min_rh = RH_new.min().item()
            diagnostics['warnings'].append(
                f"⚠️  Level {P_hPa:.0f} hPa: Created very dry air! Min RH = {min_rh*100:.1f}%"
            )

        RH_change_ratio = (RH_new.mean() / (RH_old.mean() + 1e-10)).item()
        if RH_change_ratio < 0.2:
            diagnostics['warnings'].append(
                f"⚠️  Level {P_hPa:.0f} hPa: RH dropped to {RH_change_ratio*100:.1f}% of original. "
                f"Consider reducing freeze_efficiency."
            )

        # ========== COMMIT CHANGES (ONLY timestep 1) ==========
        batch.atmos_vars["t"][0, 1, level_idx] = T_new
        batch.atmos_vars["q"][0, 1, level_idx] = q_new

        delta_T_applied[level_idx] = delta_T
        delta_q_applied[level_idx] = -q_removed

        # ========== STORE DIAGNOSTICS ==========
        seeded_region = mask_torch > 0
        diagnostics['levels'].append(P_hPa)
        diagnostics['RH_before'].append(RH_old[seeded_region].mean().item())
        diagnostics['RH_after'].append(RH_new[seeded_region].mean().item())
        diagnostics['q_frozen_mean'].append(q_frozen[seeded_region].mean().item())
        diagnostics['q_removed_mean'].append(q_removed[seeded_region].mean().item())
        diagnostics['delta_T_mean'].append(delta_T[seeded_region].mean().item())
        diagnostics['q_precipitated_mean'].append(q_precip[seeded_region].mean().item())
        diagnostics['energy_released_mean'].append(delta_E[seeded_region].mean().item())

        # ========== VERTICAL COUPLING ==========
        if seeding_params.get('vertical_coupling', False):
            coupling_factor = seeding_params.get('coupling_factor', 0.3)
            for offset in [-1, 1]:
                adj_idx = level_idx + offset
                if 0 <= adj_idx < len(batch.metadata.atmos_levels):
                    delta_T_adj = delta_T * coupling_factor
                    batch.atmos_vars["t"][0, 1, adj_idx] += delta_T_adj
                    delta_T_applied[adj_idx] += delta_T_adj

    return delta_T_applied, delta_q_applied, diagnostics


def print_diagnostics(diagnostics, seeding_params):
    """
    Print diagnostic information about the seeding perturbation.

    Parameters:
    -----------
    diagnostics : dict
        Diagnostic information from apply_physically_consistent_cloud_seeding
    seeding_params : dict
        Seeding parameters used
    """

    print("\n" + "="*80)
    print("☁️ PHYSICALLY CONSISTENT Cloud Seeding Applied")
    print("="*80)

    print("\n⚙️  SEEDING PARAMETERS:")
    print(f"  Pressure levels: {seeding_params['layers_mb']} hPa")
    print(f"  Freeze efficiency: {seeding_params['freeze_efficiency']*100:.0f}%")
    print(f"  Fallout fraction: {seeding_params['fallout_fraction']*100:.0f}%")
    print(f"  Max removal fraction: {seeding_params['max_removal_fraction']*100:.0f}%")
    print(f"  Vertical coupling: {seeding_params.get('vertical_coupling', False)}")

    print("\n📊 RESULTS BY PRESSURE LEVEL:")
    print(f"{'Level':>8} {'RH Before':>10} {'RH After':>10} {'ΔT':>8} {'Δq':>12} {'Precip':>12}")
    print(f"{'(hPa)':>8} {'(%)':>10} {'(%)':>10} {'(K)':>8} {'(g/kg)':>12} {'(g/kg)':>12}")
    print("-" * 80)

    for i, level in enumerate(diagnostics['levels']):
        rh_before = diagnostics['RH_before'][i] * 100
        rh_after = diagnostics['RH_after'][i] * 100
        delta_t = diagnostics['delta_T_mean'][i]
        delta_q = diagnostics['q_removed_mean'][i] * 1000  # to g/kg
        precip = diagnostics['q_precipitated_mean'][i] * 1000  # to g/kg

        print(f"{level:8.0f} {rh_before:10.1f} {rh_after:10.1f} {delta_t:8.3f} "
              f"{-delta_q:12.4f} {precip:12.4f}")

    if diagnostics['warnings']:
        print("\n⚠️  WARNINGS:")
        for warning in diagnostics['warnings']:
            print(f"  {warning}")

    print("\n" + "="*80)


# Default seeding configurations for different scenarios
SEEDING_CONFIG_AR = {
    'layers_mb': [850.0, 700.0, 600.0, 500.0],
    'freeze_efficiency': 0.70,
    'fallout_fraction': 0.90,
    'max_removal_fraction': 0.60,
    'energy_method': 'net_realistic',
    'vertical_coupling': False,
    'coupling_factor': 0.3
}

SEEDING_CONFIG_HURRICANE = {
    'layers_mb': [925.0, 850.0, 700.0],
    'freeze_efficiency': 0.60,
    'fallout_fraction': 0.80,
    'max_removal_fraction': 0.50,
    'energy_method': 'net_realistic',
    'vertical_coupling': True,
    'coupling_factor': 0.4
}

SEEDING_CONFIG_FREEZE = {
    'layers_mb': [700.0, 600.0, 500.0],
    'freeze_efficiency': 0.80,
    'fallout_fraction': 0.95,
    'max_removal_fraction': 0.70,
    'energy_method': 'net_realistic',
    'vertical_coupling': False,
    'coupling_factor': 0.2
}
