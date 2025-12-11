"""
Integrated Vapor Transport (IVT) Analysis Module

This module provides functions to calculate and analyze IVT for atmospheric river
detection and tracking. IVT is a key diagnostic for identifying moisture transport
patterns and AR landfall locations.

IVT = ∫(q * V) dp / g, integrated over pressure levels

Author: Adapted from perturbation_trail_111.ipynb
Date: 2025-12-02
"""

import numpy as np
import torch
from scipy.interpolate import RegularGridInterpolator


def calculate_ivt_integrated(u_data, v_data, q_data, pressure_levels,
                              p_top=200, p_bottom=1000):
    """
    Calculate Integrated Vapor Transport (IVT) for atmospheric river detection.

    Parameters:
    -----------
    u_data : torch.Tensor or array (level, lat, lon) or (batch, level, lat, lon)
        Zonal wind component in m/s
    v_data : torch.Tensor or array
        Meridional wind component in m/s
    q_data : torch.Tensor or array
        Specific humidity in kg/kg
    pressure_levels : tuple or torch.Tensor
        Pressure levels in hPa
    p_top : float
        Top pressure level for integration (default: 200 hPa)
    p_bottom : float
        Bottom pressure level for integration (default: 1000 hPa)

    Returns:
    --------
    ivt_u : torch.Tensor or array (lat, lon)
        Zonal component of IVT in kg/(m·s)
    ivt_v : torch.Tensor or array (lat, lon)
        Meridional component of IVT in kg/(m·s)
    ivt_magnitude : torch.Tensor or array (lat, lon)
        IVT magnitude in kg/(m·s)
    """

    g = 9.81  # m/s²

    # Convert to torch tensor if needed
    is_torch = isinstance(u_data, torch.Tensor)
    device = u_data.device if is_torch else None

    # Convert pressure levels to tensor if needed
    if isinstance(pressure_levels, tuple):
        if is_torch:
            pressure_levels = torch.tensor(pressure_levels, dtype=torch.float32, device=device)
        else:
            pressure_levels = np.array(pressure_levels)

    # Convert hPa to Pa
    if is_torch:
        pressure_levels_pa = pressure_levels * 100
    else:
        pressure_levels_pa = pressure_levels * 100

    # Filter to only include levels between p_top and p_bottom
    if is_torch:
        mask = (pressure_levels >= p_top) & (pressure_levels <= p_bottom)
        level_indices = torch.where(mask)[0]
    else:
        mask = (pressure_levels >= p_top) & (pressure_levels <= p_bottom)
        level_indices = np.where(mask)[0]

    if len(level_indices) == 0:
        raise ValueError(f"No pressure levels found between {p_top} and {p_bottom} hPa")

    # Handle batch dimension
    if u_data.ndim == 4:
        # Has batch dimension
        u_data = u_data[:, level_indices]
        v_data = v_data[:, level_indices]
        q_data = q_data[:, level_indices]
    else:
        # No batch dimension
        u_data = u_data[level_indices]
        v_data = v_data[level_indices]
        q_data = q_data[level_indices]

    p_filtered = pressure_levels_pa[level_indices]

    # Calculate IVT using trapezoidal integration
    # IVT = (1/g) * ∫ q * V dp

    if is_torch:
        # Sort by pressure (descending: high pressure at bottom)
        sort_idx = torch.argsort(p_filtered, descending=True)
        p_sorted = p_filtered[sort_idx]

        if u_data.ndim == 4:
            u_sorted = u_data[:, sort_idx]
            v_sorted = v_data[:, sort_idx]
            q_sorted = q_data[:, sort_idx]

            # Compute integrands
            integrand_u = q_sorted * u_sorted
            integrand_v = q_sorted * v_sorted

            # Trapezoidal integration over pressure
            ivt_u = torch.trapz(integrand_u, p_sorted, dim=1) / g
            ivt_v = torch.trapz(integrand_v, p_sorted, dim=1) / g
        else:
            u_sorted = u_data[sort_idx]
            v_sorted = v_data[sort_idx]
            q_sorted = q_data[sort_idx]

            integrand_u = q_sorted * u_sorted
            integrand_v = q_sorted * v_sorted

            ivt_u = torch.trapz(integrand_u, p_sorted, dim=0) / g
            ivt_v = torch.trapz(integrand_v, p_sorted, dim=0) / g

        ivt_magnitude = torch.sqrt(ivt_u**2 + ivt_v**2)

    else:
        # NumPy version
        sort_idx = np.argsort(p_filtered)[::-1]  # Descending
        p_sorted = p_filtered[sort_idx]

        if u_data.ndim == 4:
            u_sorted = u_data[:, sort_idx]
            v_sorted = v_data[:, sort_idx]
            q_sorted = q_data[:, sort_idx]

            integrand_u = q_sorted * u_sorted
            integrand_v = q_sorted * v_sorted

            ivt_u = np.trapz(integrand_u, p_sorted, axis=1) / g
            ivt_v = np.trapz(integrand_v, p_sorted, axis=1) / g
        else:
            u_sorted = u_data[sort_idx]
            v_sorted = v_data[sort_idx]
            q_sorted = q_data[sort_idx]

            integrand_u = q_sorted * u_sorted
            integrand_v = q_sorted * v_sorted

            ivt_u = np.trapz(integrand_u, p_sorted, axis=0) / g
            ivt_v = np.trapz(integrand_v, p_sorted, axis=0) / g

        ivt_magnitude = np.sqrt(ivt_u**2 + ivt_v**2)

    return ivt_u, ivt_v, ivt_magnitude


def calculate_ivt_trajectory(predictions, pressure_levels):
    """
    Calculate IVT time series from model predictions.

    Parameters:
    -----------
    predictions : list of Batch objects
        Model predictions at different time steps
    pressure_levels : tuple or array
        Pressure levels in hPa

    Returns:
    --------
    ivt_trajectory : list of arrays
        IVT magnitude at each time step
    """

    ivt_trajectory = []

    for i, pred in enumerate(predictions):
        u = pred.atmos_vars["u"][:, 0]
        v = pred.atmos_vars["v"][:, 0]
        q = pred.atmos_vars["q"][:, 0]

        _, _, ivt_mag = calculate_ivt_integrated(u, v, q, pressure_levels)

        # Convert to numpy if torch
        if isinstance(ivt_mag, torch.Tensor):
            ivt_mag = ivt_mag[0].cpu().numpy()
        else:
            ivt_mag = ivt_mag[0]

        ivt_trajectory.append(ivt_mag)

    return ivt_trajectory


def find_ar_landfall_location(ivt_field, lats, lons, coastal_lats, coastal_lons,
                               ivt_threshold=250):
    """
    Find AR landfall location by identifying maximum IVT along coastline.

    Parameters:
    -----------
    ivt_field : array (lat, lon)
        IVT magnitude field in kg/(m·s)
    lats : array (lat,)
        Latitude coordinates
    lons : array (lon,)
        Longitude coordinates
    coastal_lats : array
        Coastline latitude points
    coastal_lons : array
        Coastline longitude points
    ivt_threshold : float
        Minimum IVT to consider as AR (kg/(m·s))

    Returns:
    --------
    landfall_info : dict
        Dictionary with keys:
        - 'lat': landfall latitude
        - 'lon': landfall longitude
        - 'ivt': IVT magnitude at landfall
        - 'found': bool, whether AR was detected
    """

    # Create interpolator
    interpolator = RegularGridInterpolator(
        (lats, lons),
        ivt_field,
        method='linear',
        bounds_error=False,
        fill_value=0
    )

    # Sample IVT along coastline
    coastal_points = np.stack([coastal_lats, coastal_lons], axis=1)
    coastal_ivt = interpolator(coastal_points)

    # Find maximum above threshold
    max_idx = np.argmax(coastal_ivt)
    max_ivt = coastal_ivt[max_idx]

    if max_ivt >= ivt_threshold:
        return {
            'lat': coastal_lats[max_idx],
            'lon': coastal_lons[max_idx],
            'ivt': max_ivt,
            'found': True
        }
    else:
        return {
            'lat': np.nan,
            'lon': np.nan,
            'ivt': max_ivt,
            'found': False
        }


def calculate_landfall_trajectory(ivt_trajectory_control, ivt_trajectory_seeded,
                                   lats, lons, coastal_lats, coastal_lons,
                                   ivt_threshold=250, hours_per_step=6):
    """
    Track AR landfall locations over time for control and seeded simulations.

    Parameters:
    -----------
    ivt_trajectory_control : list of arrays
        Control simulation IVT time series
    ivt_trajectory_seeded : list of arrays
        Seeded simulation IVT time series
    lats : array
        Latitude coordinates
    lons : array
        Longitude coordinates
    coastal_lats : array
        Coastline latitude points
    coastal_lons : array
        Coastline longitude points
    ivt_threshold : float
        AR detection threshold
    hours_per_step : int
        Hours between time steps

    Returns:
    --------
    landfall_control : list of dict
        Landfall locations for control
    landfall_seeded : list of dict
        Landfall locations for seeded
    """

    landfall_control = []
    landfall_seeded = []

    n_steps = min(len(ivt_trajectory_control), len(ivt_trajectory_seeded))

    for i in range(n_steps):
        hours = i * hours_per_step

        # Control
        lf_ctrl = find_ar_landfall_location(
            ivt_trajectory_control[i], lats, lons,
            coastal_lats, coastal_lons, ivt_threshold
        )
        lf_ctrl['hours'] = hours
        landfall_control.append(lf_ctrl)

        # Seeded
        lf_seed = find_ar_landfall_location(
            ivt_trajectory_seeded[i], lats, lons,
            coastal_lats, coastal_lons, ivt_threshold
        )
        lf_seed['hours'] = hours
        landfall_seeded.append(lf_seed)

    return landfall_control, landfall_seeded


def create_coastline_profile(lat_range, coastline_lon, n_points=100):
    """
    Create a simplified coastline profile for AR landfall tracking.

    Parameters:
    -----------
    lat_range : tuple (lat_min, lat_max)
        Latitude range for coastline
    coastline_lon : float
        Approximate longitude of coastline
    n_points : int
        Number of points along coastline

    Returns:
    --------
    coastal_lats : array
        Coastline latitude points
    coastal_lons : array
        Coastline longitude points (constant)
    """

    coastal_lats = np.linspace(lat_range[0], lat_range[1], n_points)
    coastal_lons = np.full(n_points, coastline_lon)

    return coastal_lats, coastal_lons


# AR detection thresholds for different regions
IVT_THRESHOLD_WEST_COAST = 250  # kg/(m·s)
IVT_THRESHOLD_EAST_COAST = 300  # kg/(m·s)
IVT_THRESHOLD_EUROPE = 250      # kg/(m·s)

# Coastline longitudes (approximate)
COASTLINE_CALIFORNIA = 235  # ~125W
COASTLINE_JAPAN = 140       # ~140E
COASTLINE_EUROPE = 0        # ~0E
