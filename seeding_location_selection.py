"""
Seeding Location Selection Module

This module provides functions to select optimal seeding locations based on
FTLE fields, jet stream characteristics, and geographic constraints.

The selection strategy combines:
1. High FTLE values (regions of high flow sensitivity)
2. Jet stream edge proximity (dynamically active regions)
3. Geographic filtering (region of interest)
4. Spatial separation (avoid clustering)

Author: Adapted from perturbation_trail_111.ipynb
Date: 2025-12-02
"""

import numpy as np
from scipy.interpolate import RegularGridInterpolator


def interpolate_wind_to_ftle_grid(wind_field, wind_lats, wind_lons, ftle_lats, ftle_lons):
    """
    Interpolate wind field to FTLE grid resolution.

    Parameters:
    -----------
    wind_field : array (lat, lon)
        Wind field to interpolate
    wind_lats : array (lat,)
        Wind field latitude coordinates
    wind_lons : array (lon,)
        Wind field longitude coordinates
    ftle_lats : array (lat,)
        FTLE grid latitude coordinates
    ftle_lons : array (lon,)
        FTLE grid longitude coordinates

    Returns:
    --------
    wind_at_ftle : array (ftle_lat, ftle_lon)
        Wind field interpolated to FTLE grid
    """

    # Create interpolator
    interp = RegularGridInterpolator(
        (wind_lats, wind_lons),
        wind_field,
        method='linear',
        bounds_error=False,
        fill_value=0
    )

    # Create 2D grids
    if ftle_lons.ndim == 1:
        lon_2d, lat_2d = np.meshgrid(ftle_lons, ftle_lats)
    else:
        lon_2d, lat_2d = ftle_lons, ftle_lats

    # Sample wind at FTLE grid points
    wind_at_ftle = np.zeros_like(lat_2d)
    for i in range(lat_2d.shape[0]):
        for j in range(lat_2d.shape[1]):
            lat_point = lat_2d[i, j]
            lon_point = lon_2d[i, j]
            wind_at_ftle[i, j] = interp((lat_point, lon_point))

    return wind_at_ftle


def calculate_composite_score(ftle_field, jet_speed, jet_optimal=30.0, jet_sigma=5.0):
    """
    Calculate composite score for seeding location selection.

    Parameters:
    -----------
    ftle_field : array (lat, lon)
        FTLE values
    jet_speed : array (lat, lon)
        Jet stream speed in m/s
    jet_optimal : float
        Optimal jet stream speed in m/s
    jet_sigma : float
        Width of Gaussian for jet proximity scoring

    Returns:
    --------
    composite_score : array (lat, lon)
        Combined score (0-1 range, higher is better)
    """

    # Normalize FTLE (0-1 scale, higher is better)
    ftle_normalized = (ftle_field - ftle_field.min()) / (ftle_field.max() - ftle_field.min() + 1e-10)

    # Jet stream proximity score (Gaussian centered at optimal speed)
    jet_score = np.exp(-((jet_speed - jet_optimal) / jet_sigma)**2)

    # Combined score (equal weight)
    composite_score = ftle_normalized * jet_score

    return composite_score


def select_seeding_candidates(ftle_field, ftle_lats, ftle_lons,
                               jet_speed=None, jet_lats=None, jet_lons=None,
                               ftle_percentile=90,
                               jet_range=(25, 40),
                               jet_optimal=30.0,
                               geographic_bounds=None,
                               min_separation_km=300,
                               max_candidates=20):
    """
    Select optimal seeding location candidates.

    Parameters:
    -----------
    ftle_field : array (lat, lon)
        FTLE values
    ftle_lats : array (lat,)
        FTLE latitude coordinates
    ftle_lons : array (lon,)
        FTLE longitude coordinates
    jet_speed : array (lat, lon), optional
        Jet stream speed in m/s (if None, skip jet filtering)
    jet_lats : array (lat,), optional
        Jet stream latitude coordinates
    jet_lons : array (lon,), optional
        Jet stream longitude coordinates
    ftle_percentile : float
        FTLE threshold percentile (e.g., 90 = top 10%)
    jet_range : tuple (min, max)
        Jet stream edge speed range in m/s
    jet_optimal : float
        Optimal jet stream speed for Gaussian weighting
    geographic_bounds : dict, optional
        Geographic constraints: {'lat': (min, max), 'lon': (min, max)}
    min_separation_km : float
        Minimum separation between candidates in km
    max_candidates : int
        Maximum number of candidates to return

    Returns:
    --------
    selected_lats : array
        Selected candidate latitudes
    selected_lons : array
        Selected candidate longitudes
    selected_scores : array
        Composite scores of selected candidates
    """

    print("🔍 Finding optimal seeding points...")

    # Create 2D grids
    if ftle_lons.ndim == 1:
        lon_2d, lat_2d = np.meshgrid(ftle_lons, ftle_lats)
    else:
        lon_2d, lat_2d = ftle_lons, ftle_lats

    # Step 1: FTLE threshold
    ftle_threshold = np.percentile(ftle_field, ftle_percentile)
    print(f"  FTLE threshold ({ftle_percentile}th percentile): {ftle_threshold:.4f}")
    high_ftle_mask = ftle_field >= ftle_threshold

    # Step 2: Jet stream filtering (if provided)
    if jet_speed is not None:
        print(f"  Jet stream edge range: {jet_range[0]}-{jet_range[1]} m/s")

        # Interpolate jet to FTLE grid if needed
        if jet_lats is not None and jet_lons is not None:
            jet_at_ftle = interpolate_wind_to_ftle_grid(
                jet_speed, jet_lats, jet_lons, ftle_lats, ftle_lons
            )
        else:
            jet_at_ftle = jet_speed

        jet_edge_mask = (jet_at_ftle >= jet_range[0]) & (jet_at_ftle <= jet_range[1])
    else:
        jet_at_ftle = None
        jet_edge_mask = np.ones_like(ftle_field, dtype=bool)
        print("  Skipping jet stream filtering (not provided)")

    # Step 3: Geographic filtering
    if geographic_bounds is not None:
        lat_min, lat_max = geographic_bounds['lat']
        lon_min, lon_max = geographic_bounds['lon']
        lat_mask = (lat_2d >= lat_min) & (lat_2d <= lat_max)
        lon_mask = (lon_2d >= lon_min) & (lon_2d <= lon_max)
        geo_mask = lat_mask & lon_mask
        print(f"  Geographic bounds: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}]")
    else:
        geo_mask = np.ones_like(ftle_field, dtype=bool)
        print("  No geographic filtering")

    # Combine all masks
    combined_mask = high_ftle_mask & jet_edge_mask & geo_mask

    # Get coordinates and values
    lons_high = lon_2d[combined_mask]
    lats_high = lat_2d[combined_mask]
    ftle_high = ftle_field[combined_mask]

    print(f"\n  Found {len(lons_high)} candidate points after filtering")

    if len(lons_high) == 0:
        print("  ⚠️  No candidates found! Consider relaxing constraints.")
        return np.array([]), np.array([]), np.array([])

    # Step 4: Calculate composite score
    if jet_at_ftle is not None:
        jet_high = jet_at_ftle[combined_mask]
        composite_score = calculate_composite_score(
            ftle_high, jet_high, jet_optimal=jet_optimal
        )
    else:
        # Use FTLE only
        composite_score = (ftle_high - ftle_high.min()) / (ftle_high.max() - ftle_high.min() + 1e-10)

    print(f"  Composite score range: {composite_score.min():.3f} to {composite_score.max():.3f}")

    # Step 5: Filter by spatial separation
    print(f"\n  Filtering by minimum separation: {min_separation_km} km...")

    # Sort by composite score (descending)
    sorted_indices = np.argsort(-composite_score)

    selected_indices = []
    selected_lats = []
    selected_lons = []
    selected_scores = []

    for idx in sorted_indices:
        lat_candidate = lats_high[idx]
        lon_candidate = lons_high[idx]
        score_candidate = composite_score[idx]

        # Check separation from already selected points
        if len(selected_lats) == 0:
            # First point, automatically select
            too_close = False
        else:
            # Calculate distance to all selected points
            distances = []
            for sel_lat, sel_lon in zip(selected_lats, selected_lons):
                dist = haversine_distance(lat_candidate, lon_candidate, sel_lat, sel_lon)
                distances.append(dist)
            too_close = any(d < min_separation_km for d in distances)

        if not too_close:
            selected_indices.append(idx)
            selected_lats.append(lat_candidate)
            selected_lons.append(lon_candidate)
            selected_scores.append(score_candidate)

            if len(selected_indices) >= max_candidates:
                break

    selected_lats = np.array(selected_lats)
    selected_lons = np.array(selected_lons)
    selected_scores = np.array(selected_scores)

    print(f"\n✅ Selected {len(selected_lats)} candidates with min separation {min_separation_km} km")
    print(f"  Latitude range: {selected_lats.min():.2f}° to {selected_lats.max():.2f}°")
    print(f"  Longitude range: {selected_lons.min():.2f}° to {selected_lons.max():.2f}°")

    return selected_lats, selected_lons, selected_scores


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate great circle distance between two points on Earth.

    Parameters:
    -----------
    lat1, lon1 : float
        First point coordinates (degrees)
    lat2, lon2 : float
        Second point coordinates (degrees)

    Returns:
    --------
    distance : float
        Distance in kilometers
    """

    # Convert to radians
    lat1_rad = np.deg2rad(lat1)
    lat2_rad = np.deg2rad(lat2)
    dlon_rad = np.deg2rad(lon2 - lon1)
    dlat_rad = np.deg2rad(lat2 - lat1)

    # Haversine formula
    a = np.sin(dlat_rad/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon_rad/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    distance_km = 6371.0 * c  # Earth radius

    return distance_km


def create_seeding_locations_from_candidates(candidate_lats, candidate_lons,
                                              selected_indices, radius_km=250):
    """
    Create seeding location dictionaries from candidate points.

    Parameters:
    -----------
    candidate_lats : array
        All candidate latitudes
    candidate_lons : array
        All candidate longitudes
    selected_indices : list
        Indices of candidates to use (1-indexed)
    radius_km : float
        Seeding radius in kilometers

    Returns:
    --------
    seeding_locations : list of dict
        List of seeding location dictionaries with keys:
        - 'lat_center': float
        - 'lon_center': float
        - 'radius_km': float
    """

    seeding_locations = []
    for idx in selected_indices:
        i = idx - 1  # Convert to 0-based index
        if 0 <= i < len(candidate_lats):
            seeding_locations.append({
                'lat_center': float(candidate_lats[i]),
                'lon_center': float(candidate_lons[i]),
                'radius_km': radius_km
            })

    return seeding_locations


def print_seeding_locations(seeding_locations):
    """
    Print seeding locations in a readable format.

    Parameters:
    -----------
    seeding_locations : list of dict
        List of seeding location dictionaries
    """

    print(f"\n✅ Created {len(seeding_locations)} seeding locations:")
    for i, loc in enumerate(seeding_locations, 1):
        print(f"  {i}. Lat: {loc['lat_center']:6.2f}°, "
              f"Lon: {loc['lon_center']:6.2f}°, "
              f"Radius: {loc['radius_km']:.0f} km")


# Event-specific geographic bounds
BOUNDS_PACIFIC_AR = {
    'lat': (10, 55),
    'lon': (120, 240)
}

BOUNDS_ATLANTIC_HURRICANE = {
    'lat': (10, 45),
    'lon': (260, 360)  # -100 to 0 degrees = 260 to 360
}

BOUNDS_NORTH_AMERICA_FREEZE = {
    'lat': (25, 55),
    'lon': (230, 290)  # -130 to -70 degrees = 230 to 290
}

BOUNDS_GLOBAL = {
    'lat': (-60, 60),
    'lon': (0, 360)
}
