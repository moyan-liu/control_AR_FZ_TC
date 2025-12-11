"""
FTLE (Finite-Time Lyapunov Exponent) Calculation Module

This module provides functions to calculate FTLE fields from atmospheric data,
which identify regions of high flow sensitivity for targeted perturbations.

Author: Adapted from perturbation_trail_111.ipynb
Date: 2025-12-02
"""

import numpy as np
import torch
from scipy.interpolate import RegularGridInterpolator


def advect_particles(u_field, v_field, lat_grid, lon_grid, dt_hours=6,
                     integration_time_hours=48, direction='forward'):
    """
    Advect particles using wind fields to calculate trajectories.

    Parameters:
    -----------
    u_field : array (lat, lon)
        Zonal wind component in m/s
    v_field : array (lat, lon)
        Meridional wind component in m/s
    lat_grid : array (lat,)
        Latitude coordinates
    lon_grid : array (lon,)
        Longitude coordinates
    dt_hours : float
        Time step for integration in hours
    integration_time_hours : float
        Total integration time in hours
    direction : str
        'forward' or 'backward' integration

    Returns:
    --------
    final_positions : array (lat, lon, 2)
        Final positions of particles [lat, lon] for each grid point
    """

    # Convert to numpy if torch tensors
    if isinstance(u_field, torch.Tensor):
        u_field = u_field.cpu().numpy()
    if isinstance(v_field, torch.Tensor):
        v_field = v_field.cpu().numpy()
    if isinstance(lat_grid, torch.Tensor):
        lat_grid = lat_grid.cpu().numpy()
    if isinstance(lon_grid, torch.Tensor):
        lon_grid = lon_grid.cpu().numpy()

    # Create 2D grids
    lon_2d, lat_2d = np.meshgrid(lon_grid, lat_grid)

    # Initialize particle positions
    particle_lats = lat_2d.copy()
    particle_lons = lon_2d.copy()

    # Time step in seconds
    dt_seconds = dt_hours * 3600
    n_steps = int(integration_time_hours / dt_hours)

    # Direction multiplier
    time_direction = 1 if direction == 'forward' else -1

    # Create interpolators
    u_interp = RegularGridInterpolator(
        (lat_grid, lon_grid), u_field,
        method='linear', bounds_error=False, fill_value=0
    )
    v_interp = RegularGridInterpolator(
        (lat_grid, lon_grid), v_field,
        method='linear', bounds_error=False, fill_value=0
    )

    # Advection loop
    for step in range(n_steps):
        # Get wind at current positions
        points = np.stack([particle_lats.ravel(), particle_lons.ravel()], axis=1)
        u_vals = u_interp(points).reshape(particle_lats.shape)
        v_vals = v_interp(points).reshape(particle_lats.shape)

        # Convert wind to lat/lon displacement
        # u: m/s eastward, v: m/s northward
        # 1 degree latitude ≈ 111 km
        # 1 degree longitude ≈ 111 km * cos(lat)

        dlat = (v_vals * dt_seconds) / (111000.0) * time_direction  # degrees
        dlon = (u_vals * dt_seconds) / (111000.0 * np.cos(np.deg2rad(particle_lats))) * time_direction

        # Update positions
        particle_lats += dlat
        particle_lons += dlon

        # Handle longitude wrapping
        particle_lons = np.mod(particle_lons, 360)

        # Clip latitudes to valid range
        particle_lats = np.clip(particle_lats, -90, 90)

    # Stack final positions
    final_positions = np.stack([particle_lats, particle_lons], axis=-1)

    return final_positions


def calculate_ftle(final_positions, lat_grid, lon_grid, integration_time_hours=48):
    """
    Calculate FTLE field from final particle positions.

    Parameters:
    -----------
    final_positions : array (lat, lon, 2)
        Final positions of particles
    lat_grid : array (lat,)
        Latitude coordinates
    lon_grid : array (lon,)
        Longitude coordinates
    integration_time_hours : float
        Integration time in hours

    Returns:
    --------
    ftle_field : array (lat, lon)
        FTLE values in units of 1/day
    """

    nlat, nlon = len(lat_grid), len(lon_grid)
    ftle_field = np.zeros((nlat, nlon))

    # Grid spacing (convert to km)
    dlat_deg = np.abs(lat_grid[1] - lat_grid[0])
    dlon_deg = np.abs(lon_grid[1] - lon_grid[0])
    dlat_km = dlat_deg * 111.0

    # Integration time in days
    T = integration_time_hours / 24.0

    for i in range(1, nlat-1):
        # Longitude spacing varies with latitude
        dlon_km = dlon_deg * 111.0 * np.cos(np.deg2rad(lat_grid[i]))

        for j in range(1, nlon-1):
            # Get neighboring positions
            pos_ij = final_positions[i, j]
            pos_ip = final_positions[i+1, j]
            pos_im = final_positions[i-1, j]
            pos_jp = final_positions[i, j+1]
            pos_jm = final_positions[i, j-1]

            # Calculate gradient matrix (deformation tensor)
            # dX/dlat
            dX_dlat = (pos_ip - pos_im) / (2 * dlat_km)
            # dX/dlon
            dX_dlon = (pos_jp - pos_jm) / (2 * dlon_km)

            # Gradient matrix F
            F = np.array([
                [dX_dlat[0], dX_dlon[0]],  # d(lat_final)/d(lat_0), d(lat_final)/d(lon_0)
                [dX_dlat[1], dX_dlon[1]]   # d(lon_final)/d(lat_0), d(lon_final)/d(lon_0)
            ])

            # Cauchy-Green strain tensor: C = F^T * F
            C = F.T @ F

            # FTLE = (1/2T) * ln(λ_max), where λ_max is largest eigenvalue of C
            eigenvalues = np.linalg.eigvalsh(C)
            lambda_max = np.max(eigenvalues)

            if lambda_max > 0:
                ftle_field[i, j] = (1.0 / (2.0 * T)) * np.log(lambda_max)
            else:
                ftle_field[i, j] = 0.0

    # Handle boundaries (copy from neighbors)
    ftle_field[0, :] = ftle_field[1, :]
    ftle_field[-1, :] = ftle_field[-2, :]
    ftle_field[:, 0] = ftle_field[:, 1]
    ftle_field[:, -1] = ftle_field[:, -2]

    return ftle_field


def calculate_ftle_from_winds(u_field, v_field, lat_grid, lon_grid,
                               dt_hours=6, integration_time_hours=48,
                               direction='forward'):
    """
    Complete FTLE calculation pipeline from wind fields.

    Parameters:
    -----------
    u_field : array (lat, lon)
        Zonal wind component in m/s
    v_field : array (lat, lon)
        Meridional wind component in m/s
    lat_grid : array (lat,)
        Latitude coordinates
    lon_grid : array (lon,)
        Longitude coordinates
    dt_hours : float
        Time step for integration
    integration_time_hours : float
        Total integration time
    direction : str
        'forward' or 'backward'

    Returns:
    --------
    ftle_field : array (lat, lon)
        FTLE values in units of 1/day
    final_positions : array (lat, lon, 2)
        Final particle positions
    """

    print(f"🌀 Calculating {direction} FTLE...")
    print(f"   Integration time: {integration_time_hours} hours")
    print(f"   Time step: {dt_hours} hours")

    # Step 1: Advect particles
    print("   Step 1/2: Advecting particles...")
    final_positions = advect_particles(
        u_field, v_field, lat_grid, lon_grid,
        dt_hours=dt_hours,
        integration_time_hours=integration_time_hours,
        direction=direction
    )

    # Step 2: Calculate FTLE
    print("   Step 2/2: Computing FTLE field...")
    ftle_field = calculate_ftle(
        final_positions, lat_grid, lon_grid,
        integration_time_hours=integration_time_hours
    )

    print(f"✅ FTLE calculation complete")
    print(f"   FTLE range: [{np.min(ftle_field):.4f}, {np.max(ftle_field):.4f}] day⁻¹")

    return ftle_field, final_positions


def crop_region(field, lat_grid, lon_grid, lat_range, lon_range):
    """
    Crop a field to a specific geographic region.

    Parameters:
    -----------
    field : array (lat, lon)
        Field to crop
    lat_grid : array (lat,)
        Latitude coordinates
    lon_grid : array (lon,)
        Longitude coordinates
    lat_range : tuple (lat_min, lat_max)
        Latitude bounds
    lon_range : tuple (lon_min, lon_max)
        Longitude bounds

    Returns:
    --------
    field_cropped : array
        Cropped field
    lat_cropped : array
        Cropped latitude coordinates
    lon_cropped : array
        Cropped longitude coordinates
    """

    lat_mask = (lat_grid >= lat_range[0]) & (lat_grid <= lat_range[1])
    lon_mask = (lon_grid >= lon_range[0]) & (lon_grid <= lon_range[1])

    field_cropped = field[np.ix_(lat_mask, lon_mask)]
    lat_cropped = lat_grid[lat_mask]
    lon_cropped = lon_grid[lon_mask]

    return field_cropped, lat_cropped, lon_cropped
