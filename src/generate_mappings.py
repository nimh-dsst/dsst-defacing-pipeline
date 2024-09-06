#!/usr/local/bin/python3
"""Generates Primary to "others" mapping file and prints VisualQC's T1 MRI utility command.

    Terminology
    -----------
    "primary scan" : Best quality T1w scan, ideally. If T1s not available, we'll need another strategy to pick a primary scan.
    "other scans" : Apart from the primary scan, every "other" scan within the subject-session anat directory is considered a secondary or "other" scan.

    References
    ----------
    visualqc T1 MRI utility : https://raamana.github.io/visualqc/cli_t1_mri.html
"""

import json
import random
from collections import defaultdict
from pathlib import Path


def sort_by_acq_time(sidecars, logger):
    """Sorting a list of scans' JSON sidecars based on their acquisition time.

    :param list sidecars: A list of JSON sidecars for all T1w scans in within a session.
    :return list acq_time_sorted_list: A list of JSON sidecar file paths sorted by acquisition time in descending order.
    """
    sidecar_acq_time_map = dict()
    acq_time_keys = ["AcquisitionTime", "AcquisitionDateTime"]
    for sidecar in sidecars:
        with open(sidecar, 'r') as f:
            data = json.load(f)
            for key in acq_time_keys:
                if key in data.keys():
                    sidecar_acq_time_map[sidecar] = data[key]
    sorted_map = sorted(sidecar_acq_time_map.items(), key=lambda key_val_tup: key_val_tup[1], reverse=True)

    if sorted_map:
        reordered_sidecars = [tup[0] for tup in sorted_map]
    else:
        logger.info(
            f"'AcquisitionTime' or 'AcquisitionDateTime' field was not found in the following sidecar files:\n"
            f"{'\n'.join([str(s) for s in sidecars])}. Picking a primary scan arbitrarily.")
        random.shuffle(sidecars)  # shuffles the list in place
        reordered_sidecars = sidecars

    return reordered_sidecars


def get_anat_dir_paths(subj_path, logger):
    """Given subject directory path finds all anat directories in subject directory tree.

    :param Path subj_path : Absolute path to subject directory.
    :param logger: Logger object imported from main.py module.
    :return: A list of absolute paths to anat directory(s) within subject tree.
    """

    sess_paths = list(subj_path.glob('ses-*'))  # check if subject has 'ses' directories
    sess_exist = True if sess_paths else False

    anat_dirs = []
    if not sess_exist:
        anat_dir = subj_path / 'anat'
        if anat_dir.exists():
            anat_dirs.append(anat_dir)
        else:
            logger.info(f"No 'anat' directory found in {subj_path}.")
    else:
        for sess_path in sess_paths:
            anat_dir = sess_path / 'anat'
            if anat_dir.exists():
                anat_dirs.append(anat_dir)
            else:
                logger.info(f"No 'anat' directory found in {sess_path}.")

    return anat_dirs, sess_exist


def update_mapping_dict(mapping_dict, anat_dir, sess_exist, t1_sidecars, logger):
    """Updates mapping dictionary for a given subject's or session's anatomical directory.

    :param defaultdict mapping_dict: A dictionary with primary to others mapping information.
    :param Path anat_dir: Absolute path to subject's or session's anatomical directory.
    :param boolean sess_exist: True if subject has 'ses' directories, else False.
    :param list t1_sidecars:Absolute paths to T1w JSON sidecars.
    :param logger: Logger object imported from main.py module.
    :return defaultdict mapping_dict: An updated dictionary with primary to others mapping information.
    """
    # sort and separate primary and other scans
    if t1_sidecars:
        reordered_sidecars = sort_by_acq_time(t1_sidecars, logger)

        latest_sidecar = reordered_sidecars[0]  # latest T1w based on acquisition time
        nifti_name = latest_sidecar.name.split('.')[0] + '.nii.gz'
        nifti_path = latest_sidecar.parent / nifti_name
        if not nifti_path.exists():
            nifti_path = nifti_path.parent / reordered_sidecars[0].name.split('.')[0] + '.nii'
            if not nifti_path.exists():
                logger.error(f"No associated '.nii.gz' or '.nii' file found for {latest_sidecar}.")
                raise FileNotFoundError(f"Please ensure a nifti file corresponding to {latest_sidecar} is available.")

        primary_t1 = nifti_path
        others = [str(s) for s in list(anat_dir.glob('*.nii*')) if s != primary_t1]
    else:
        primary_t1 = ""
        others = [str(s) for s in list(anat_dir.glob('*.nii*'))]

    # updating mapping dict
    subj_id = [p for p in anat_dir.parts if p.startswith('sub-')][0]
    if sess_exist:
        sess_id = anat_dir.parent.name
        mapping_dict[subj_id][sess_id] = {
            'primary_t1': str(primary_t1),
            'others': others
        }
    else:
        mapping_dict[subj_id] = {
            'primary_t1': str(primary_t1),
            'others': others
        }

    return mapping_dict


def crawl(input_dir, output_dir, logger):
    """Crawls through the BIDS dataset and generates a mapping file for primary to other T1w scans."""
    logger.info("Generating mapping file for primary (latest T1w in session) to other scans.")

    # make dir for log files and visualqc prep
    dir_names = ['logs', 'QC']
    for dir_name in dir_names:
        output_dir.joinpath(dir_name).mkdir(parents=True, exist_ok=True)

    mapping_dict = defaultdict(dict)
    subj_dirs = list(input_dir.glob('sub-*'))
    if not subj_dirs:
        logger.exception(f"No subject directories found in {input_dir}.")
        raise FileNotFoundError(
            f"Please verify the input directory contains at least one subject with anatomical scans.")
    for subj_dir in subj_dirs:
        anat_dirs, sess_exist = get_anat_dir_paths(subj_dir, logger)
        for anat_dir in anat_dirs:
            t1_sidecars = list(anat_dir.glob('*T1w.json'))
            mapping_dict = update_mapping_dict(mapping_dict, anat_dir, sess_exist, t1_sidecars, logger)

    # write mapping dict to file
    with open(output_dir / 'primary_to_others_mapping.json', 'w') as f1:
        json.dump(mapping_dict, f1, indent=4)

    return mapping_dict
