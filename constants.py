from pathlib import Path

BIDS_DIR = Path('/data/BrainBlocks/joyce/bids')
OUTPUTS_DIR = Path('/data/NIMH_scratch/hv_protocol/defacing_comparisons/new_algorithm_v2')
REQ_ACQS = ['acq-mprage', 'acq-fspgr']
T1W_SCANS = [s for s in list(BIDS_DIR.glob('sub-*/ses-*/anat/*run-01*T1w.nii.gz')) if s.name.split('_')[2] in REQ_ACQS]
