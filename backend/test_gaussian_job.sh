#!/bin/bash
#SBATCH --job-name=gaussian_job
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=24:00:00
#SBATCH --output=gaussian_job.out
#SBATCH --error=gaussian_job.err
cd $SLURM_SUBMIT_DIR

# 加载模块
# Gaussian 模块
module load gaussian  # 根据实际环境调整

# 设置 Gaussian 环境变量
export GAUSSIAN_CPUS=8
export GAUSSIAN_MEM=16384MB

# 运行 Gaussian
g16 < test.com