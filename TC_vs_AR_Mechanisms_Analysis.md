# Tropical Cyclone vs Atmospheric River: Mechanisms & Perturbation Strategy

## Analysis Date: 2025-12-02

---

## Executive Summary

This document analyzes the fundamental differences and similarities between Tropical Cyclones (TCs) and Atmospheric Rivers (ARs), and proposes an adapted perturbation strategy for Hurricane Sandy that leverages Moyan Liu's FTLE + cloud seeding methodology.

**Key Finding:** TCs and ARs share similar sensitivity to **diabatic heating** and **moisture availability**, but differ fundamentally in **energy source**, **spatial scale**, and **steering mechanisms**. Moyan's approach can be adapted with modifications to pressure levels, seeding locations, and temporal scales.

---

## Part 1: TC vs AR Mechanisms Comparison

### 1.1 Energy Source & Thermodynamics

| Aspect | **Tropical Cyclone** | **Atmospheric River** |
|--------|---------------------|----------------------|
| **Primary Energy** | Latent heat from ocean surface evaporation | Latent heat from condensation/precipitation |
| **Heat Source** | Warm ocean (SST > 26.5°C) | Mid-latitude baroclinic zones |
| **Vertical Structure** | Deep convective tower (surface to tropopause) | Shallow-to-mid troposphere (850-700 hPa) |
| **Energy Conversion** | WISHE (Wind-Induced Surface Heat Exchange) | Slantwise convection + frontogenesis |
| **Temperature Anomaly** | Warm core (10-15 K above environment) | Warm anomaly in lower troposphere (2-5 K) |

**Common Ground:**
- **Both driven by latent heat release** from water vapor condensation
- **Both enhanced by moisture availability** (high specific humidity)
- **Both sensitive to diabatic heating** perturbations

**Key Difference:**
- **TCs** are self-sustaining heat engines (positive feedback loop)
- **ARs** are transient features embedded in synoptic flow (no self-amplification)

---

### 1.2 Spatial & Temporal Scales

| Aspect | **Tropical Cyclone** | **Atmospheric River** |
|--------|---------------------|----------------------|
| **Horizontal Scale** | 200-500 km (eyewall: 20-80 km) | 250-500 km width × 2000+ km length |
| **Vertical Extent** | Surface to 15-18 km (tropopause) | 1-4 km (850-700 hPa dominant) |
| **Lifetime** | 3-14 days | 1-5 days |
| **Motion Speed** | 5-8 m/s (10-15 kt) | 10-20 m/s (20-40 kt) |
| **Aspect Ratio** | Circular/symmetric | Elongated filament |

**Common Ground:**
- **Similar width scales** (~300-500 km)
- **Multi-day persistence** allows forecast lead time
- **Mesoscale to synoptic-scale phenomena**

**Key Difference:**
- **TCs** are compact and quasi-symmetric
- **ARs** are elongated and embedded in larger-scale flow

---

### 1.3 Steering Mechanisms

| Aspect | **Tropical Cyclone** | **Atmospheric River** |
|--------|---------------------|----------------------|
| **Primary Steering** | Environmental flow (500-700 hPa) | Jet stream position/strength (250-300 hPa) |
| **Beta Drift** | Yes (poleward and westward) | No (passive advection) |
| **Self-Steering** | Asymmetric convection affects motion | None (moves with flow) |
| **Key Control** | Upper-level ridges/troughs | Jet stream configuration |
| **Blocking Sensitivity** | High (can stall or recurve) | High (meridional flow enhancement) |

**Common Ground:**
- **Both highly sensitive to upper-level flow patterns**
- **Both affected by blocking patterns** (e.g., Rex blocks, omega blocks)
- **Both show nonlinear trajectory changes** with small perturbations

**Key Difference:**
- **TCs** have internal dynamics that modify steering flow
- **ARs** are purely passive tracers of large-scale flow

---

### 1.4 Moisture Transport & IVT

| Aspect | **Tropical Cyclone** | **Atmospheric River** |
|--------|---------------------|----------------------|
| **IVT Magnitude** | 500-1500 kg/(m·s) in rainbands | 250-1000 kg/(m·s) in AR core |
| **Moisture Source** | Local ocean evaporation | Remote tropical/subtropical moisture |
| **Vertical Profile** | Deep (925-500 hPa) | Shallow (925-700 hPa) |
| **IVT Convergence** | Symmetric eyewall + spiral bands | Elongated frontal zone |
| **Precipitation Efficiency** | High (40-60%) | Moderate (30-50%) |

**Common Ground:**
- **Both produce extreme precipitation** (>200 mm/day)
- **Both tracked via IVT** (standard metric)
- **Both sensitive to moisture availability**

**Key Difference:**
- **TCs** recycle moisture locally (closed circulation)
- **ARs** transport moisture long distances (open channel)

---

### 1.5 Sensitivity to Perturbations

| Aspect | **Tropical Cyclone** | **Atmospheric River** |
|--------|---------------------|----------------------|
| **Track Sensitivity** | **HIGH** - chaotic after 3-5 days | **MODERATE** - follows steering flow |
| **Intensity Sensitivity** | **VERY HIGH** - rapid intensification | **LOW** - constrained by synoptic pattern |
| **Perturbation Amplification** | **Rapid** (12-24 hrs) | **Gradual** (24-48 hrs) |
| **Optimal Perturbation Location** | Eyewall/inner core | Upstream moisture source |
| **FTLE Applicability** | **Excellent** (steering flow sensitivities) | **Excellent** (jet stream sensitivities) |

**Common Ground:**
- **Both show sensitive dependence on initial conditions**
- **Both amplify small heating perturbations through diabatic processes**
- **Both benefit from FTLE-guided targeting**

**Key Difference:**
- **TCs** amplify perturbations through internal feedback loops
- **ARs** transmit perturbations through advection (no local amplification)

---

## Part 2: Your Previous TC Perturbation Approach

### 2.1 Summary of Existing Method (from TC_Perturbation_Analysis.md)

**Method:** Gaussian temperature perturbations representing diabatic heating uncertainty

**Configuration:**
- **Temperature increase:** δT = 2.49 K (from L_v × δq / c_p)
- **Spatial scale:** σ = 8.0° (~1600 km diameter)
- **Vertical levels:** 700-925 hPa (mid-to-lower troposphere)
- **Grid:** 5×5 array (25 locations) from 30-50°N, 140-250°E
- **Application:** Applied at all timesteps (continuous forcing)

**Key Results:**
- **Track deviations:** Up to 500+ km over 7 days
- **Upstream sensitivity:** Western Pacific perturbations had strongest impact
- **Nonlinear response:** >3× perturbation strength showed saturation
- **Aurora limitation:** Base forecast didn't capture Sandy's westward turn

**Strengths:**
- ✅ Physically-based heating (latent heat from condensation)
- ✅ Systematic spatial coverage
- ✅ Continuous forcing simulates ongoing convection

**Weaknesses:**
- ❌ Very large spatial scale (8° = 880 km) - exceeds TC scale
- ❌ No moisture removal (only heating)
- ❌ Not targeted to FTLE-identified sensitive regions
- ❌ No distinction between different TC regions (eyewall vs environment)

---

## Part 3: Moyan Liu's AR Perturbation Approach

### 3.1 Summary of Moyan's Method

**Method:** Cloud seeding via ice nucleation (vapor deposition)

**Configuration:**
- **FTLE-guided targeting:** 90th percentile FTLE + jet stream edge (25-40 m/s)
- **Spatial scale:** 250 km radius circular regions (4-5 locations)
- **Pressure levels:** 850, 700, 600, 500 hPa
- **Physical process:**
  - Vapor freezing: q_frozen = q × 0.70 × mask
  - Latent heat release: ΔT = L_d × q_frozen / c_p (L_d = 2.834 MJ/kg)
  - Moisture removal: Δq = -q_frozen (90% precipitates out)
- **Thermodynamic consistency:** Validates RH, T bounds, q_sat recalculation

**Key Results:**
- **IVT reduction:** 50-150 kg/(m·s) in AR core
- **Landfall shift:** 1-5° latitude (100-500 km)
- **Teleconnection:** Pacific perturbations → Atlantic IVT changes (2-3 days later)
- **Mechanism:** Modified jet stream → downstream Rossby wave train

**Strengths:**
- ✅ FTLE-targeted (optimal leverage points)
- ✅ Physically realistic (both heating + drying)
- ✅ Appropriate scale (~250 km)
- ✅ Thermodynamically consistent

---

## Part 4: TC vs AR - What's the Same, What's Different?

### 4.1 Similarities (Adaptable Components)

1. **Diabatic Heating Sensitivity**
   - Both TCs and ARs are driven by latent heat release
   - Perturbations to heating → changes in pressure/winds → altered track/intensity
   - **Adaptable:** Cloud seeding heating formula applies to both

2. **FTLE Applicability**
   - TCs: FTLE identifies steering flow sensitivities (where to perturb environment)
   - ARs: FTLE identifies jet stream sensitivities (where to perturb moisture transport)
   - **Adaptable:** FTLE calculation method identical

3. **Moisture-Heating Coupling**
   - TCs: Eyewall moisture → convection → latent heat → intensification
   - ARs: Jet-level moisture → condensation → latent heat → IVT enhancement
   - **Adaptable:** Moisture removal + heating perturbation physics

4. **Teleconnections**
   - Both systems influenced by remote atmospheric patterns
   - Moyan's observation: Pacific perturbations → Atlantic IVT changes (via mid-latitude circulations)
   - TCs also respond to Rossby wave trains triggered by upstream heating
   - **Adaptable:** Expect delayed downstream effects (24-72 hrs)

---

### 4.2 Differences (Modifications Needed)

1. **Spatial Scale**
   - **ARs:** 250 km radius appropriate (matches AR width)
   - **TCs:** Need smaller scale for eyewall (~50-100 km) OR larger for environment (~300-400 km)
   - **Adaptation:** Use **two-zone approach**:
     - **Inner zone** (100 km radius): Target eyewall/inner core
     - **Outer zone** (300 km radius): Target environmental flow

2. **Vertical Structure**
   - **ARs:** Shallow (850-500 hPa focus)
   - **TCs:** Deep (925-300 hPa required)
   - **Adaptation:** Extend pressure levels to 925, 850, 700, 500, 300 hPa
     - Lower levels (925-700 hPa): Modify moisture supply
     - Upper levels (500-300 hPa): Modify steering flow

3. **Perturbation Location Strategy**
   - **ARs:** Upstream of AR (Pacific for West Coast landfall)
   - **TCs:** **Multiple zones**:
     - **Zone A:** Eyewall region (modify intensity)
     - **Zone B:** Upstream environment (modify steering)
     - **Zone C:** Downstream blocking region (modify recurvature)
   - **Adaptation:** Use FTLE to identify all three zones

4. **Temporal Scale**
   - **ARs:** Effects visible in 24-48 hrs (advection timescale)
   - **TCs:** Effects visible in 12-24 hrs for intensity, 24-48 hrs for track (faster internal response)
   - **Adaptation:** Expect faster response, analyze 6-hr outputs

5. **Feedback Loops**
   - **ARs:** No positive feedback (perturbation passively advects)
   - **TCs:** Strong positive feedback (WISHE, convective instability)
   - **Adaptation:** Expect **nonlinear amplification** - smaller perturbations may suffice

---

## Part 5: Adapted Perturbation Strategy for Hurricane Sandy

### 5.1 Why Moyan's Approach is Superior to Your Previous Method

| Aspect | **Previous Method** | **Moyan's Method** | **Why Moyan Wins** |
|--------|---------------------|-------------------|-------------------|
| **Targeting** | Grid-based (25 locations) | FTLE-guided (4-5 optimal) | More efficient, higher signal-to-noise |
| **Physical Realism** | Heating only | Heating + drying | Matches actual cloud physics |
| **Spatial Scale** | 8° (~880 km) | 250 km | Matches TC/AR scales |
| **Thermodynamics** | No consistency checks | Full validation | Prevents unphysical states |
| **Pressure Levels** | 700-925 hPa | 850-500 hPa | Better vertical coverage |

**Verdict:** Moyan's approach is more physically realistic, computationally efficient, and scientifically rigorous.

---

### 5.2 Recommended Adaptations for TCs

#### **Modification 1: Dual-Scale Perturbation**

**Inner Core Perturbation (Intensity Modification):**
- **Radius:** 100 km
- **Pressure levels:** 925, 850, 700 hPa (deep convection)
- **Freeze efficiency:** 0.80 (high efficiency in TC eyewall)
- **Fallout fraction:** 0.95 (rapid precipitation)
- **Goal:** Disrupt eyewall organization, reduce intensity

**Environmental Perturbation (Track Modification):**
- **Radius:** 300 km
- **Pressure levels:** 700, 500, 300 hPa (steering level)
- **Freeze efficiency:** 0.60 (moderate efficiency in environment)
- **Fallout fraction:** 0.80
- **Goal:** Modify steering flow, alter track

#### **Modification 2: FTLE-Based Location Selection**

**Step 1:** Calculate FTLE at multiple levels
- **500 hPa:** Identifies steering flow sensitivities
- **700 hPa:** Identifies mid-level convective zones
- **850 hPa:** Identifies moisture convergence zones

**Step 2:** Select perturbation locations using composite criteria
- **High FTLE (>90th percentile):** Flow sensitivity
- **Upstream of TC (west/southwest):** 500-1500 km ahead
- **Near jet stream:** If applicable (for recurving TCs like Sandy)
- **Avoid eyewall initially:** Test environmental perturbations first

**Step 3:** Spatial separation
- Minimum 400 km between sites (TC scale > AR scale)

#### **Modification 3: Pressure Level Strategy**

| **Level** | **Purpose** | **Process** | **Parameters** |
|-----------|-------------|-------------|----------------|
| **925 hPa** | Moisture source | High drying (80% removal) | freeze_eff=0.70, fallout=0.90 |
| **850 hPa** | Boundary layer | Moderate drying (60% removal) | freeze_eff=0.60, fallout=0.80 |
| **700 hPa** | Mid-level convection | Balanced heating+drying | freeze_eff=0.50, fallout=0.75 |
| **500 hPa** | Upper convection | Light drying (40% removal) | freeze_eff=0.40, fallout=0.70 |
| **300 hPa** | Outflow/steering | Heating only (modify flow) | freeze_eff=0.20, fallout=0.50 |

---

## Part 6: Quick Test Plan for Sandy 2012

### 6.1 Data Availability Assessment

**Available Data:**
✅ `/scratch/qhuang62/aurora/TC/2012-10-24-atmospheric.nc` (559 MB)
✅ `/scratch/qhuang62/aurora/TC/2012-10-24-surface-level.nc` (27 MB)
✅ `/scratch/qhuang62/aurora/TC/static.nc` (3.4 MB)
✅ Complete daily files: Oct 22-31, 2012 in `/scratch/qhuang62/aurora-extreme-predictability/research/TC/data/era5_sandy_2012/`

**Initialization:**
- **Date:** 2012-10-24, 00:00 UTC
- **Sandy position:** 16.6°N, 76.9°W (283.1°E)
- **Sandy intensity:** Tropical Storm → Hurricane
- **Lead time:** 5-6 days to landfall (Oct 29-30)

---

### 6.2 Test Design

#### **Baseline Run (Control)**
- **Purpose:** Establish unperturbed forecast
- **Init:** Oct 24, 00:00 UTC
- **Steps:** 28 (7 days × 4 timesteps/day)
- **Tracker:** Standard Aurora `Tracker`
- **Expected:** Track ending ~37°N, 38°W (offshore, as your previous runs showed)

#### **Test 1: Environmental FTLE-Guided Perturbation**
- **Approach:** Moyan's method adapted for TC steering
- **FTLE calculation:**
  - Use 500 hPa winds (steering level)
  - Forward integration, 48 hrs
  - Crop to Atlantic basin: 10-50°N, 260-320°E
- **Location selection:**
  - Top 3-5 FTLE maxima
  - Upstream of Sandy (west/southwest, 500-1000 km)
  - Filter: Avoid land, minimum 400 km separation
- **Perturbation config:**
  ```python
  SEEDING_CONFIG_SANDY_ENV = {
      'layers_mb': [700, 500, 300],  # Steering levels
      'freeze_efficiency': 0.60,
      'fallout_fraction': 0.80,
      'max_removal_fraction': 0.50,
      'vertical_coupling': False,
      'radius_km': 300
  }
  ```

#### **Test 2: Multi-Zone Strategy** (if Test 1 shows promise)
- **Zone A:** Eyewall (100 km radius, 925-700 hPa, high efficiency)
- **Zone B:** Environment (300 km radius, 700-300 hPa, moderate efficiency)
- **Goal:** Test combined intensity + track modification

#### **Test 3: Temporal Sensitivity** (if time permits)
- Apply perturbations at different times:
  - **t=0 only** (initial condition uncertainty)
  - **t=0-24h** (early evolution)
  - **t=24-48h** (mid-range)
- Compare propagation timescales

---

### 6.3 Expected Outcomes & Metrics

#### **Track Metrics:**
1. **Deviation from control:** Distance (km) at 24, 48, 72, 120 hrs
2. **Landfall location shift:** Change in landfall latitude/longitude
3. **Track timing:** Change in landfall time (hours)

#### **Intensity Metrics:**
1. **MSL minimum:** Change in central pressure (hPa)
2. **10m wind maximum:** Change in maximum sustained winds (m/s)
3. **Rapid intensification:** Change in 24-hr pressure drop

#### **Physical Metrics:**
1. **IVT changes:** Modification to moisture transport
2. **Temperature anomaly persistence:** How long does heating last?
3. **Downstream teleconnections:** Changes >1000 km from perturbation site

---

### 6.4 Implementation Steps

**Step 1: Run Baseline (2 hours)**
```bash
cd /scratch/qhuang62/aurora-extreme-predictability/research/TC/2012_Sandy/
python sandy_stage1_lead_day.py  # Use 5-day lead (Oct 25 init) from existing code
```

**Step 2: Calculate FTLE (30 min)**
```python
# Use ftle_calculation.py module
from ftle_calculation import calculate_ftle_from_winds

# Load Oct 24 data, extract 500 hPa winds
u_500 = batch.atmos_vars["u"][0, 1, level_idx_500].cpu().numpy()
v_500 = batch.atmos_vars["v"][0, 1, level_idx_500].cpu().numpy()

# Calculate FTLE
ftle_field, _ = calculate_ftle_from_winds(
    u_500, v_500, lats, lons,
    integration_time_hours=48,
    direction='forward'
)
```

**Step 3: Select Perturbation Locations (15 min)**
```python
# Use seeding_location_selection.py module
from seeding_location_selection import select_seeding_candidates

# Atlantic basin bounds
BOUNDS_SANDY = {'lat': (10, 45), 'lon': (260, 300)}

selected_lats, selected_lons, scores = select_seeding_candidates(
    ftle_field, lats, lons,
    ftle_percentile=85,  # Slightly lower for TCs (more candidates)
    geographic_bounds=BOUNDS_SANDY,
    min_separation_km=400,
    max_candidates=5
)
```

**Step 4: Create Seeding Mask (5 min)**
```python
# Use cloud_seeding_perturbation.py module
from cloud_seeding_perturbation import create_seeding_mask

seeding_locations = [
    {'lat_center': lat, 'lon_center': lon, 'radius_km': 300}
    for lat, lon in zip(selected_lats, selected_lons)
]

seeding_mask = create_seeding_mask(seeding_locations, lats, lons)
```

**Step 5: Apply Perturbation (5 min)**
```python
from cloud_seeding_perturbation import apply_physically_consistent_cloud_seeding

SEEDING_CONFIG_SANDY = {
    'layers_mb': [700.0, 500.0, 300.0],
    'freeze_efficiency': 0.60,
    'fallout_fraction': 0.80,
    'max_removal_fraction': 0.50,
    'vertical_coupling': False
}

# Clone batch
batch_seeded = clone_batch(batch_control)

# Apply perturbation
delta_T, delta_q, diagnostics = apply_physically_consistent_cloud_seeding(
    batch_seeded, seeding_mask, SEEDING_CONFIG_SANDY
)

print_diagnostics(diagnostics, SEEDING_CONFIG_SANDY)
```

**Step 6: Run Forecast & Compare (2 hours)**
```python
# Run perturbed forecast
preds_seeded = run_forecast(model, batch_seeded, tracker_seeded, steps=28)

# Calculate track error
forecast_track_seeded = extract_track_from_tracker(tracker_seeded)
track_deviation = compute_track_differences(
    forecast_track_control, forecast_track_seeded
)

# Plot comparison
plot_track_comparison(
    {'Control': forecast_track_control, 'FTLE-Seeded': forecast_track_seeded},
    obs_track,
    title="Sandy: FTLE-Guided Cloud Seeding Test"
)
```

**Total Time:** ~5 hours (mostly model inference)

---

### 6.5 Success Criteria

**Minimum Success:**
- Perturbations produce measurable track deviation (>50 km at 72 hrs)
- Perturbations remain thermodynamically valid (no NaNs, no unphysical RH)
- Method replicable (clear workflow, documented parameters)

**Strong Success:**
- Track deviation >200 km at 120 hrs (comparable to your previous results)
- FTLE-guided perturbations show larger impact than random locations
- Physical mechanisms identifiable (e.g., steering flow modification visible in winds)

**Breakthrough Success:**
- Perturbations improve landfall forecast (reduce error vs Aurora's baseline)
- Teleconnections observed (downstream Rossby waves, remote IVT changes)
- Methodology generalizes to other TCs

---

## Part 7: Key Insights from Moyan's Experiment

### 7.1 Teleconnection Mechanism

**Moyan's Observation:**
> "When he perturbs in the Pacific, in next few days the Atlantic same latitude would have some IVT changes"

**Physical Mechanism:**
1. **Pacific heating perturbation** → Local pressure fall → Cyclonic circulation
2. **Rossby wave generation** → Perturbation propagates downstream (eastward group velocity)
3. **Mid-latitude waveguide** → Rossby waves trapped in jet stream
4. **Atlantic arrival** → Modified IVT 2-3 days later (Rossby wave phase speed ~15 m/s)

**Relevance to TCs:**
- Sandy's unusual track involved **blocking pattern over North Atlantic**
- Upstream perturbations (e.g., in Caribbean) could modify this block
- **Test hypothesis:** Perturbations west of Sandy → changes in blocking → altered track
- **Timescale:** 24-72 hrs for perturbation to affect Atlantic blocking

**Implication:**
- **Don't expect immediate effects** - allow 1-2 days for perturbation to propagate
- **Analyze time-lagged correlations** between perturbation location and Sandy track
- **Look for Rossby wave trains** in 500 hPa geopotential height anomalies

---

### 7.2 Perturbation Takes Time to Affect Field Variables

**Key Insight:** The perturbation doesn't instantly change the entire flow. Instead:
- **t=0-12 hrs:** Local adjustment (pressure fall, wind response)
- **t=12-24 hrs:** Mesoscale propagation (gravity waves, convective adjustment)
- **t=24-48 hrs:** Synoptic-scale reorganization (Rossby waves, jet stream shifts)
- **t=48-120 hrs:** Large-scale impacts (blocking modifications, remote teleconnections)

**For Sandy Test:**
- Don't judge results at first 6-12 hrs (local effects only)
- Focus on **24-72 hr forecast** (synoptic adjustment complete)
- **120+ hr forecast** may show remote teleconnections

---

## Part 8: Advantages of Moyan's Method for Sandy

1. **FTLE Targeting Overcomes Aurora's Base Forecast Failure:**
   - Your previous analysis showed Aurora fails to predict Sandy's westward turn
   - FTLE identifies **where perturbations have maximum leverage**
   - Even if Aurora's dynamics are wrong, FTLE-guided perturbations may **steer forecast toward correct track**

2. **Thermodynamic Consistency Prevents Model Blowup:**
   - Your previous perturbations were large (2.49 K, 8° scale)
   - Moyan's method includes **moisture removal + heating**, maintaining physical balance
   - Reduces risk of Aurora producing unphysical states

3. **Smaller, Targeted Perturbations = Higher Signal-to-Noise:**
   - 4-5 FTLE-guided locations vs 25-location grid
   - Easier to interpret which perturbations mattered
   - More computationally efficient

4. **Replicable Across Events:**
   - Moyan's method is **event-agnostic** (just needs winds for FTLE)
   - Your previous method required **hand-tuning grid** for each TC
   - Enables systematic multi-case studies

---

## Conclusion

**Recommendation:** Adopt Moyan's FTLE + cloud seeding framework with TC-specific modifications:
- ✅ Use FTLE to identify sensitive steering flow regions
- ✅ Apply cloud seeding perturbations (heating + drying) at these locations
- ✅ Use TC-appropriate scales (300 km radius, 700-300 hPa steering levels)
- ✅ Expect delayed effects (24-72 hrs) via Rossby wave propagation
- ✅ Validate with IVT, track deviation, and field comparison metrics

**Quick Test Plan:** 5-hour experiment using Oct 24 data, FTLE-guided 3-5 perturbation sites, compare control vs seeded forecasts.

**Expected Outcome:** Measurable track deviations (>200 km at 120 hrs), potential improvement over Aurora's baseline, demonstration of FTLE-guided methodology for TCs.

---

**Next Steps:**
1. Run baseline Sandy forecast (replicate your previous work)
2. Calculate FTLE field using new module
3. Apply FTLE-guided perturbations with adapted parameters
4. Compare tracks and document results
5. If successful: Extend to other TCs (Matthew 2016, Harvey 2017, etc.)

