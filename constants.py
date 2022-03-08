from pathlib import Path

BIDS_DIR = Path('/data/BrainBlocks/joyce/bids')
OUTPUTS_DIR = Path('/data/NIMH_scratch/hv_protocol/defacing_comparisons/new_algorithm')
T1W_SCANS = list(BIDS_DIR.glob('sub-*/ses-*/anat/*run-01*T1w.nii.gz'))
