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

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description=__doc__)

    parser.add_argument('-i', '--input', type=Path, action='store', dest='inputdir', metavar='INPUT_DIR',
                        help='Path to input BIDS directory.')
    parser.add_argument('-o', '--output', type=Path, action='store', dest='outdir', metavar='SCRIPT_OUTPUT_DIR',
                        default=Path('.'), help="Path to directory that'll contain this script's outputs.")
    args = parser.parse_args()

    return args.inputdir.resolve(), args.outdir.resolve()


def run(cmdstr, logfile):
    """Runs the given command str as shell subprocess. If logfile object is provided, then the stdout and stderr of the
    subprocess is written to the log file.

    :param str cmdstr: A shell command formatted as a string variable.
    :param io.TextIOWrapper logfile: optional, File object to log the stdout and stderr of the subprocess.
    """
    if not logfile:
        subprocess.run(cmdstr, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8', shell=True)
    else:
        subprocess.run(cmdstr, stdout=logfile, stderr=subprocess.STDOUT, encoding='utf8', shell=True)


def primary_scans_qc_prep(mapping_dict, outdir):
    """Prepares a directory tree with symbolic links to primary scans and an id_list of primary scans to be used in the
    visualqc_t1_mri command.

    :param defaultdict mapping_dict: A dictionary mapping each subject's and session's primary and other scans.
    :param Path() outdir: Path to output directory provided by the user. The output directory contains this scripts output files and
        directories.
    :return str vqc_t1_mri_cmd: A visualqc T1 MRI command string.
    """

    interested_keys = ['primary_t1', 'others']
    primaries = []
    for subjid in mapping_dict.keys():

        # check existence of sessions to query mapping dict
        if mapping_dict[subjid].keys() != interested_keys:
            for sessid in mapping_dict[subjid].keys():
                primary = mapping_dict[subjid][sessid]['primary_t1']
                primaries.append(primary)
        else:
            primary = mapping_dict[subjid]['primary_t1']
            primaries.append(primary)
        # remove empty strings from primaries list
        primaries = [p for p in primaries if p != '']

    vqc_inputs = outdir.joinpath('visualqc_prep/t1_mri')
    if not vqc_inputs.exists:
        vqc_inputs.mkdir(parents=True)

    id_list = []
    for primary in primaries:
        entities = Path(primary).name.split('_')
        subjid = entities[0]

        # check existence of session to construct destination path
        sessid = [e for e in entities if e.startswith('ses')][0]
        if sessid:
            dest = vqc_inputs.joinpath(subjid, sessid, 'anat')
        else:
            dest = vqc_inputs.joinpath(subjid, 'anat')
        if not dest.exists(): dest.mkdir(parents=True)

        id_list.append(dest)
        ln_cmd = f"ln -s {primary} {dest.joinpath('primary.nii.gz')}"
        run(ln_cmd, "")

    with open(outdir.joinpath('visualqc_prep/id_list_t1.txt'), 'w') as f:
        for i in id_list:
            f.write(str(i) + '\n')

    vqc_t1_mri_cmd = f"visualqc_t1_mri -u {vqc_inputs} -i {vqc_inputs.parent.joinpath('id_list_t1.txt')} -m primary.nii.gz"

    return vqc_t1_mri_cmd


def sort_by_acq_time(sidecars):
    """Sorting a list of scans' JSON sidecars based on their acquisition time.

    :param list sidecars: A list of JSON sidecars for all T1w scans in within a session.
    :return list acq_time_sorted_list: A list of JSON sidecar file paths sorted by acquisition time in descending order.
    """
    acq_time_dict = dict()
    for sidecar in sidecars:
        sidecar_fobj = open(sidecar, 'r')
        data = json.load(sidecar_fobj)
        acq_time_dict[sidecar] = data["AcquisitionTime"]

    acq_time_sorted_list = sorted(acq_time_dict.items(), key=lambda key_val_tup: key_val_tup[1], reverse=True)
    return acq_time_sorted_list


def get_anat_dir_paths(subj_dir_path):
    """Given subject directory path, finds all anat directories in subject directory tree.

    :param Path subj_dir_path : Absolute path to subject directory.
    :return: A list of absolute paths to anat directory(s) within subject tree.
    """
    anat_dirs = []
    no_anat_dirs = []

    # check if there are session directories
    # sess_exist, sessions = is_sessions(subj_dir_path)
    sessions = list(subj_dir_path.glob('ses-*'))
    sess_exist = True if sessions else False

    if not sess_exist:
        anat_dir = subj_dir_path.joinpath('anat')
        if not anat_dir.exists():
            # print(f'No anat directories found for {subj_dir_path.name}.\n')
            no_anat_dirs.append(subj_dir_path)
        else:
            anat_dirs.append(anat_dir)
    else:
        for sess in sessions:
            anat_dir = sess.joinpath('anat')
            if not anat_dir.exists():
                # print(f'No anat directories found for {subj_dir_path.name} and {sess.name}.\n')
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
        nifti_fname = t1_acq_time_list[0][0].name.split('.')[0] + '.nii.gz'

        primary_t1 = t1_acq_time_list[0][0].parent.joinpath(nifti_fname)
        others = [str(s) for s in list(anat_dir.glob('*.nii*')) if s != primary_t1]
        t1_available.append(anat_dir.parent)
    else:
        primary_t1 = ""
        others = [str(s) for s in list(anat_dir.glob('*.nii*'))]
        t1_unavailable.append(anat_dir.parent)

    # updating mapping dict
    if is_sessions:
        sessid = anat_dir.parent.name
        mapping_dict[subjid][sessid]['primary_t1'] = str(primary_t1)
        mapping_dict[subjid][sessid]['others'] = others
    else:
        mapping_dict[subjid]['primary_t1'] = str(primary_t1)
        mapping_dict[subjid]['others'] = others

    return mapping_dict, t1_unavailable, t1_available


def summary_to_stdout(vqc_t1_cmd, sess_ct, t1s_found, t1s_not_found, no_anat_dirs, output):
    readable_path_list = ['/'.join([path.parent.name, path.name]) for path in t1s_not_found]
    print(f"====================")
    print(f"Dataset Summary")
    print(f"====================")
    print(f"Total number of sessions with 'anat' directory in the dataset: {sess_ct}")
    print(f"Sessions with 'anat' directory with at least one T1w scan: {len(t1s_found)}")
    print(f"Sessions without a T1w scan: {len(t1s_not_found)}")
    print(f"List of sessions without a T1w scan:\n {readable_path_list}\n")
    print(f"Please find the mapping file in JSON format and other helpful logs at {str(output)}\n")


def main():
    input, output = get_args()

    # input_layout = bids.BIDSLayout(input) # taking insane amounts of time so not using pybids
    t1s_not_found = []
    t1s_found = []
    total_sessions = 0

    mapping_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for subj_dir in list(input.glob('sub-*')):
        anat_dirs, no_anat_dirs, sess_exist = get_anat_dir_paths(subj_dir)
        for anat_dir in anat_dirs:
            total_sessions += 1
            t1_sidecars = list(anat_dir.glob('*T1w.json'))
            mapping_dict, t1s_not_found, t1s_found = update_mapping_dict(mapping_dict, anat_dir, sess_exist,
                                                                         t1_sidecars, t1s_not_found, t1s_found)

    # write mapping dict to file
    with open(output.joinpath('primary_to_others_mapping.json'), 'w') as f1:
        json.dump(mapping_dict, f1, indent=4)

    # write session paths without T1w scan to file
    with open(output.joinpath('t1_unavailable.txt'), 'w') as f2:
        for sess_path in t1s_not_found:
            f2.write(str(sess_path) + '\n')

    # write vqc command to file
    vqc_t1_mri_cmd = primary_scans_qc_prep(mapping_dict, output)
    with open(output.joinpath('visualqc_t1_mri_cmd'), 'w') as f3:
        f3.write(f"{vqc_t1_mri_cmd}\n")

    with open(output.joinpath('anat_unavailable.txt'), 'w') as f4:
        for p in no_anat_dirs:
            f4.write(str(p) + '\n')

    summary_to_stdout(vqc_t1_mri_cmd, total_sessions, t1s_found, t1s_not_found, no_anat_dirs, output)


if __name__ == "__main__":
    main()
