# Atmospheric River, Frontal Zone, and Tropical Cyclone Control Analysis

This repository contains code and analysis for understanding and controlling atmospheric phenomena using Lagrangian coherent structures (LCS), finite-time Lyapunov exponents (FTLE), and atmospheric river detection.

## Overview

This project investigates the dynamics of:
- **Atmospheric Rivers (ARs)**: Narrow corridors of concentrated moisture transport
- **Frontal Zones (FZ)**: Boundaries between air masses identified through jet stream analysis
- **Tropical Cyclones (TC)**: Using Lagrangian coherent structures to understand transport barriers

## Key Components

### 1. FTLE Calculation (`ftle_calculation.ipynb`)
Implementation of Finite-Time Lyapunov Exponent calculations to identify Lagrangian Coherent Structures (LCS) in atmospheric flow.

**Features:**
- Based on methodology from Garaboa-Paz et al. (2017) - *Climatology of Lyapunov exponents*
- Lagrangian trajectory integration using 4th-order Runge-Kutta
- Forward and backward FTLE calculation for repelling/attracting structures
- Visualization of filamentary mixing structures
- Configurable integration time and pressure levels (300 hPa, 850 hPa)

**Data Requirements:**
- ERA5 reanalysis: u, v wind components
- Multiple pressure levels (50-1000 hPa)
- 6-hourly temporal resolution

### 2. Atmospheric River Visualization (`AR_visualization.ipynb`)
Detection and visualization of atmospheric rivers using Integrated Vapor Transport (IVT).

**Features:**
- IVT calculation: IVT = (1/g) ∫ q·V dp
- AR detection using 250 kg/(m·s) threshold
- Global animation of IVT evolution
- Combined dataset creation (lon, lat, time, ivt)

### 3. Jet Stream Analysis (`jet_stream_visualization.ipynb`)
Upper-atmospheric wind analysis at 300 hPa level to identify frontal zones.

**Features:**
- Jet stream detection (wind speed > 30 m/s)
- Jet core identification (wind speed > 60 m/s)
- Frequency maps and statistics
- Time evolution animations

### 4. ERA5 Data Download (`data/era5_batch_download.ipynb`)
Automated batch download of ERA5 reanalysis data via CDS API.

**Downloads:**
- Static variables (geopotential, land-sea mask, soil type)
- Surface-level variables (2m temperature, 10m winds, MSLP)
- Atmospheric variables at 13 pressure levels (t, u, v, q, z)

## Methodology

### FTLE Calculation Process
1. **Particle Grid Initialization**: Initialize particles on regular lat-lon grid
2. **Trajectory Integration**: Integrate particle trajectories using wind field interpolation
3. **Flow Map Gradient**: Compute ∇Φ using finite differences
4. **Cauchy-Green Tensor**: Calculate C̃ = (∇Φ)ᵀ · G · (∇Φ) on sphere
5. **FTLE Computation**: λ(τ,t₀,r₀) = (1/|τ|) log√(μₘₐₓ(C̃))

### AR Detection
- Vertical integration of moisture flux from surface to 50 hPa
- IVT threshold: 250 kg/(m·s) for AR identification
- Temporal tracking and frequency analysis

### Jet Stream Analysis
- 300 hPa level optimal for polar and subtropical jets
- Wind speed magnitude: √(u² + v²)
- Identification of transport barriers and frontal zones

## Data Sources

- **ERA5 Reanalysis**: ECMWF atmospheric data
  - Spatial resolution: 0.25° × 0.25°
  - Temporal resolution: 6-hourly
  - Pressure levels: 50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000 hPa

## Usage

### FTLE Calculation
```python
# Set starting time index (e.g., timestep 4 = 2022-12-23 00:00)
START_TIME_IDX = 4

# Integration parameters
tau_days = 3.0  # Integration time (days)
pressure_level = 300  # hPa

# Domain configuration
lon_min, lon_max = 0, 360
lat_min, lat_max = 0, 70
grid_spacing = 0.5  # degrees
```

### AR Visualization
```python
# IVT calculation
ivt_u, ivt_v, ivt_magnitude = calculate_ivt(u_wind, v_wind, q_data, pressure_levels, g=9.81)

# AR detection threshold
AR_THRESHOLD = 250  # kg/(m·s)
```

### Jet Stream Analysis
```python
# Jet parameters
JET_LEVEL = 300  # hPa
JET_THRESHOLD = 30  # m/s (jet stream)
JET_CORE_THRESHOLD = 60  # m/s (jet core)
```

## Requirements

```
numpy
xarray
scipy
matplotlib
cartopy
netCDF4
cdsapi (for data download)
tqdm
```

## References

1. Garaboa-Paz, D., Eiras-Barca, J., & Pérez-Muñuzuri, V. (2017). *Climatology of Lyapunov exponents: the link between atmospheric rivers and large-scale mixing variability*. Earth System Dynamics, 8, 865-873.

2. Haller, G. (2015). *Lagrangian coherent structures*. Annual Review of Fluid Mechanics, 47, 137-162.

3. Guan, B., & Waliser, D. E. (2015). *Detection of atmospheric rivers: Evaluation and application of an algorithm for global studies*. Journal of Geophysical Research: Atmospheres, 120(24), 12514-12535.

## Project Structure

```
.
├── README.md
├── ftle_calculation.ipynb          # FTLE/LCS analysis
├── AR_visualization.ipynb          # Atmospheric river detection
├── jet_stream_visualization.ipynb  # Jet stream analysis
├── data/
│   ├── era5_batch_download.ipynb   # Data download scripts
│   ├── era5_batch/                 # Downloaded ERA5 data
│   ├── ivt_combined.nc             # Processed IVT dataset
│   └── jet_stream_300hPa.nc        # Jet stream dataset
└── Climatology of Lyapunov exponents.pdf  # Reference paper
```

## Author

Moyan Liu

## License

This project is available for academic and research purposes.
