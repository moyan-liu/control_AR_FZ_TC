# Literature Review: Lyapunov Exponents for Atmospheric Rivers, Tropical Cyclones, and Blocking Events

## Summary of Reviewed Papers

### AR_Climatology (Garaboa-Paz et al., 2017)
- **Citation:** Garaboa-Paz, D., Eiras-Barca, J., and Pérez-Muñuzuri, V.: Climatology of Lyapunov exponents: the link between atmospheric rivers and large-scale mixing variability, Earth Syst. Dynam., 8, 865–873, https://doi.org/10.5194/esd-8-865-2017, 2017.

- **Problem/Goal:** Study large-scale tropospheric mixing variability using finite-time Lyapunov exponents (FTLEs) and analyze the role of atmospheric rivers (ARs) and baroclinic instabilities in tropospheric mixing for the period 1979-2014.

- **Data/Setting:** ERA-Interim reanalysis data (1979-2014), 0.7° horizontal resolution, 100 hPa vertical resolution, 6-hour temporal resolution at 850 hPa level. AR database from Guan and Waliser (2015).

- **Methods:** 
  - FTLE calculation: λ(τ,t₀,r₀) = (1/|τ|) log√μₘₐₓ(C̃(τ,t₀,r₀))
  - Cauchy-Green deformation tensor: C̃(τ,t₀,r₀) = (∇r(t₀+τ;t₀,r₀))ᵀ × G(θ(τ)) × ∇r(t₀+τ;t₀,r₀)
  - Eady baroclinic growth rate: σ_BI = 0.31|f|/N |∂V/∂z|
  - Lagrangian particle trajectories with 4th-order Runge-Kutta integration
  - Integration time τ ∈ [1,15] days, optimal correlation at τ = 5 days

- **Findings:**
  - FTLE values twice as high in midlatitudes compared to equatorial zones
  - Strong correlation (R=0.78) between AR occurrence and FTLE climatology
  - Correlation of 0.80 between backward FTLE anomalies and MEI index in western Pacific
  - ARs contribute 15% to tropospheric mixing in Saharan Morocco vs <5% in British Isles
  - AR precipitation contribution: 40% larger in Saharan Morocco than British Isles
  - Annual cycle with higher mixing in winter than summer in midlatitudes

- **Uncertainties/Limitations:**
  - Limited to 850 hPa level analysis
  - Integration time dependent on synoptic timescale
  - Regional variations in AR impact not fully characterized
  - Deformation due to vertical movement not accounted for in sphere calculations

- **Applications:**
  - **TCs:** Not directly addressed, but FTLE methodology applicable to hurricane mixing analysis
  - **ARs:** Primary focus - ARs identified as key drivers of large-scale tropospheric mixing, with regional precipitation impact variations
  - **Blocking:** Indirectly addressed through baroclinic instability analysis and storm track identification
  - **Transport/Jet barriers:** FTLE ridges identify transport barriers and Lagrangian coherent structures; correlation with Eady growth rate shows jet-mixing relationships

- **Notes for Aurora/URI integration:** 
  - Input: Wind fields (u,v,w) at multiple pressure levels, integration time parameter
  - Output: FTLE fields indicating mixing intensity and transport barriers
  - Runtime: Computationally intensive for large ensembles of particles
  - Data needs: High-resolution reanalysis data with 6-hour temporal resolution minimum

### Block_Framework (Lucarini & Gritsun, 2020)
- **Citation:** Lucarini, V. and Gritsun, A.: A new mathematical framework for atmospheric blocking events, Climate Dynamics, 54, 575–598, https://doi.org/10.1007/s00382-019-05018-2, 2020.

- **Problem/Goal:** Develop a new mathematical framework for understanding atmospheric blocking events using dynamical systems theory, focusing on their predictability properties, association with atmospheric modes, and fundamental modeling challenges.

- **Data/Setting:** Marshall-Molteni (1993) quasi-geostrophic 3-layer model (T18 resolution, Northern Hemisphere, 125,000 days), forced with ERA40 1983-1992 winter climatology. Tibaldi-Molteni blocking index for event detection.

- **Methods:**
  - Finite-time Lyapunov exponents (FTLEs): λ(τ,t₀,r₀) = (1/|τ|)log√μₘₐₓ(C̃(τ,t₀,r₀))
  - Covariant Lyapunov vectors (CLVs) and unstable periodic orbits (UPOs)
  - Marshall-Molteni model equations: ∂ₜqⱼ + J(ψⱼ,qⱼ) = -Dⱼ + Sⱼ
  - Eady baroclinic growth rate: σ_BI = 0.31|f|/N |∂V/∂z|
  - UPO detection using Newton iterative methods with 2711 UPOs found

- **Findings:**
  - Blocking events associated with anomalously high atmospheric instability
  - Atlantic blockings: predictability lowest at onset/decay, enhanced in mature phase
  - Pacific blockings: predictability lowest in mature phase (opposite pattern)
  - Global blockings very rare with highest instability levels
  - Longer-lived blockings correlate with higher instability
  - UPOs representing blocking states have higher degrees of instability than zonal flow UPOs
  - System exhibits severe violation of hyperbolicity due to variable unstable dimensions (37-89 range)
  - 441 of 2711 UPOs (15%) feature blocked states

- **Uncertainties/Limitations:**
  - Low-resolution model (T18) and simplified QG approximation
  - Limited to Northern Hemisphere and winter conditions
  - Computational complexity limits UPO sampling to short periods
  - Non-hyperbolic system violates structural stability assumptions
  - Results need validation with higher-resolution and more complex models

- **Applications:**
  - **TCs:** Not directly addressed, but FTLE/UPO framework applicable to hurricane dynamics analysis
  - **ARs:** Indirectly relevant through moisture transport and baroclinic instability connections
  - **Blocking:** Primary focus - blocking events interpreted as trajectory visits to neighborhoods of highly unstable UPOs; provides rigorous mathematical foundation for weather regimes
  - **Transport/Jet barriers:** CLVs and UPOs identify transport barriers and atmospheric modes; correlation with teleconnection patterns (PNA/NAO)

- **Notes for Aurora/URI integration:**
  - Input: 3D atmospheric state variables (ψ, q), model parameters for QG equations
  - Output: FTLE fields, CLV projections, UPO classifications, instability metrics
  - Runtime: Extremely computationally intensive for UPO calculations; scales exponentially with system dimension
  - Data needs: High-resolution wind and geopotential fields; may require model state space access
  - Framework provides fundamental theoretical basis for understanding blocking predictability limits
