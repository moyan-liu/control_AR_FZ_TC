#!/bin/bash
#SBATCH --job-name=sandy_ftle_ortho
#SBATCH --output=slurm_logs/ftle_ortho_%j.out
#SBATCH --error=slurm_logs/ftle_ortho_%j.err
#SBATCH --time=02:00:00
#SBATCH --partition=public
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G

# Load required modules (if needed)
module load gcc-11.2.0-gcc-8.5.0
module load cuda-11.8.0-gcc-11.2.0

cd /scratch/qhuang62/control_AR_FZ_TC

# Create slurm_logs directory if it doesn't exist
mkdir -p slurm_logs

echo "========================================"
echo "Starting FTLE Orthographic Projection"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $HOSTNAME"
echo "Started at: $(date)"
echo "========================================"
echo ""

# Run the FTLE calculation and orthographic projection plot
echo "Running FTLE calculation (global Northern Hemisphere)..."
python plot_ftle_orthographic_only.py

echo ""
echo "========================================"
echo "Job completed at: $(date)"
echo "========================================"
