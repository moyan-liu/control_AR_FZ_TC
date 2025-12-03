def haversine_distance(lat1, lon1, lat2, lon2):
  R = 6371.0  # Earth radius in km

  # Convert to radians
  lat1_rad = np.deg2rad(lat1)
  lat2_rad = np.deg2rad(lat2)
  lon1_rad = np.deg2rad(lon1)
  lon2_rad = np.deg2rad(lon2)

  # Haversine formula
  dlat = lat2_rad - lat1_rad
  dlon = lon2_rad - lon1_rad

  a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
  c = 2 * np.arcsin(np.sqrt(a))

  distance = R * c
  return distance


def create_seeding_mask(seeding_locations, lat_grid, lon_grid):
  # Convert torch tensors to numpy if needed
  if torch.is_tensor(lat_grid):
      lat_grid = lat_grid.cpu().numpy()
  if torch.is_tensor(lon_grid):
      lon_grid = lon_grid.cpu().numpy()

  # If 1D arrays, create 2D grids
  if lat_grid.ndim == 1 and lon_grid.ndim == 1:
      lon_grid_2d, lat_grid_2d = np.meshgrid(lon_grid, lat_grid)
  else:
      lat_grid_2d = lat_grid
      lon_grid_2d = lon_grid

  # Initialize empty mask
  combined_mask = np.zeros_like(lat_grid_2d, dtype=bool)

  # Loop through each seeding location
  for location in seeding_locations:
      lat_center = location['lat_center']
      lon_center = location['lon_center']
      radius_km = location['radius_km']

      # Calculate distance from this center to all grid points
      distances = haversine_distance(lat_center, lon_center, lat_grid_2d, lon_grid_2d)

      # Create circular mask for this location
      circle_mask = distances <= radius_km

      # Add to combined mask (logical OR - union of all circles)
      combined_mask = combined_mask | circle_mask

  return combined_mask

# Your seeding locations
seeding_locations = [      
    {'lat_center': 25.50, 'lon_center': 213.00, 'radius_km': 200},
    {'lat_center': 24.00, 'lon_center': 207.75, 'radius_km': 200},
    {'lat_center': 34.50, 'lon_center': 177.75, 'radius_km': 200},
    {'lat_center': 28.50, 'lon_center': 173.25, 'radius_km': 200},
    {'lat_center': 26.25, 'lon_center': 196.50, 'radius_km': 200},
    {'lat_center': 33.75, 'lon_center': 185.25, 'radius_km': 200},
]

# Get lat/lon grids from your batch
# Handle both torch tensors and numpy arrays
lat_grid = batch_custom.metadata.lat  # Can be torch tensor on CUDA
lon_grid = batch_custom.metadata.lon  # Can be torch tensor on CUDA

lats_np = batch_custom.metadata.lat.cpu().numpy()
lons_np = batch_custom.metadata.lon.cpu().numpy()

# Create combined mask from all locations
# The function now handles torch tensors automatically
seeding_mask_spatial = create_seeding_mask(
  seeding_locations,
  lat_grid,
  lon_grid
)

print(f"Mask shape: {seeding_mask_spatial.shape}")
print(f"Number of seeded grid cells: {seeding_mask_spatial.sum()}")
print(f"Percentage of domain seeded: {seeding_mask_spatial.sum() / seeding_mask_spatial.size * 100:.2f}%")

def calculate_q_sat(T, P):
    # Magnus formula for saturation vapor pressure (hPa)
    T_celsius = T - 273.15
    e_s = 6.112 * torch.exp((17.67 * T_celsius) / (T_celsius + 243.5))  # hPa
    
    # Convert to Pa
    e_s_Pa = e_s * 100
    
    # Saturation specific humidity
    epsilon = 0.622
    q_sat = epsilon * e_s_Pa / (P - 0.378 * e_s_Pa)
    
    return q_sat

print(f"✅ Saturation calculation function defined")

# PHYSICALLY CONSISTENT Cloud Seeding Perturbation (CORRECTED)
def apply_physically_consistent_cloud_seeding(batch, seeding_mask_spatial, seeding_params):

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
      'q_precipitated_mean': [],  # Added for tracking
      'energy_released_mean': [],  # Added for tracking
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
      # Equation: q_frozen = q × η_freeze × mask
      freeze_efficiency = seeding_params.get('freeze_efficiency', 0.30)
      max_removal_fraction = seeding_params.get('max_removal_fraction', 0.80)
    
      # Calculate potential freezing
      q_frozen_potential = q_old * freeze_efficiency * mask_torch
    
      # Limit to preserve physical moisture levels
      # Physical reasoning: Can't freeze more vapor than exists!
      # Keep at least 20% of vapor to avoid unphysical dry air
      q_frozen = torch.minimum(q_frozen_potential, q_old * max_removal_fraction)
    
      # Track where moisture limitation applied
      moisture_limited = (q_frozen < q_frozen_potential).any()
      if moisture_limited and level_idx == layer_indices[0]:
          # Only warn once (first level)
          pct_limited = ((q_frozen < q_frozen_potential).sum() /
                         (mask_torch > 0).sum() * 100).item()
          diagnostics['warnings'].append(
              f"ℹ️  {pct_limited:.1f}% of seeded cells were moisture-limited "
              f"(too dry for full {freeze_efficiency*100:.0f}% efficiency)"
          )
      # ========== LATENT HEAT RELEASE ==========
      # CRITICAL: Vapor → ice is DEPOSITION, not freezing!
      # - Deposition (vapor → ice): releases L_v + L_f = 2.834 MJ/kg
      # Physical reason: 
      # 1. Vapor → liquid would release L_v
      # 2. Liquid → ice would release L_f
      # 3. Vapor → ice releases BOTH: L_v + L_f
      #
      # Equation: ΔE = (L_v + L_f) × q_frozen
      delta_E = L_d * q_frozen  # J/kg (energy released to air)
      delta_T = delta_E / C_p   # K (temperature increase)

      # ========== MOISTURE REMOVAL ==========
      # ALL frozen vapor leaves the vapor phase
      # This is correct regardless of what happens next:
      # - Some ice may precipitate out (removed from column)
      # - Some ice may stay suspended (still not vapor)
      # - Either way, it's not counted in Aurora's "q" (vapor mixing ratio)
      #
      # Note: fallout_fraction determines precipitation amount,
      # but doesn't affect energy/temperature at THIS level
      # (the heat was already released when ice formed)
      q_removed = q_frozen  # kg/kg

      # Track precipitation for diagnostics
      fallout_fraction = seeding_params.get('fallout_fraction', 0.40)
      q_precip = q_frozen * fallout_fraction  # Amount that falls out

      # ========== APPLY CHANGES ==========
      T_new = T_old + delta_T  # Temperature INCREASES (warming from deposition)
      q_new = q_old - q_removed  # Humidity decreases

      # ========== THERMODYNAMIC CONSISTENCY CHECK ==========
      # Recalculate saturation mixing ratio at new temperature
      # Equation: q_sat = f(T_new, P)
      q_sat_new = calculate_q_sat(T_new, P_Pa)
      RH_new = q_new / (q_sat_new + 1e-10)

      # Check for unphysical states
      if (q_new < 0).any():
          min_q = q_new.min().item()
          diagnostics['warnings'].append(
              f"⚠️  Level {P_hPa:.0f} hPa: Negative q detected! Min q = {min_q:.6f} kg/kg"
          )
          # Physical interpretation: tried to freeze more vapor than available
          # Clip to zero and recalculate delta_T based on actual freezing
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
          # Note: This shouldn't happen with warming, but check anyway

      if (RH_new < 0.01).any() and (RH_old.mean() > 0.1):
          min_rh = RH_new.min().item()
          diagnostics['warnings'].append(
              f"⚠️  Level {P_hPa:.0f} hPa: Created very dry air! Min RH = {min_rh*100:.1f}%"
          )

      # Additional check: Warming should partially offset RH decrease
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
      # Warming in seeded level can affect adjacent levels through:
      # - Convective adjustment
      # - Radiative transfer
      # - Turbulent mixing
      if seeding_params.get('vertical_coupling', True):
          coupling_factor = seeding_params.get('coupling_factor', 0.3)
          for offset in [-1, 1]:
              adj_idx = level_idx + offset
              if 0 <= adj_idx < len(batch.metadata.atmos_levels):
                  delta_T_adj = delta_T * coupling_factor
                  batch.atmos_vars["t"][0, 1, adj_idx] += delta_T_adj  # Only timestep 1
                  delta_T_applied[adj_idx] += delta_T_adj

  return delta_T_applied, delta_q_applied, diagnostics

# ============= UPDATED SEEDING CONFIGURATION =============
# : 50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, and 1000 hPa
seeding_params_realistic = {
    'layers_mb': [850.0, 700.0,600],
    'freeze_efficiency': 0.70,           # 30% of moisture freezes
    'fallout_fraction': 0.90,            # 70% of frozen water precipitates out
    'energy_method': 'net_realistic',    # Proper energy balance
    'vertical_coupling': False,
    'coupling_factor': 0.3,
    'max_removal_fraction':0.6
}

# Create perturbed batch (clone original to preserve control)
batch_control = batch_custom
batch_seeded = Batch(
  surf_vars={k: v.clone() for k, v in batch_custom.surf_vars.items()},
  atmos_vars={k: v.clone() for k, v in batch_custom.atmos_vars.items()},
  static_vars={k: v.clone() for k, v in batch_custom.static_vars.items()},
  metadata=batch_custom.metadata
).to("cuda")

# Apply PHYSICALLY CONSISTENT seeding perturbation
delta_T_field, delta_q_field, diagnostics = apply_physically_consistent_cloud_seeding(
  batch_seeded,
  seeding_mask_spatial,
  seeding_params_realistic
)
