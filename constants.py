from pathlib import Path

# BIDS input directory
BIDS_DIR = Path('/data/BrainBlocks/joyce/bids')

# Output directory, not sure whether or not it needs to exist
OUTPUTS_DIR = Path('/data/NIMH_scratch/hv_protocol/defacing_comparisons/new_algorithm_v2')

# Optional BIDS acquisition labels list
REQ_ACQS = ['acq-mprage', 'acq-fspgr']

# The thing that collects your T1w's
T1W_SCANS = [s for s in list(BIDS_DIR.glob('sub-*/ses-*/anat/*run-01*T1w.nii.gz')) if s.name.split('_')[2] in REQ_ACQS]
