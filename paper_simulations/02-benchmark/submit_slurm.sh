#!/bin/bash

#SBATCH --job-name="HG-Test-Set"
#SBATCH --partition=CLUSTER
#SBATCH --ntasks=1
#SBATCH --mem=10G
#SBATCH -t 900:00:00
#SBATCH --nodelist=compute-1-4

Folder=$(pwd)

ssh -tt cluster2 <<EOF
source ~/.bashrc

conda activate forcebalance

export OE_LICENSE=/gpfs/jsetiadi/oe_license.txt
cd ${Folder}/

# Start the estimation server.
python evaluator-hg.py ${Folder} &> server_console_output.log

exit
EOF

exit
