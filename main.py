import argparse
import json
from collections import defaultdict
from pathlib import Path

import deface


def get_args():
    parser = argparse.ArgumentParser(
        description='Deface anatomical scans for a given BIDS dataset.')
    subparsers = parser.add_subparsers(help='commands')

    parser.add_argument('--input', '-i', action='store', required=True, dest='input',
                        help='Path to input BIDS dataset.')

    parser.add_argument('--output', '-o', action='store', required=True, dest='output',
                        help='Path to output BIDS dataset with defaced scan.')

    parser.add_argument('--level', '-l', choices=['dataset', 'subject'], default='dataset',
                        action='store', dest='level')  # TODO: add help description
    subject_parser = subparsers.add_parser('subject_args')
    subject_parser.add_argument('--subject', '-s', dest='subjid', action='store',
                                help='Deface anatomical scans in the subject directory only.')

    args = parser.parse_args()
    return Path(args.input).resolve(), Path(args.output).resolve(), args.level, args.subjid


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
    input, output, level, subjid = get_args()

    afni_refacer_failures = []  # list of scans that failed afni_refacer_run
    mapping_dict = defaultdict(lambda: defaultdict(list))  # primary to other scans per subject-session mapping file

    if level == 'dataset':
        for subj_dir in list(input.glob('sub-*')):
            mapping_dict, missing_refacer_out = deface.deface_primary_scan(subj_dir, mapping_dict, output)
            if missing_refacer_out is not None:
                afni_refacer_failures.append(missing_refacer_out)
    elif level == 'subject':
        subj_dir = input.joinpath(subjid)
        mapping_dict, missing_refacer_out = deface.deface_primary_scan(subj_dir, mapping_dict, output)
        if missing_refacer_out is not None:
            afni_refacer_failures.append(missing_refacer_out)


if __name__ == "__main__":
    main()
