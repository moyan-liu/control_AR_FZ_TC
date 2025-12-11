# Hurricane Ian 2022 - FTLE Perturbation Test

**Tropical cyclone track modification via FTLE-guided cloud seeding**

Adapted from Hurricane Sandy 2012 successful methodology.

---

## Event Overview

- **Storm**: Hurricane Ian (2022)
- **Basin**: Gulf of Mexico / Caribbean / Atlantic
- **Initialization**: September 25, 2022 18:00 UTC (3-day lead time)
- **Target**: Florida landfall ~September 28, 2022
- **Initial Position**: 15.80°N, 279.90°E (-80.10°W)

---

## Quick Start

### 1. Run FTLE Perturbation Test (3-day lead)

```bash
cd /scratch/qhuang62/control_AR_FZ_TC/Ian_2022_perturb
python ian_ftle_perturbation_test.py
```

**Runtime**: ~2-3 hours on GPU (11 timesteps, 3-day forecast)

**⚠️ Result**: 3-day lead showed minimal effect (max 27.8 km deviation at 24h, converged to 0 km by 48h)

### 1b. Run Extended 5-Day Lead Test

```bash
python ian_ftle_perturbation_test_5day.py
```

**Runtime**: ~3-4 hours on GPU (19 timesteps, 5-day forecast)

**Outputs**:
- `ian_ftle_test_output/preds_baseline.pt` - Baseline forecast
- `ian_ftle_test_output/preds_seeded.pt` - Perturbed forecast
- `ian_ftle_test_output/ian_ftle_track_comparison.png` - Track comparison
- `ian_ftle_test_output/seeding_locations_map.png` - FTLE field + seeding sites

### 2. Analyze Atmospheric Fields

```bash
python analyze_ian_perturbation_fields.py
```

**Runtime**: ~10-15 minutes (55 field plots)

**Outputs**:
- `ian_ftle_test_output/field_analysis/msl_t*.png` - MSL pressure evolution
- `ian_ftle_test_output/field_analysis/z500_t*.png` - 500 hPa height evolution
- `ian_ftle_test_output/field_analysis/t700_t*.png` - 700 hPa temperature evolution
- `ian_ftle_test_output/field_analysis/rh850_t*.png` - 850 hPa humidity evolution
- `ian_ftle_test_output/field_analysis/wind300_t*.png` - 300 hPa wind evolution
- `ian_ftle_test_output/field_analysis/field_differences_timeseries.png` - Summary

---

## Key Configuration Differences from Sandy

| Parameter | Sandy 2012 | Ian 2022 | Notes |
|-----------|------------|----------|-------|
| **Initialization** | Oct 23, 2012 00:00 UTC | Sep 25, 2022 18:00 UTC | Different synoptic hour |
| **Lead Time** | 7 days | 3 days | Shorter for Ian |
| **Forecast Steps** | 28 (168 hours) | 11 (66 hours) | 3 vs 7 days |
| **Basin** | Atlantic | Gulf/Caribbean | Different dynamics |
| **Geographic Bounds** | (0°-35°N, 260°-300°E) | (10°-35°N, 270°-300°E) | Gulf-focused |
| **Map Extent** | [260, 300, 0, 50] | [270, 300, 10, 35] | Matches prediction study |

**Unchanged**:
- FTLE integration time: 48 hours
- Seeding levels: 700, 500, 300 hPa
- Seeding efficiency: 60%
- Distance filter: 500-1500 km from TC

---

## Data Requirements

**ERA5 Data**: `/scratch/qhuang62/aurora-extreme-predictability/research/TC/data/era5_ian_2022/`

**Required Files**:
- `ian_2022_surface_combined.nc` - Surface variables (Sep 21-28, 2022)
- `ian_2022_atmospheric_combined.nc` - Atmospheric variables (Sep 21-28, 2022)
- Static fields (lsm, z_surf) from single-day file

**Alternative**: Single-day files for Sep 25, 2022 (if combined files not available)

---

## Analysis Features

### Field Analysis Script Improvements

1. **Global Min/Max Scaling**: Difference plots use consistent color scales across all timesteps
   - Enables creation of smooth GIF animations
   - Prevents misleading color jumps between frames

2. **Updated Map Extent**: Uses Ian prediction study extent `[270, 300, 10, 35]`
   - Matches existing visualization standards
   - Focuses on Gulf/Caribbean/Florida region

3. **Two-Pass Algorithm**:
   - **Pass 1**: Scan all timesteps to find global min/max differences
   - **Pass 2**: Plot all timesteps with fixed scales

---

## Results Summary

### 3-Day Lead Test (Sep 25 18:00 UTC) ❌

**Initialization**: 15.80°N, 279.90°E
**Perturbation sites**: 4 locations (1440-1495 km from TC)
**Result**: **Minimal effect**
- 24hr deviation: 27.8 km
- 48hr deviation: 0.0 km
- Final deviation: 0.0 km

**Analysis**: Insufficient propagation time, sites may be too far from TC

### 5-Day Lead Test (Sep 23 18:00 UTC) 🔄

**Script created**: `ian_ftle_perturbation_test_5day.py`
**Initialization**: 14.60°N, 289.40°E
**Forecast**: 19 steps (114 hours)
**Status**: Ready to run

---

## Expected Results (Original Targets)

### Success Criteria

- ✅ **Minimum success**: Track deviation > 50 km at 48 hours
- ✅ **Strong success**: Final track deviation > 100 km
- ✅ **Thermodynamic validity**: No NaN values, RH bounds respected

### Comparison with Sandy

Sandy achieved **321.6 km** final deviation with:
- 7-day forecast
- 3 perturbation sites
- Atlantic basin dynamics

Ian test will reveal whether:
- **3-day lead** provides sufficient propagation time
- **Gulf dynamics** respond similarly to Atlantic
- **Same methodology** generalizes to different TC basins

---

## Known Limitations

### 3-Day Lead Time ✅ CONFIRMED ISSUE

**Issue**: 3-day lead time insufficient for perturbation propagation.

**Evidence from test run**:
- Selected 4 perturbation sites at 1440-1495 km from TC
- Max deviation only 27.8 km at 24 hours
- Deviation converged back to 0 km by 48 hours
- Perturbation effects dissipated before influencing steering flow

**Mitigation**: ✅ Created 5-day lead test script
- Initialize Sep 23 18:00 UTC (2 days earlier)
- 19-step forecast (114 hours)
- More time for environmental modifications to develop
- If 5-day fails, try 7-day lead (like Sandy)

### Perturbation Site Selection

**Note**: Sandy's success depended on fortunate site selection. Ian's FTLE field may identify sites that don't effectively modify the track.

**If sites don't work**:
- Adjust FTLE percentile threshold (try 80% or 90%)
- Modify distance filter range
- Try different seeding radii (200 km or 400 km)
- Test multiple site configurations

---

## Physical Interpretation

### Key Variables to Monitor

1. **MSL Pressure**: Look for pressure anomalies at seeding sites
   - Expected: -0.5 to -2 hPa (heating → lower pressure)

2. **500 hPa Height**: Steering flow modification
   - Expected: +10 to +30 m at seeding sites (warming → higher geopotential)
   - Downstream: Rossby wave response

3. **700 hPa Temperature**: Direct heating signature
   - Expected: +0.5 to +2 K at seeding sites
   - Duration: 12-24 hours (advects away)

4. **850 hPa Humidity**: Drying signature
   - Expected: -10% to -40% at seeding sites
   - Duration: 6-12 hours (moisture recharges)

5. **300 hPa Wind**: Jet stream changes
   - Expected: ±2-5 m/s (upper-level steering modification)

---

## File Structure

```
Ian_2022_perturb/
├── README.md                                   # This file
├── ian_ftle_perturbation_test.py              # 3-day lead test (COMPLETED)
├── ian_ftle_perturbation_test_5day.py         # 5-day lead test (NEW)
├── analyze_ian_perturbation_fields.py         # Field analysis
├── ian_ftle_test_output/                      # 3-day test outputs
│   ├── preds_baseline.pt
│   ├── preds_seeded.pt
│   ├── ian_ftle_track_comparison.png
│   ├── seeding_locations_map.png
│   └── field_analysis/
│       ├── msl_t*.png, z500_t*.png, etc.
│       └── field_differences_timeseries.png
└── ian_ftle_test_output_5day/                 # 5-day test outputs (when run)
    ├── preds_baseline.pt
    ├── preds_seeded.pt
    ├── ian_ftle_track_comparison_5day.png
    └── seeding_locations_map_5day.png
```

---

## Next Steps After Ian

1. **Typhoon Hinnamnor 2022**:
   - Basin: Western Pacific (different from Atlantic/Gulf)
   - 3-day lead: Sep 3 18:00 UTC
   - Tests methodology in different ocean basin

2. **Cyclone Amphan 2020**:
   - Basin: Bay of Bengal
   - 5-day lead: May 15 12:00 UTC
   - In-sample validation (2020 in Aurora training)

3. **Cross-TC Comparison**:
   - Identify common FTLE-perturbation mechanisms
   - Compare basin-specific responses
   - Assess generalizability of methodology

---

## References

- **Sandy Pipeline**: `/scratch/qhuang62/control_AR_FZ_TC/README_PIPELINE.md`
- **Module Documentation**: `/scratch/qhuang62/control_AR_FZ_TC/README_MODULES.md`
- **Ian Prediction Study**: `/scratch/qhuang62/aurora-extreme-predictability/research/TC/2022_Ian/`
- **IBTrACS Data**: https://www.ncdc.noaa.gov/ibtracs/

---

**Created**: December 4, 2025
**Author**: Qiyu Huang
**Adapted from**: Sandy 2012 FTLE perturbation test
