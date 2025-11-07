# Get metadata
lat_vals = _to_np(batch_control.metadata.lat)
lon_vals = _to_np(batch_control.metadata.lon)
levels = _to_np(batch_control.metadata.atmos_levels)
lat_len, lon_len = len(lat_vals), len(lon_vals)

# First, inspect the actual shapes
print("\n📐 Data shapes:")
t_ctrl = _to_np(batch_control.atmos_vars["t"])
t_seed = _to_np(batch_seeded.atmos_vars["t"])
print(f"Temperature shape: {t_ctrl.shape}")

q_ctrl = _to_np(batch_control.atmos_vars["q"])
q_seed = _to_np(batch_seeded.atmos_vars["q"])
print(f"Humidity shape: {q_ctrl.shape}")

u_ctrl = _to_np(batch_control.atmos_vars["u"])
print(f"Wind shape: {u_ctrl.shape}")

print(f"Number of pressure levels: {len(levels)}")
print(f"Lat x Lon: {lat_len} x {lon_len}")

# Find which axis is the level axis
lev_len = int(levels.size)
lev_axis = None
for axis_idx, size in enumerate(t_ctrl.shape):
    if size == lev_len:
        lev_axis = axis_idx
        print(f"Level axis is axis {lev_axis} (size {size})")
        break

if lev_axis is None:
    print("⚠️  Could not find level axis, skipping per-level analysis")
    # Just do overall comparison
    t_diff = t_seed - t_ctrl
    q_diff = q_seed - q_ctrl

    print(f"\nOverall temperature difference:")
    print(f"  Max |Δ|: {np.max(np.abs(t_diff)):.6f} K")
    print(f"  Points with |Δ| > 1e-6: {np.sum(np.abs(t_diff) > 1e-6)}")

    print(f"\nOverall humidity difference:")
    print(f"  Max |Δ|: {np.max(np.abs(q_diff)):.9f} kg/kg")
    print(f"  Points with |Δ| > 1e-9: {np.sum(np.abs(q_diff) > 1e-9)}")

else:
    # Check temperature at each pressure level
    print("\n📊 Temperature differences by pressure level:")
    for i in range(len(levels)):
        t_ctrl_level = np.take(t_ctrl, i, axis=lev_axis)
        t_seed_level = np.take(t_seed, i, axis=lev_axis)

        t_ctrl_level = _coerce_latlon(t_ctrl_level, lat_len, lon_len)
        t_seed_level = _coerce_latlon(t_seed_level, lat_len, lon_len)

        diff = t_seed_level - t_ctrl_level

        num_diff = np.sum(np.abs(diff) > 1e-6)  # Count non-zero differences
        max_diff = np.max(np.abs(diff))

        if num_diff > 0:
            print(f"  {int(levels[i]):4d} hPa: {num_diff:6d} points differ | Max |Δ|: {max_diff:.6f} K")
        else:
            print(f"  {int(levels[i]):4d} hPa: No differences")

    # Check humidity
    print("\n💧 Humidity differences by pressure level:")
    for i in range(len(levels)):
        q_ctrl_level = np.take(q_ctrl, i, axis=lev_axis)
        q_seed_level = np.take(q_seed, i, axis=lev_axis)

        q_ctrl_level = _coerce_latlon(q_ctrl_level, lat_len, lon_len)
        q_seed_level = _coerce_latlon(q_seed_level, lat_len, lon_len)

        diff = q_seed_level - q_ctrl_level

        num_diff = np.sum(np.abs(diff) > 1e-9)
        max_diff = np.max(np.abs(diff))

        if num_diff > 0:
            print(f"  {int(levels[i]):4d} hPa: {num_diff:6d} points differ | Max |Δ|: {max_diff:.9f} kg/kg")
        else:
            print(f"  {int(levels[i]):4d} hPa: No differences")
