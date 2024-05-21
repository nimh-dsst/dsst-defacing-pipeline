#!/usr/bin/env python3
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
import subprocess
from collections import defaultdict
from pathlib import Path


def run_command(cmdstr, logfile):
    """Runs the given command str as shell subprocess. If logfile object is provided, then the stdout and stderr of the
    subprocess is written to the log file.

    :param str cmdstr: A shell command formatted as a string variable.
    :param io.TextIOWrapper logfile: optional, File object to log the stdout and stderr of the subprocess.
    """
    if not logfile:
        logfile = subprocess.PIPE
    subprocess.run(cmdstr, stdout=logfile, stderr=subprocess.STDOUT, encoding='utf8', shell=True)


def sort_by_acq_time(sidecars):
    """Sorting a list of scans' JSON sidecars based on their acquisition time.

    :param list sidecars: A list of JSON sidecars for all T1w scans in within a session.
    :return list acq_time_sorted_list: A list of JSON sidecar file paths sorted by acquisition time in descending order.
    """
    acq_time_dict = dict()
    acq_time_field_vars = ["AcquisitionTime", "AcquisitionDateTime"]
    for sidecar in sidecars:
        with open(sidecar, 'r') as f:
            data = json.load(f)
            for field in acq_time_field_vars:
                if field in data.keys():
                    acq_time_dict[sidecar] = data[field]
    acq_time_sorted_dict_list = sorted(acq_time_dict.items(), key=lambda key_val_tup: key_val_tup[1], reverse=True)

    if acq_time_sorted_dict_list != []:
        acq_time_sorted_list = [tup[0] for tup in acq_time_sorted_dict_list]
    else:
        newline_sidecars = '\n'.join(
            [str(s) for s in sidecars])  # need this since f-string expression part cannot include a backslash
        print(
            f"'AcquisitionTime' or 'AcquisitionDateTime' field was not found in the following sidecar files:\n"
            f"{newline_sidecars}. Picking a primary scan arbitrarily.")
        random.shuffle(sidecars)  # shuffles the list in place
        acq_time_sorted_list = sidecars

    return acq_time_sorted_list


def get_anat_dir_paths(subj_dir_path):
    """Given subject directory path, finds all anat directories in subject directory tree.

    :param Path subj_dir_path : Absolute path to subject directory.
    :return: A list of absolute paths to anat directory(s) within subject tree.
    """

    # check if there are session directories
    sessions = list(subj_dir_path.glob('ses-*'))
    sess_exist = True if sessions else False

    no_anat_dirs = []
    anat_dirs = []
    if not sess_exist:
        anat_dir = subj_dir_path / 'anat'
        if not anat_dir.exists():
            no_anat_dirs.append(subj_dir_path)
        else:
            anat_dirs.append(anat_dir)
    else:
        for sess in sessions:
            anat_dir = sess / 'anat'
            if not anat_dir.exists():
                no_anat_dirs.append(sess)
            else:
                anat_dirs.append(anat_dir)

    return anat_dirs, no_anat_dirs, sess_exist


def update_mapping_dict(mapping_dict, anat_dir, is_sessions, sidecars, t1_unavailable, t1_available):
    """Updates mapping dictionary for a given subject's or session's anatomical directory.

    :param defaultdict mapping_dict: A dictionary with primary to others mapping information.
    :param Path anat_dir: Absolute path to subject's or session's anatomical directory.
    :param boolean is_sessions: True if subject/session has 'ses' directories, else False.
    :param list sidecars: Absolute paths to T1w JSON sidecars.
    :param list t1_unavailable: Subject/session directory paths that don't have a T1w scan.

    :return defaultdict mapping_dict: An updated dictionary with primary to others mapping information.
    :return list t1_unavailable: An updated list of subject/session directory paths that don't have a T1w scan.
    """

    subjid = [p for p in anat_dir.parts if p.startswith('sub-')][0]

    if sidecars:
        t1_acq_time_list = sort_by_acq_time(sidecars)

        # latest T1w scan in the session based on acquisition time
        nifti_fname = t1_acq_time_list[0].name.split('.')[0] + '.nii.gz'

        primary_t1 = t1_acq_time_list[0].parent / nifti_fname
        others = [str(s) for s in list(anat_dir.glob('*.nii*')) if s != primary_t1]
        t1_available.append(anat_dir.parent)
    else:
        primary_t1 = ""
        others = [str(s) for s in list(anat_dir.glob('*.nii*'))]
        t1_unavailable.append(anat_dir.parent)

    # updating mapping dict
    if is_sessions:
        if subjid not in mapping_dict:
            mapping_dict[subjid] = {}

        sessid = anat_dir.parent.name
        if sessid not in mapping_dict[subjid]:
            mapping_dict[subjid][sessid] = {
                'primary_t1': str(primary_t1),
                'others': others
            }

        else:
            mapping_dict[subjid][sessid] = {
                'primary_t1': str(primary_t1),
                'others': others
            }

    else:
        mapping_dict[subjid] = {
            'primary_t1': str(primary_t1),
            'others': others
        }

    return mapping_dict, t1_unavailable, t1_available


def summary_to_stdout(sess_ct, t1s_found, t1s_not_found, output):
    readable_path_list = ['/'.join([path.parent.name, path.name]) for path in t1s_not_found]
    print(f"====================")
    print(f"Dataset Summary")
    print(f"====================")
    print(f"Total number of sessions with 'anat' directory in the dataset: {sess_ct}")
    print(f"Sessions with 'anat' directory with at least one T1w scan: {len(t1s_found)}\n")
    if len(t1s_not_found) != 0:  # don't print the following if it's not helpful to the user
        print(f"Sessions without a T1w scan: {len(t1s_not_found)}")
        print(f"List of sessions without a T1w scan:\n {readable_path_list}")
    print(
        f"\nPlease find the mapping file in JSON format at {str(output / 'primary_to_others_mapping.json')} \nand other helpful logs at {str(output / 'logs')}\n")


def crawl(input_dir, output):
    # make dir for log files and visualqc prep
    dir_names = ['logs', 'defacing_QC']
    for dir_name in dir_names:
        output.joinpath(dir_name).mkdir(parents=True, exist_ok=True)

    t1s_not_found = []
    t1s_found = []
    total_sessions = 0

    # mapping_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    mapping_dict = {}

    for subj_dir in list(input_dir.glob('sub-*')):
        # subj_id = subj_dir.name
        anat_dirs, no_anat_dirs, sess_exist = get_anat_dir_paths(subj_dir)
        for anat_dir in anat_dirs:
            total_sessions += 1
            t1_sidecars = list(anat_dir.glob('*T1w.json'))
            mapping_dict, t1s_not_found, t1s_found = update_mapping_dict(mapping_dict, anat_dir, sess_exist,
                                                                         t1_sidecars, t1s_not_found, t1s_found)

    # write mapping dict to file
    with open(output / 'primary_to_others_mapping.json', 'w') as f1:
        json.dump(mapping_dict, f1, indent=4)

    # write session paths without T1w scan to file
    with open(output / 'logs' / 't1_unavailable.txt', 'w') as f2:
        f2.write('\n'.join([str(sess_path) for sess_path in t1s_not_found]))

    with open(output / 'logs' / 'anat_unavailable.txt', 'w') as f3:
        f3.write('\n'.join([str(p) for p in no_anat_dirs]))

    summary_to_stdout(total_sessions, t1s_found, t1s_not_found, output)
    return mapping_dict
