import argparse
import gzip
import json
import shutil
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
    parser.add_argument('--no-clean', dest='no_clean', action='store_true', default=False,
                        help='If this argument is provided, then AFNI intermediate files are preserved.')

    args = parser.parse_args()
    # Arguments related checks
    if not args.subj_id and args.sess_id:  # Invalid: subjid not provided but sessid provided
        print("Session ID provided without a subject ID. Invalid Argument.")
        raise ValueError

    return args.input.resolve(), args.output.resolve(), args.mapping.resolve(), args.subj_id, args.sess_id, args.no_clean


# def run_command(cmdstr):
#     subprocess.run(cmdstr, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8', shell=True)


def write_to_file(file_content, filepath):
    ext = filepath.split('.')[-1]
    with open(filepath, 'w') as f:
        if ext == 'json':
            json.dump(file_content, f, indent=4)
        else:
            f.writelines(file_content)


def get_sess_dirs(subj_dir_path, mapping_dict):
    sess_dirs = [subj_dir_path / key if key.startswith('ses-') else "" for key in
                 mapping_dict[subj_dir_path.name].keys()]
    return sess_dirs


def compress_to_gz(input_file, output_file):
    if not output_file.exists():
        with open(input_file, 'rb') as f_input:
            with gzip.open(output_file, 'wb') as f_output:
                f_output.writelines(f_input)


def reorganize_into_bids(input_dir, defacing_outputs, mapping_dict, no_clean):
    # make afni_intermediate_files for each session within anat dir
    for anat_dir in defacing_outputs.rglob('anat'):
        sess_id = None
        # extract subject/session IDs
        subj_id = [i for i in anat_dir.parts if i.startswith('sub-')][0]

        # one anat dir associated with one sess dir, if at all
        for s in anat_dir.parts:
            if s.startswith('ses-'):
                sess_id = s

        primary_t1 = mapping_dict[subj_id][sess_id]['primary_t1'] if sess_id else mapping_dict[subj_id]['primary_t1']

        # iterate over all nii files within an anat dir to rename all primary and "other" scans
        for nii_filepath in anat_dir.rglob('*nii*'):
            if nii_filepath.name.startswith('tmp.99.result'):
                # convert to nii.gz, rename and copy over to anat dir
                gz_file = anat_dir / Path(primary_t1).name
                print(nii_filepath)
                compress_to_gz(nii_filepath, gz_file)

            elif nii_filepath.name.endswith('_defaced.nii.gz'):
                new_filename = '_'.join(nii_filepath.name.split('_')[:-1]) + '.nii.gz'
                shutil.copy2(nii_filepath, str(anat_dir / new_filename))

        # move QC images and afni intermediate files to a new directory
        intermediate_files_dir = anat_dir / 'afni_intermediate_files'
        intermediate_files_dir.mkdir(parents=True, exist_ok=True)
        for dirpath in anat_dir.glob('*'):
            if dirpath.name.startswith('workdir') or dirpath.name.endswith('QC'):
                shutil.move(dirpath, intermediate_files_dir)

        if not no_clean:
            shutil.rmtree(intermediate_files_dir)


def main():
    # get command line arguments
    input_dir, output, mapping, subj_id, sess_id, no_clean = get_args()

    # load primary to other scans mapping into a dict
    with open(mapping, 'r') as f:
        mapping_dict = json.load(f)

    # create a separate bids tree with only defaced scans
    defacing_outputs = output / 'defacing_outputs'
    defacing_outputs.mkdir(parents=True, exist_ok=True)

    afni_refacer_failures = []  # list to capture afni_refacer_run failures
    subj_sess_list = []

    if subj_id and not sess_id:  # parallel execution at subject level
        subj_dir = input_dir / subj_id
        subj_sess_list = [(subj_dir, sess_dir) for sess_dir in get_sess_dirs(subj_dir, mapping_dict)]

    elif subj_id and sess_id:  # parallel execution at session level
        subj_dir = input_dir / subj_id
        subj_sess_list = [(subj_dir, subj_dir / sess_id)]

    else:  # neither subjid nor sessid given; running pipeline serially
        for subj_dir in list(input_dir.glob('sub-*')):
            subj_sess_list = [(subj_dir, sess_dir) for sess_dir in get_sess_dirs(subj_dir, mapping_dict)]

    # calling deface.py script
    for subj_sess in subj_sess_list:
        missing_refacer_out = deface.deface_primary_scan(subj_sess[0], subj_sess[1], mapping_dict, defacing_outputs)
        if missing_refacer_out is not None:
            afni_refacer_failures.extend(missing_refacer_out)

    with open(output / 'defacing_pipeline_logs' / 'missing_afni_refacer_output.txt', 'w') as f:
        f.write('\n'.join(afni_refacer_failures))

    reorganize_into_bids(input_dir, defacing_outputs, mapping_dict, no_clean)


if __name__ == "__main__":
    main()
