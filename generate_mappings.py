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
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('-i', '--input', type=Path, action='store', dest='inputdir',
                        help='Path to input BIDS directory.')
    parser.add_argument('-o', '--output', type=Path, action='store', dest='outdir',
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

    primaries = [mapping_dict[subj_sess]['primary_t1'] for subj_sess in mapping_dict.keys() if
                 mapping_dict[subj_sess]['primary_t1'] != ""]

    vqc_inputs = outdir.joinpath('visualqc_prep/t1_mri')
    if not vqc_inputs.exists:
        vqc_inputs.mkdir(parents=True)

    id_list = []
    for primary in primaries:
        entities = Path(primary).name.split('_')
        subjid = entities[0]
        sessid = entities[1]
        dest = vqc_inputs.joinpath(subjid, sessid, 'anat')
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

        acq_time_sorted_list = sorted(acq_time_dict.items(), key=lambda key_val_tup: key_val_tup[1],
                                      reverse=True)
        return acq_time_sorted_list


def main():
    input, output = get_args()
    t1w_scan_not_found = []
    mapping_dict = defaultdict(lambda: defaultdict(list))

    for subj_dir in list(input.glob('sub-*')):
        subjid = subj_dir.name
        subj_sess_paths = list(subj_dir.glob('ses-*'))
        for subj_sess_path in subj_sess_paths:
            t1_sidecars = list(subj_sess_path.glob('anat/*T1w.json'))
            if t1_sidecars:
                t1_acq_time_list = sort_by_acq_time(t1_sidecars)

                # latest T1w scan in the session based on acquisition time
                nifti_fname = t1_acq_time_list[0][0].name.split('.')[0] + '.nii.gz'

                primary_t1 = t1_acq_time_list[0][0].parent.joinpath(nifti_fname)
                others = [str(s) for s in list(subj_sess_path.glob('anat/*.nii*')) if s != primary_t1]
            else:
                t1w_scan_not_found.append(subj_sess_path)
                primary_t1 = ""
                others = [str(s) for s in list(subj_sess_path.glob('anat/*.nii*'))]

            mapping_dict[f"{subjid}/{subj_sess_path.name}"]['primary_t1'] = str(primary_t1)
            mapping_dict[f"{subjid}/{subj_sess_path.name}"]['others'] = others

    # write mapping dict to file
    with open(output.joinpath('primary_to_others_mapping.json'), 'w') as f1:
        json.dump(mapping_dict, f1, indent=4)

    # write session paths without T1w scan to file
    with open(output.joinpath('t1_unavailable.txt'), 'w') as f2:
        for sess_path in t1w_scan_not_found:
            f2.write(str(sess_path) + '\n')

    vqc_t1_mri_cmd = primary_scans_qc_prep(mapping_dict, output)
    print(
        f"\nVisualQC's visualqc_t1_mri utility can be used to QC primary scans with the following command.\n {vqc_t1_mri_cmd}")


if __name__ == "__main__":
    main()
