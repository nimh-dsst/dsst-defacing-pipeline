#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path
import time
import shutil
import json
import os
import filecmp


def get_args():
    parser = argparse.ArgumentParser(
        description='Prepare the defaced BIDS formatted output dataset to be shared publicly.')

    parser.add_argument('original_bids_dir', type=Path,
                        help='The directory with the input dataset '
                             'formatted according to the BIDS standard containing non-defaced anatomical images.')
    parser.add_argument('defaced_bids_dir', type=Path,
                        help='The directory with the output dataset '
                             'formatted according to the BIDS standard containing defaced anatomical images.')

    return parser.parse_args()


def run_command(cmdstr, logfile):
    if not logfile:
        logfile = subprocess.PIPE
    subprocess.run(cmdstr, stdout=logfile, stderr=subprocess.STDOUT, encoding='utf8', shell=True)


def scrub_identifiers(bids_defaced_dir):
    sidecar_fields_to_rm = ['AcquisitionDateTime', 'AcquisitionTime']
    sidecars = bids_defaced_dir.rglob('*.json')
    for sidecar in sidecars:
        with open(sidecar, 'r') as f:
            data = json.load(f)

        for field in sidecar_fields_to_rm:
            if field in data.keys():
                del data[field]

        with open(sidecar, 'w') as f:
            json.dump(data, f, indent=4)


def main():
    args = get_args()
    bids_dir = args.bids_dir
    bids_defaced_dir = args.output_dir

    # copy over all non-anat subdirectories in original BIDS tree
    bids_subdirs = [Path(x_walk_tuple[0]).relative_to(bids_dir) for x_walk_tuple in os.walk(bids_dir)]
    bids_defaced_subdirs = [Path(y_walk_tuple[0]).relative_to(bids_defaced_dir)
                            for y_walk_tuple in os.walk(bids_defaced_dir)]
    diff_subdirs = set(bids_subdirs).difference(bids_defaced_subdirs)
    for subdir in diff_subdirs:
        shutil.copytree(bids_dir / subdir, bids_defaced_dir / subdir)

    # remove JSON sidecar fields with identifying information
    scrub_identifiers(bids_defaced_dir)

    # remove defacing pipeline log files
    logfiles = bids_defaced_dir.rglob('defacing_pipeline.log')
    for logfile in logfiles:
        logfile.unlink(missing_ok=True)

    # copy over top-level (modality agnostic) files from original BIDS tree
    dcmp = filecmp.dircmp(bids_dir, bids_defaced_dir)
    for toplevel_file in dcmp.left_only:
        shutil.copy2(bids_dir / toplevel_file, bids_defaced_dir / toplevel_file)


if __name__ == "__main__":
    start_time = time.time()
    main()
    print("\n--- %s seconds ---" % (time.time() - start_time))

