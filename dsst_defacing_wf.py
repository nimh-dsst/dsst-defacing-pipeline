import argparse
import json
from pathlib import Path

import deface


def get_args():
    parser = argparse.ArgumentParser(
        description='Deface anatomical scans for a given BIDS dataset or a subject directory in BIDS format.')

    parser.add_argument('--input', '-i', action='store', type=Path, required=True, dest='input',
                        help='Path to input BIDS dataset.')

    parser.add_argument('--output', '-o', action='store', type=Path, required=True, dest='output',
                        help='Path to output BIDS dataset with defaced scan.')

    parser.add_argument('--mapping-file', '-m', action='store', type=Path, required=True, dest='mapping',
                        help='Path to primary to other/secondary scans mapping file.')

    parser.add_argument('--participant-id', '-p', dest='subj_id', action='store', required=False, default=None,
                        help="Subject ID associated with the participant. Since the input dataset is assumed to be \
                        BIDS valid, this argument expects subject IDs with 'sub-' prefix.")
    # This argument is valid only if a subject ID is provided
    # TODO Test the session id argument
    parser.add_argument('--session-id', '-s', dest='sess_id', action='store', required=False, default=None,
                        help="Session ID associated with the subject ID. If the BIDS input dataset contains sessions, \
                        then this argument expects session IDs with 'ses-' prefix.")

    args = parser.parse_args()
    # Arguments related checks
    if not args.subj_id and args.sess_id:  # Invalid: subjid not provided but sessid provided
        print("Session ID provided without a subject ID. Invalid Argument.")
        raise ValueError

    return args.input.resolve(), args.output.resolve(), args.mapping.resolve(), args.subj_id, args.sess_id


def write_to_file(file_content, filepath):
    ext = filepath.split('.')[-1]
    with open(filepath, 'w') as f:
        if ext == 'json':
            json.dump(file_content, f, indent=4)
        else:
            f.writelines(file_content)


def reorganize_into_bids():
    return None


def main():
    # get command line arguments
    input_dir, output, mapping, subj_id, sess_id = get_args()

    # load primary to other scans mapping into a dict
    with open(mapping, 'r') as f:
        mapping_dict = json.load(f)

    # create a separate bids tree with only defaced scans
    bids_output_dir = output / 'bids_defaced'
    bids_output_dir.mkdir(parents=True, exist_ok=True)

    afni_refacer_failures = []  # list to capture afni_refacer_run failures

    # run the pipeline at subject or session depending on provided arguments; parallel execution
    if subj_id and not sess_id:
        subj_dir = input_dir / subj_id
        sess_dirs = [sess if sess else "" for sess in subj_dir.glob('ses-*')]  # check if sess dirs are present
        for sess_dir in sess_dirs:
            missing_refacer_out = deface.deface_primary_scan(subj_dir, sess_dir, mapping_dict, bids_output_dir)
            if missing_refacer_out is not None:
                afni_refacer_failures.extend(missing_refacer_out)

    elif subj_id and sess_id:
        subj_dir = input_dir / subj_id
        sess_dir = subj_dir / sess_id
        missing_refacer_out = deface.deface_primary_scan(subj_dir, sess_dir, mapping_dict, bids_output_dir)
        if missing_refacer_out is not None:
            afni_refacer_failures.extend(missing_refacer_out)

    else:  # neither subjid nor sessid given; running pipeline serially
        for subj_dir in list(input_dir.glob('sub-*')):
            missing_refacer_out = deface.deface_primary_scan(subj_dir, "", mapping_dict, bids_output_dir)
            if missing_refacer_out is not None:
                afni_refacer_failures.extend(missing_refacer_out)

    with open(output / 'logs' / 'missing_afni_refacer_output.txt', 'w') as f:
        f.write('\n'.join(afni_refacer_failures))


if __name__ == "__main__":
    main()
