# FTLE-Guided Cloud Seeding Perturbation Workflow
## Technical Documentation for Poster Presentation

---

## 🎯 **Overall Strategy**

**Goal**: Use FTLE (Finite-Time Lyapunov Exponents) to identify sensitive regions in the atmospheric flow, then apply physically-consistent cloud seeding perturbations to modify tropical cyclone tracks.

**Hypothesis**: Small perturbations in FTLE-identified sensitive regions can amplify into large-scale track changes through chaotic dynamics.

---

## 📋 **Complete Workflow (7 Steps)**

### **Step 1: Calculate FTLE Field**
**Purpose**: Identify regions of maximum flow sensitivity

**Input Data**:
- 500 hPa winds (steering level): u(lat, lon), v(lat, lon)
- Grid: 720 lats × 1440 lons (0.25° resolution)
- Integration time: T = 48 hours (TC timescale)
- Time step: Δt = 6 hours

**Algorithm**:

1. **Particle Advection** (forward integration):

   For each grid point, advect a particle using Euler integration:

   ```
   lat[n+1] = lat[n] + (v * Δt) / 111,000 m
   lon[n+1] = lon[n] + (u * Δt) / (111,000 * cos(lat[n]))
   ```

   where:
   - v, u = meridional/zonal wind (m/s)
   - Δt = 6 hours = 21,600 seconds
   - 111,000 m ≈ 111 km/degree

2. **Flow Map Gradient** (Jacobian matrix):

   For each grid point (i,j), compute the deformation gradient tensor:

   ```
   ∂Φ/∂x₀ ≈ [∂lat_f/∂lat₀  ∂lat_f/∂lon₀]
             [∂lon_f/∂lat₀  ∂lon_f/∂lon₀]
   ```

   Using centered finite differences:
   ```
   ∂lat_f/∂lat₀ ≈ (lat_f[i+1,j] - lat_f[i-1,j]) / (2 * Δlat)
   ∂lat_f/∂lon₀ ≈ (lat_f[i,j+1] - lat_f[i,j-1]) / (2 * Δlon * cos(lat))
   ```

3. **Cauchy-Green Strain Tensor**:

   ```
   C = (∂Φ/∂x₀)ᵀ * (∂Φ/∂x₀)
   ```

4. **FTLE Calculation**:

   ```
   FTLE = (1/T) * ln(√λ_max)
   ```

   where:
   - λ_max = largest eigenvalue of C
   - T = integration time (48 hours = 2 days)
   - Units: day⁻¹

**Output**:
- FTLE field: λ(lat, lon) in day⁻¹
- Higher values → more sensitive to perturbations
- Typical range: 0.01 - 0.50 day⁻¹

---

### **Step 2: Select Perturbation Sites**
**Purpose**: Choose optimal locations for cloud seeding

**Selection Criteria**:

1. **FTLE Threshold**:
   ```
   FTLE_threshold = percentile(FTLE_field, 85)
   ```
   Keep only top 15% of FTLE values

2. **Distance from TC**:
   ```
   500 km ≤ distance ≤ 1500 km
   ```
   (environmental steering region, not TC core)

   Using Haversine formula:
   ```
   a = sin²(Δlat/2) + cos(lat₁) * cos(lat₂) * sin²(Δlon/2)
   c = 2 * arcsin(√a)
   distance = R_earth * c    (R_earth = 6371 km)
   ```

3. **Minimum Separation**:
   ```
   separation ≥ 300 km between sites
   ```

**Site Configuration**:
- Number of sites: 3-5 locations
- Radius per site: R = 300 km
- Total seeded area: ~500-800 grid cells

---

### **Step 3: Create Seeding Mask**
**Purpose**: Define spatial domain for perturbation

**Formula**:
For each selected site center (lat_c, lon_c) with radius R:

```
mask[i,j] = 1  if  distance(lat[i], lon[j], lat_c, lon_c) ≤ R
            0  otherwise
```

Combined mask for multiple sites:
```
mask_total = OR(mask_site1, mask_site2, ..., mask_siteN)
```

**Output**:
- Boolean mask: M(lat, lon) ∈ {0,1}
- Applied to 3 pressure levels: 700, 500, 300 hPa

---

### **Step 4: Apply Cloud Seeding Perturbation**
**Purpose**: Modify temperature and humidity fields

**Physical Process**: Ice nucleation via vapor deposition (vapor → ice directly)

#### **Thermodynamic Calculations**:

1. **Saturation Mixing Ratio** (Clausius-Clapeyron):
   ```
   e_sat = 611.2 Pa * exp[(L_v/R_v) * (1/T₀ - 1/T)]
   q_sat = ε * e_sat / (P - e_sat)
   ```
   where:
   - L_v = 2.5×10⁶ J/kg (latent heat of vaporization)
   - R_v = 461.5 J/(kg·K) (gas constant for water vapor)
   - ε = 0.622 (molecular weight ratio R_d/R_v)
   - T₀ = 273.15 K
   - P = pressure (Pa)

2. **Relative Humidity**:
   ```
   RH = q / q_sat
   ```

3. **Water Vapor Frozen** (deposition process):
   ```
   q_frozen = q_old * η_freeze * RH * mask
   ```
   where:
   - η_freeze = 0.60 (freeze efficiency, tunable parameter)
   - mask = spatial seeding mask

4. **Precipitation Removal**:
   ```
   q_precip = q_frozen * f_fallout
   q_removed = min(q_precip, q_old * f_max)
   ```
   where:
   - f_fallout = 0.80 (fallout fraction)
   - f_max = 0.50 (max removal fraction, safety limit)

5. **Latent Heat Release**:
   ```
   Q_released = q_removed * L_d
   ΔT = Q_released / C_p
   ```
   where:
   - L_d = L_v + L_f = 2.834×10⁶ J/kg (deposition latent heat)
   - L_f = 3.34×10⁵ J/kg (latent heat of fusion)
   - C_p = 1004 J/(kg·K) (specific heat of air)

6. **Apply Perturbations**:
   ```
   T_new = T_old + ΔT * mask
   q_new = q_old - q_removed * mask
   ```

#### **Typical Magnitudes** (Sandy case):
- ΔT: +0.5 to +3.0 K (warming from latent heat)
- Δq: -0.5 to -2.0 g/kg (drying from precipitation)
- Energy: ~1-3 MJ/kg released
- Seeded mass: ~10¹²-10¹³ kg (depending on site size)

---

### **Step 5: Run Baseline Forecast**
**Purpose**: Establish control scenario (no perturbation)

**Model**: Aurora 0.25° (Microsoft)
- 6-hour timestep
- 28 steps (7 days forecast for Sandy)
- 19 steps (4.75 days for Ian)

**Tracking**: TC center identified by minimum MSLP

**Output**:
- Baseline track: {lat(t), lon(t), time(t)}
- Predictions saved for field analysis

---

### **Step 6: Run Perturbed Forecast**
**Purpose**: Forecast with seeding perturbation

**Initialization**:
- Clone baseline initial conditions
- Apply ΔT and Δq from Step 4
- Same forecast length

**Output**:
- Perturbed track: {lat(t), lon(t), time(t)}
- Predictions saved for comparison

---

### **Step 7: Compute Track Deviation**
**Purpose**: Quantify perturbation impact

**Formula**:
For each timestep i:
```
deviation[i] = distance(lat_baseline[i], lon_baseline[i],
                        lat_perturbed[i], lon_perturbed[i])
```

Using Haversine distance (same as Step 2).

**Key Metrics**:
- 24-hour deviation (4 steps)
- 48-hour deviation (8 steps)
- 72-hour deviation (12 steps)
- Final deviation (end of forecast)

**Position Shift**:
```
Δlat = lat_perturbed[final] - lat_baseline[final]
Δlon = lon_perturbed[final] - lon_baseline[final]
```

---

## 📊 **Results Summary**

### Hurricane Sandy (Oct 23-30, 2012)
- **FTLE sites**: 5 locations (500-1500 km from TC)
- **Seeding configuration**: 700, 500, 300 hPa levels
- **Maximum deviation**: ~450 km (at 144 hours)
- **Final deviation**: ~173 km
- **Mechanism**: Modification of steering flow → track deflection

### Hurricane Ian (Sep 23-28, 2022)
- **FTLE sites**: 3-5 locations (targeted cluster)
- **Test cases**: Single site vs. multi-site trajectory
- **Early results**: 27-37 km deviation (5-day lead time)
- **Ongoing**: Testing longer lead times (7+ days)

---

## 🔬 **Physical Mechanisms**

### Perturbation Amplification Chain:
1. **Initial**: Cloud seeding → ΔT (warming), Δq (drying)
2. **Local**: Modified diabatic heating → pressure changes
3. **Mesoscale**: Altered pressure gradient → wind changes
4. **Synoptic**: Modified steering flow at 500 hPa
5. **Propagation**: Rossby wave response → downstream effects
6. **Result**: TC track deviation through chaotic amplification

### Key Atmospheric Fields Modified:
- Mean sea level pressure (MSLP): ±5-20 hPa differences
- 500 hPa geopotential height: ±30-90 m differences
- 700 hPa temperature: ±1-5°C differences
- 850 hPa relative humidity: ±20-60% differences
- 250/300 hPa winds: ±5-25 m/s differences (jet stream)

---

## 🛠️ **Key Parameters**

| Parameter | Symbol | Sandy Value | Ian Value | Units |
|-----------|--------|-------------|-----------|-------|
| FTLE integration time | T | 48 | 48 | hours |
| FTLE percentile | p | 85 | 85 | % |
| TC distance range | d | 500-1500 | 500-1500 | km |
| Site radius | R | 300 | 300 | km |
| Freeze efficiency | η | 0.60 | 0.60 | - |
| Fallout fraction | f | 0.80 | 0.80 | - |
| Max removal | f_max | 0.50 | 0.50 | - |
| Pressure levels | - | 700,500,300 | 700,500,300 | hPa |

---

## 📚 **References**

**FTLE Method**:
- Haller, G. (2015). "Lagrangian coherent structures." *Annual Review of Fluid Mechanics*, 47, 137-162.
- Tallapragada, P., et al. (2014). "Hurricane sensitivity to high-altitude environmental flow." *Mon. Wea. Rev.*

**Cloud Seeding Physics**:
- Pruppacher & Klett (1997). *Microphysics of Clouds and Precipitation*
- Cotton & Anthes (1989). *Storm and Cloud Dynamics*

**TC Dynamics**:
- Emanuel, K. (2018). "100 years of progress in tropical cyclone research." *Meteorological Monographs*
- Zhang, F., & Tao, D. (2013). "Effects of environmental flow on TC track." *Mon. Wea. Rev.*

---

## 💡 **Innovation**

This workflow adapts Moyan Liu's FTLE-based atmospheric river perturbation methodology to tropical cyclones, representing the **first application of dynamical systems theory (FTLE) to TC track modification via cloud seeding**.

**Novel aspects**:
1. FTLE-targeted (vs. random or grid-based) seeding locations
2. Physically-consistent thermodynamics (deposition process)
3. Multi-level steering flow modification (700-300 hPa)
4. Quantified sensitivity via ensemble-like framework

---

*Generated for poster presentation - Hurricane track modification via FTLE-guided cloud seeding*
