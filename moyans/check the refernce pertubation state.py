  # ===================== CORRECTED INITIAL CONDITION PLOT =====================
  # Use TIMESTEP 1 (the actual initial condition for forecasting)

  print("🗺️  Plotting CORRECTED initial perturbation (timestep 1 only)...")

  # Get metadata
  lat_vals = _to_np(batch_control.metadata.lat)
  lon_vals = _to_np(batch_control.metadata.lon)
  levels = _to_np(batch_control.metadata.atmos_levels)
  lat_len, lon_len = len(lat_vals), len(lon_vals)

  lev_idx = np.argmin(np.abs(levels - 700))

  # Get TIMESTEP 1 only (index 1)
  t_ctrl = _to_np(batch_control.atmos_vars["t"])
  t_seed = _to_np(batch_seeded.atmos_vars["t"])

  # Extract: [batch=0, TIME=1, level, lat, lon]
  t_ctrl_t1 = t_ctrl[0, 1, lev_idx, :, :]
  t_seed_t1 = t_seed[0, 1, lev_idx, :, :]

  t_diff = t_seed_t1 - t_ctrl_t1

  print(f"✅ Using timestep 1 (current time, the actual initial condition)")
  print(f"   Points affected: {np.sum(np.abs(t_diff) > 1e-6)}")
  print(f"   Max |Δ|: {np.max(np.abs(t_diff)):.4f} K")

  # Plot
  fig, ax = plt.subplots(1, 1, figsize=(14, 9),
                         subplot_kw={'projection': ccrs.PlateCarree(central_longitude=CENT_LON)})

  data_crs = ccrs.PlateCarree()
  setup_map(ax, EXTENT, data_crs)

  Lon, Lat = np.meshgrid(lon_vals, lat_vals)

  vmax = np.max(np.abs(t_diff))

  cf = ax.contourf(Lon, Lat, t_diff,
                   levels=np.linspace(-vmax, vmax, 21),
                   cmap='RdBu_r', extend='both',
                   transform=data_crs, alpha=0.85)

  cbar = plt.colorbar(cf, ax=ax, pad=0.02)
  cbar.set_label('Temperature Difference [K]\n(Seeded − Control)', fontsize=12, fontweight='bold')

  # Draw 400 km circle
  from matplotlib.patches import Circle
  seed_lon = seeding_location['lon_center']
  seed_lat = seeding_location['lat_center']
  circle = Circle((seed_lon, seed_lat), radius=400/111,  # approximate
                  transform=data_crs, fill=False, edgecolor='black',
                  linewidth=2, linestyle='--', zorder=5, label='400 km radius')
  ax.add_patch(circle)

  maybe_plot_seed_star(ax, data_crs)

  ax.set_title(f'CORRECTED: Initial Temperature Perturbation at 700 hPa (Timestep 1)\n' +
               f'{np.sum(np.abs(t_diff) > 1e-6)} points affected | Max: {vmax:.4f} K',
               fontsize=13, fontweight='bold')

  plt.legend(loc='upper right')
  plt.tight_layout()
  plt.show()

  print("\n✅ This is the CORRECT initial perturbation that Aurora will forecast from!")




## Now check time step 0 which should be identiacl 
  # ===================== VERIFY TIMESTEP 0 HAS NO CHANGES =====================
  # Check that historical timestep (t=-6hr) is identical between control and seeded

  print("🔍 Verifying Timestep 0 (t=-6hr) has NO changes...")
  print("=" * 80)

  # Get metadata
  lat_vals = _to_np(batch_control.metadata.lat)
  lon_vals = _to_np(batch_control.metadata.lon)
  levels = _to_np(batch_control.metadata.atmos_levels)
  lat_len, lon_len = len(lat_vals), len(lon_vals)

  lev_idx = np.argmin(np.abs(levels - 700))

  # Get TIMESTEP 0 (historical, should be identical)
  t_ctrl = _to_np(batch_control.atmos_vars["t"])
  t_seed = _to_np(batch_seeded.atmos_vars["t"])

  # Extract: [batch=0, TIME=0, level, lat, lon]
  t_ctrl_t0 = t_ctrl[0, 0, lev_idx, :, :]
  t_seed_t0 = t_seed[0, 0, lev_idx, :, :]

  t_diff = t_seed_t0 - t_ctrl_t0

  print(f"\n📊 Timestep 0 Statistics at 700 hPa:")
  print(f"   Min difference: {np.min(t_diff):.10f} K")
  print(f"   Max difference: {np.max(t_diff):.10f} K")
  print(f"   Mean difference: {np.mean(t_diff):.10f} K")
  print(f"   Std deviation: {np.std(t_diff):.10f} K")
  print(f"   Points with |Δ| > 1e-6: {np.sum(np.abs(t_diff) > 1e-6)}")

  # Plot
  fig, ax = plt.subplots(1, 1, figsize=(14, 9),
                         subplot_kw={'projection': ccrs.PlateCarree(central_longitude=CENT_LON)})

  data_crs = ccrs.PlateCarree()
  setup_map(ax, EXTENT, data_crs)

  Lon, Lat = np.meshgrid(lon_vals, lat_vals)

  # Use very small scale to detect any tiny differences
  vmax = max(np.max(np.abs(t_diff)), 1e-8)

  cf = ax.contourf(Lon, Lat, t_diff,
                   levels=np.linspace(-vmax, vmax, 21),
                   cmap='RdBu_r', extend='both',
                   transform=data_crs, alpha=0.85)

  cbar = plt.colorbar(cf, ax=ax, pad=0.02)
  cbar.set_label('Temperature Difference [K]\n(Seeded − Control)', fontsize=12, fontweight='bold')

  maybe_plot_seed_star(ax, data_crs)

  # Check result
  if np.max(np.abs(t_diff)) < 1e-6:
      result = "✅ PASS: Timestep 0 is IDENTICAL (as expected)"
      color = 'green'
  else:
      result = f"❌ FAIL: Timestep 0 has {np.sum(np.abs(t_diff) > 1e-6)} different points!"
      color = 'red'

  ax.set_title(f'Timestep 0 (t=-6hr, Historical) Temperature Difference at 700 hPa\n' +
               f'Max |Δ|: {np.max(np.abs(t_diff)):.10f} K\n{result}',
               fontsize=13, fontweight='bold', color=color)

  plt.tight_layout()
  plt.show()

  print("\n" + "=" * 80)
  if np.max(np.abs(t_diff)) < 1e-6:
      print("✅ SUCCESS: Timestep 0 is unchanged!")
      print("   The historical reference is identical between control and seeded.")
      print("   This is correct - we should only perturb timestep 1.")
  else:
      print(f"❌ PROBLEM: Timestep 0 has {np.sum(np.abs(t_diff) > 1e-6)} points that differ!")
      print("   The bug is still present - check that you removed all [:, 0, ...] assignments")
  print("=" * 80)
