import argparse
import json
from pathlib import Path

import deface


def get_args():
    parser = argparse.ArgumentParser(
        description='Deface anatomical scans for a given BIDS dataset or a subject directory in BIDS format.')

    parser.add_argument('--input', '-i', action='store', required=True, dest='input',
                        help='Path to input BIDS dataset.')

    parser.add_argument('--output', '-o', action='store', required=True, dest='output',
                        help='Path to output BIDS dataset with defaced scan.')

    parser.add_argument('--mapping-file', '-m', action='store', required=True, dest='mapping',
                        help='Path to primary to other/secondary scans mapping file.')

    parser.add_argument('--subject-id', '-s', dest='subjid', action='store',
                        help="Subject ID associated with the participant. Since the input dataset is assumed to be \
                        BIDS valid, this argument expects subject IDs with 'sub-' prefix.")

    args = parser.parse_args()
    if not args.subjid:
        args.subjid = ""

    return Path(args.input).resolve(), Path(args.output).resolve(), Path(
        args.mapping).resolve(), args.subjid


def write_to_file(file_content, filepath):
    ext = filepath.split('.')[-1]
    if ext == 'json':
        with open(filepath, 'w') as f:
            json.dump(file_content, f, indent=4)
    else:
        with open(filepath, 'w') as f:
            f.writelines(file_content)


def defaced_scans_in_bids_tree():
    return None


def main():
    # get command line arguments
    input, output, mapping, subjid = get_args()

    afni_refacer_failures = []  # list of scans that failed afni_refacer_run
    mapping_fobj = open(mapping, 'r')
    mapping_dict = json.load(mapping_fobj)  # primary to other scans per subject-session mapping file

    if not subjid:
        for subj_dir in list(input.glob('sub-*')):
            missing_refacer_out = deface.deface_primary_scan(subj_dir, mapping_dict, output)
            if missing_refacer_out is not None:
                afni_refacer_failures.extend(missing_refacer_out)
    elif subjid:
        subj_dir = input.joinpath(subjid)
        missing_refacer_out = deface.deface_primary_scan(subj_dir, mapping_dict, output)
        if missing_refacer_out is not None:
            afni_refacer_failures.extend(missing_refacer_out)

    with open(output.joinpath('missing_afni_refacer_output.txt'), 'w') as f:
        for line in afni_refacer_failures:
            f.write(str(line))


if __name__ == "__main__":
    main()
