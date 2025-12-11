#!/usr/bin/env python3
"""
Create GIF Animations from Field Analysis Plots

This script creates animated GIFs from the field analysis timestep plots,
showing the evolution of atmospheric fields over the forecast period.

Creates 5 GIFs:
- msl_evolution.gif     - Mean sea level pressure evolution
- z500_evolution.gif    - 500 hPa geopotential height evolution
- t700_evolution.gif    - 700 hPa temperature evolution
- rh850_evolution.gif   - 850 hPa relative humidity evolution
- wind250_evolution.gif - 250 hPa wind speed evolution (upper-level jet)

Each GIF shows all timesteps (000-027) as frames.

Author: Field Evolution Visualization
Date: 2025-12-02
"""

import sys
from pathlib import Path
from PIL import Image
import numpy as np

print("=" * 80)
print("  Creating Field Evolution GIFs")
print("=" * 80)
print()

# =========================================================================
# CONFIGURATION
# =========================================================================
field_analysis_dir = Path("/scratch/qhuang62/control_AR_FZ_TC/sandy_ftle_test_output/field_analysis")
output_dir = field_analysis_dir  # Save GIFs in same directory

if not field_analysis_dir.exists():
    print(f"❌ Field analysis directory not found: {field_analysis_dir}")
    print("   Run analyze_sandy_perturbation_fields.py first!")
    sys.exit(1)

print(f"Input directory: {field_analysis_dir}")
print(f"Output directory: {output_dir}")
print()

# =========================================================================
# FIELD DEFINITIONS
# =========================================================================
fields = {
    'msl': {
        'pattern': 'msl_t*.png',
        'output': 'msl_evolution.gif',
        'description': 'Mean Sea Level Pressure'
    },
    'z500': {
        'pattern': 'z500_t*.png',
        'output': 'z500_evolution.gif',
        'description': '500 hPa Geopotential Height'
    },
    't700': {
        'pattern': 't700_t*.png',
        'output': 't700_evolution.gif',
        'description': '700 hPa Temperature'
    },
    'rh850': {
        'pattern': 'rh850_t*.png',
        'output': 'rh850_evolution.gif',
        'description': '850 hPa Relative Humidity'
    },
    'wind250': {
        'pattern': 'wind250_t*.png',
        'output': 'wind250_evolution.gif',
        'description': '250 hPa Wind Speed (Upper-Level Jet)'
    }
}

# GIF parameters
fps = 2  # Frames per second (2 fps = 0.5s per frame)
duration_ms = int(1000 / fps)  # Duration per frame in milliseconds
loop = 0  # 0 = infinite loop

print(f"GIF settings:")
print(f"  Frame rate: {fps} fps")
print(f"  Frame duration: {duration_ms} ms")
print(f"  Loop: {'infinite' if loop == 0 else f'{loop} times'}")
print()

# =========================================================================
# CREATE GIFs
# =========================================================================

def create_gif_from_pattern(field_dir, pattern, output_path, description):
    """Create a GIF from PNG files matching a pattern."""

    # Find all matching files and sort them numerically by timestep
    png_files = sorted(field_dir.glob(pattern))

    if not png_files:
        print(f"  ⚠️  No files found for pattern: {pattern}")
        return False

    # Extract timestep numbers and sort
    def extract_timestep(filepath):
        """Extract timestep number from filename like 'msl_t027.png'"""
        stem = filepath.stem  # 'msl_t027'
        timestep_str = stem.split('_t')[-1]  # '027'
        return int(timestep_str)

    png_files = sorted(png_files, key=extract_timestep)

    print(f"  Found {len(png_files)} frames (t{extract_timestep(png_files[0]):03d} to t{extract_timestep(png_files[-1]):03d})")

    # Load all images
    images = []
    for png_file in png_files:
        try:
            img = Image.open(png_file)
            images.append(img.copy())  # Copy to avoid file handle issues
            img.close()
        except Exception as e:
            print(f"  ⚠️  Error loading {png_file.name}: {e}")
            continue

    if not images:
        print(f"  ❌ No valid images found")
        return False

    # Save as GIF
    try:
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=loop,
            optimize=False  # Disable optimization for faster creation
        )

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ Created: {output_path.name} ({file_size_mb:.1f} MB)")
        return True

    except Exception as e:
        print(f"  ❌ Error creating GIF: {e}")
        return False

# Create GIF for each field
print("Creating GIFs...")
print()

success_count = 0
for field_name, field_info in fields.items():
    print(f"{field_info['description']}:")

    output_path = output_dir / field_info['output']

    if create_gif_from_pattern(
        field_analysis_dir,
        field_info['pattern'],
        output_path,
        field_info['description']
    ):
        success_count += 1

    print()

# =========================================================================
# SUMMARY
# =========================================================================
print("=" * 80)
print(f"  ✓ GIF Creation Complete! ({success_count}/{len(fields)} successful)")
print("=" * 80)
print()
print(f"Output directory: {output_dir}")
print()
print("Created GIFs:")
for field_name, field_info in fields.items():
    output_path = output_dir / field_info['output']
    if output_path.exists():
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ {field_info['output']:25s} - {field_info['description']} ({file_size_mb:.1f} MB)")
    else:
        print(f"  ✗ {field_info['output']:25s} - Not created")
print()
print("Viewing tips:")
print("  - Each frame = 6 hours of forecast")
print("  - Watch for spatial patterns in difference panels")
print("  - Look for Rossby wave propagation in Z500")
print("  - Track diabatic heating evolution in T700")
print("  - Monitor moisture redistribution in RH850")
print("  - Check jet stream perturbations in WIND250 (Weather Jiu-Jitsu?)")
print("  - Identify when perturbation effects become visible")
print()
