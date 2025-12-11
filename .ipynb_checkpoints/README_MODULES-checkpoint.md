# FTLE-Based Cloud Seeding Perturbation Framework

A modular Python framework for studying targeted weather modification using Finite-Time Lyapunov Exponents (FTLE) and physically-consistent cloud seeding perturbations.

## Overview

This framework combines **dynamical systems theory** (FTLE analysis) with **cloud microphysics** to identify and perturb regions where small initial condition changes can significantly influence extreme weather events.

### Key Capabilities

1. **FTLE Calculation** - Identify regions of high flow sensitivity
2. **Optimal Seeding Location Selection** - Combine FTLE, jet stream, and geography
3. **Physically-Consistent Perturbations** - Cloud seeding via ice nucleation
4. **IVT Analysis** - Track atmospheric rivers and moisture transport
5. **Multi-Event Support** - Atmospheric rivers, hurricanes, freeze events

## Modules

### 1. `ftle_calculation.py`

Calculate FTLE fields from wind data to identify sensitive regions.

```python
from ftle_calculation import calculate_ftle_from_winds

# Calculate forward FTLE
ftle_field, final_positions = calculate_ftle_from_winds(
    u_field, v_field, lat_grid, lon_grid,
    dt_hours=6,
    integration_time_hours=48,
    direction='forward'
)
```

**Key Functions:**
- `calculate_ftle_from_winds()` - Complete FTLE pipeline
- `advect_particles()` - Particle advection
- `calculate_ftle()` - FTLE from final positions
- `crop_region()` - Geographic subsetting

### 2. `seeding_location_selection.py`

Select optimal seeding locations based on FTLE and dynamical criteria.

```python
from seeding_location_selection import select_seeding_candidates, BOUNDS_PACIFIC_AR

# Select candidate locations
selected_lats, selected_lons, scores = select_seeding_candidates(
    ftle_field, ftle_lats, ftle_lons,
    jet_speed=wind_speed,
    ftle_percentile=90,
    jet_range=(25, 40),
    geographic_bounds=BOUNDS_PACIFIC_AR,
    min_separation_km=300,
    max_candidates=20
)

# Create seeding location dictionaries
from seeding_location_selection import create_seeding_locations_from_candidates

seeding_locations = create_seeding_locations_from_candidates(
    selected_lats, selected_lons,
    selected_indices=[1, 5, 10],  # Pick specific candidates
    radius_km=250
)
```

**Key Functions:**
- `select_seeding_candidates()` - Multi-criteria location selection
- `create_seeding_locations_from_candidates()` - Format seeding locations
- `haversine_distance()` - Great circle distance calculation

**Predefined Geographic Bounds:**
- `BOUNDS_PACIFIC_AR` - Pacific atmospheric rivers
- `BOUNDS_ATLANTIC_HURRICANE` - Atlantic hurricanes
- `BOUNDS_NORTH_AMERICA_FREEZE` - North American freeze events
- `BOUNDS_GLOBAL` - Global analysis

### 3. `cloud_seeding_perturbation.py`

Apply physically-consistent cloud seeding perturbations.

```python
from cloud_seeding_perturbation import (
    apply_physically_consistent_cloud_seeding,
    create_seeding_mask,
    print_diagnostics,
    SEEDING_CONFIG_AR
)

# Create spatial mask
seeding_mask = create_seeding_mask(
    seeding_locations,
    batch.metadata.lat,
    batch.metadata.lon
)

# Apply perturbation
delta_T, delta_q, diagnostics = apply_physically_consistent_cloud_seeding(
    batch_seeded,
    seeding_mask,
    SEEDING_CONFIG_AR
)

# Print diagnostics
print_diagnostics(diagnostics, SEEDING_CONFIG_AR)
```

**Key Functions:**
- `apply_physically_consistent_cloud_seeding()` - Main perturbation function
- `create_seeding_mask()` - Create circular seeding regions
- `calculate_q_sat()` - Saturation mixing ratio
- `print_diagnostics()` - Display perturbation statistics

**Predefined Configurations:**
- `SEEDING_CONFIG_AR` - Atmospheric river modification
- `SEEDING_CONFIG_HURRICANE` - Hurricane modification
- `SEEDING_CONFIG_FREEZE` - Freeze event modification

### 4. `ivt_analysis.py`

Calculate and analyze Integrated Vapor Transport for AR detection.

```python
from ivt_analysis import calculate_ivt_integrated, calculate_landfall_trajectory

# Calculate IVT
ivt_u, ivt_v, ivt_magnitude = calculate_ivt_integrated(
    u_data, v_data, q_data,
    pressure_levels,
    p_top=200,
    p_bottom=1000
)

# Track landfall
landfall_control, landfall_seeded = calculate_landfall_trajectory(
    ivt_control, ivt_seeded,
    lats, lons, coastal_lats, coastal_lons,
    ivt_threshold=250
)
```

**Key Functions:**
- `calculate_ivt_integrated()` - IVT from 3D atmospheric fields
- `calculate_ivt_trajectory()` - Time series of IVT
- `find_ar_landfall_location()` - Detect AR landfall
- `calculate_landfall_trajectory()` - Track landfall evolution

## Physical Basis

### FTLE Analysis

The Finite-Time Lyapunov Exponent quantifies flow divergence:

```
FTLE = (1/2T) * ln(λ_max)
```

where `λ_max` is the largest eigenvalue of the Cauchy-Green strain tensor.

**High FTLE regions** indicate:
- Sensitive dependence on initial conditions
- Flow separation and convergence
- Locations where small perturbations amplify rapidly

### Cloud Seeding Physics

**Process:** Ice nucleation via vapor deposition (vapor → ice)

1. **Vapor Freezing:**
   ```
   q_frozen = q_vapor × η_freeze × mask
   ```
   - `η_freeze`: Freeze efficiency (0.6-0.8)

2. **Latent Heat Release:**
   ```
   ΔE = L_d × q_frozen
   ΔT = ΔE / C_p
   ```
   - `L_d = 2.834 MJ/kg` (deposition heat)
   - Results in warming of air column

3. **Moisture Removal:**
   ```
   q_new = q_old - q_frozen
   ```
   - Reduced humidity for downstream convection

4. **Thermodynamic Consistency:**
   - Recalculates saturation mixing ratio
   - Validates relative humidity bounds
   - Ensures physical states

### IVT for AR Detection

Integrated Vapor Transport:

```
IVT = (1/g) ∫ q·V dp
```

- Integrated from 200-1000 hPa
- Units: kg/(m·s)
- AR threshold: 250-300 kg/(m·s)

## Usage Example: Atmospheric River Divergence

```python
import torch
import numpy as np
from ftle_calculation import calculate_ftle_from_winds
from seeding_location_selection import select_seeding_candidates, BOUNDS_PACIFIC_AR
from cloud_seeding_perturbation import (
    create_seeding_mask,
    apply_physically_consistent_cloud_seeding,
    SEEDING_CONFIG_AR
)
from ivt_analysis import calculate_ivt_trajectory, calculate_landfall_trajectory

# Step 1: Load atmospheric data (u, v at jet level)
u_jet = batch.atmos_vars["u"][0, 1, jet_level_idx].cpu().numpy()
v_jet = batch.atmos_vars["v"][0, 1, jet_level_idx].cpu().numpy()
lats = batch.metadata.lat.cpu().numpy()
lons = batch.metadata.lon.cpu().numpy()

# Step 2: Calculate FTLE
ftle_field, _ = calculate_ftle_from_winds(
    u_jet, v_jet, lats, lons,
    integration_time_hours=48,
    direction='forward'
)

# Step 3: Select seeding locations
wind_speed = np.sqrt(u_jet**2 + v_jet**2)
selected_lats, selected_lons, _ = select_seeding_candidates(
    ftle_field, lats, lons,
    jet_speed=wind_speed,
    geographic_bounds=BOUNDS_PACIFIC_AR,
    max_candidates=5
)

# Create seeding locations
seeding_locations = [
    {'lat_center': lat, 'lon_center': lon, 'radius_km': 250}
    for lat, lon in zip(selected_lats, selected_lons)
]

# Step 4: Apply cloud seeding perturbation
batch_control = batch  # Original
batch_seeded = clone_batch(batch)  # Clone for modification

seeding_mask = create_seeding_mask(seeding_locations, lats, lons)
delta_T, delta_q, diagnostics = apply_physically_consistent_cloud_seeding(
    batch_seeded, seeding_mask, SEEDING_CONFIG_AR
)

# Step 5: Run Aurora forecast
preds_control = model.forward(batch_control, steps=20)
preds_seeded = model.forward(batch_seeded, steps=20)

# Step 6: Calculate IVT and track AR
ivt_control = calculate_ivt_trajectory(preds_control, pressure_levels)
ivt_seeded = calculate_ivt_trajectory(preds_seeded, pressure_levels)

# Step 7: Analyze landfall divergence
coastal_lats, coastal_lons = create_coastline_profile(
    lat_range=(30, 50), coastline_lon=235
)
landfall_ctrl, landfall_seed = calculate_landfall_trajectory(
    ivt_control, ivt_seeded,
    lats, lons, coastal_lats, coastal_lons
)

# Step 8: Quantify divergence
for i, (lf_c, lf_s) in enumerate(zip(landfall_ctrl, landfall_seed)):
    if lf_c['found'] and lf_s['found']:
        lat_shift = lf_s['lat'] - lf_c['lat']
        print(f"Hour +{lf_c['hours']:3d}: Landfall shift = {lat_shift:+.2f}° lat")
```

## Adapting to Other Extreme Events

### Hurricane Modification

**Goal:** Reduce intensity or alter track

**Strategy:**
1. **FTLE at upper levels** (500-300 hPa) to identify steering flow sensitivities
2. **Seeding in eyewall region** to disrupt convective organization
3. **Mid-level seeding** (700-500 hPa) to increase dry air intrusion

```python
from cloud_seeding_perturbation import SEEDING_CONFIG_HURRICANE
from seeding_location_selection import BOUNDS_ATLANTIC_HURRICANE

# Use higher levels for hurricane steering
ftle_field, _ = calculate_ftle_from_winds(
    u_500hPa, v_500hPa, lats, lons,
    integration_time_hours=24,  # Shorter for faster-moving hurricanes
    direction='forward'
)

# Apply hurricane-specific seeding
delta_T, delta_q, _ = apply_physically_consistent_cloud_seeding(
    batch_seeded, seeding_mask, SEEDING_CONFIG_HURRICANE
)
```

**Key Differences:**
- **Vertical coupling enabled** - Convective processes are crucial
- **Lower freeze efficiency** (0.6) - Warmer tropical environment
- **Mid-level focus** (925-700 hPa) - Target moisture source
- **Shorter integration time** - Faster event evolution

### Freeze Event Prevention

**Goal:** Prevent damaging cold air intrusion

**Strategy:**
1. **FTLE at mid-levels** (700-500 hPa) where cold air advection occurs
2. **Seeding upstream** of cold front to enhance warming
3. **High fallout fraction** to maximize latent heat release

```python
from cloud_seeding_perturbation import SEEDING_CONFIG_FREEZE
from seeding_location_selection import BOUNDS_NORTH_AMERICA_FREEZE

# Focus on mid-upper levels for cold air mass
ftle_field, _ = calculate_ftle_from_winds(
    u_600hPa, v_600hPa, lats, lons,
    integration_time_hours=36,
    direction='backward'  # Identify upstream influence
)

# Apply freeze-prevention seeding
delta_T, delta_q, _ = apply_physically_consistent_cloud_seeding(
    batch_seeded, seeding_mask, SEEDING_CONFIG_FREEZE
)
```

**Key Differences:**
- **Backward FTLE** - Identify upstream sources of cold air
- **High freeze efficiency** (0.8) - Maximize warming
- **Mid-upper levels** (700-500 hPa) - Target cold air mass
- **No vertical coupling** - Focus energy at specific levels

## Configuration Parameters

### Seeding Parameters

| Parameter | AR | Hurricane | Freeze | Description |
|-----------|----|-----------|----|-------------|
| `layers_mb` | [850, 700, 600, 500] | [925, 850, 700] | [700, 600, 500] | Pressure levels (hPa) |
| `freeze_efficiency` | 0.70 | 0.60 | 0.80 | Fraction of vapor frozen |
| `fallout_fraction` | 0.90 | 0.80 | 0.95 | Fraction precipitated out |
| `max_removal_fraction` | 0.60 | 0.50 | 0.70 | Max vapor removal cap |
| `vertical_coupling` | False | True | False | Couple adjacent levels |
| `coupling_factor` | 0.3 | 0.4 | 0.2 | Coupling strength |

### FTLE Parameters

| Parameter | AR | Hurricane | Freeze | Description |
|-----------|----|-----------|----|-------------|
| `integration_time_hours` | 48 | 24 | 36 | Integration period |
| `direction` | forward | forward | backward | Advection direction |
| `dt_hours` | 6 | 6 | 6 | Time step |
| `pressure_level` | 250 hPa (jet) | 500 hPa (steering) | 600 hPa (cold air) | Analysis level |

### Location Selection

| Parameter | AR | Hurricane | Freeze | Description |
|-----------|----|-----------|----|-------------|
| `ftle_percentile` | 90 | 85 | 90 | FTLE threshold |
| `jet_range` | (25, 40 m/s) | N/A | N/A | Jet edge speed |
| `min_separation_km` | 300 | 200 | 400 | Spacing between sites |
| `radius_km` | 250 | 150 | 300 | Seeding radius |

## Expected Physical Effects

### Atmospheric Rivers
- **Temperature:** +0.5 to +2 K warming in seeded regions
- **Humidity:** -10% to -60% reduction
- **IVT:** -50 to -150 kg/(m·s) reduction
- **Landfall:** 1-5° latitude shift (100-500 km)

### Hurricanes
- **Temperature:** +0.3 to +1 K warming
- **Humidity:** -5% to -30% reduction in eyewall
- **Intensity:** Potential 5-15% reduction in max winds
- **Track:** 0.5-2° deviation (50-200 km)

### Freeze Events
- **Temperature:** +1 to +3 K warming
- **Humidity:** -20% to -70% reduction
- **Cold air mass:** 1-3 K temperature increase downstream
- **Duration:** Potential 6-12 hour reduction in freeze duration

## References

- Haller, G. (2015). Lagrangian Coherent Structures. *Annual Review of Fluid Mechanics*.
- Ralph, F. M., et al. (2018). Atmospheric Rivers. *Nature Reviews Earth & Environment*.
- Rosenfeld, D., et al. (2020). Cloud Seeding. *Annual Review of Meteorology*.

## Authors

Adapted from perturbation_trail_111.ipynb by Moyan Liu
Modularized by: Qiyu Huang
Date: 2025-12-02

## License

Research use only. See LICENSE file for details.
