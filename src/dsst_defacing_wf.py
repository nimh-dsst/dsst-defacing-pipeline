import argparse
import json
import re
import subprocess
from pathlib import Path

import deface
import generate_mappings


def get_args():
    parser = argparse.ArgumentParser(
        description='Deface anatomical scans for a given BIDS dataset or a subject directory in BIDS format.')

    parser.add_argument('--input', '-i', action='store', type=Path, required=True, dest='input',
                        help='Path to input BIDS dataset.')

    parser.add_argument('--output', '-o', action='store', type=Path, required=True, dest='output',
                        help='Path to output BIDS dataset with defaced scan.')

    parser.add_argument('--participant-id', '-p', dest='subj_id', action='store', required=False, default=None,
                        help="Subject ID associated with the participant. Since the input dataset is assumed to be \
                        BIDS valid, this argument expects subject IDs with 'sub-' prefix.")
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

    return args.input.resolve(), args.output.resolve(), args.subj_id, args.sess_id, args.no_clean


def run_command(cmdstr):
    subprocess.run(cmdstr, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8', shell=True)


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


def generate_3d_renders(defaced_img, render_outdir):
    rotations = [(45, 5, 10), (-45, 5, 10)]
    for idx, rot in enumerate(rotations):
        yaw, pitch, roll = rot[0], rot[1], rot[2]
        outfile = render_outdir.joinpath('defaced_render_' + str(idx) + '.png')
        fsleyes_render_cmd = f"export TMP_DISPLAY=`echo $DISPLAY`; unset DISPLAY; module unload fsl; fsleyes render --scene 3d -rot {yaw} {pitch} {roll} --outfile {outfile} {defaced_img} -dr 20 250 -in spline -bf 0.3 -r 100 -ns 500; export DISPLAY=`echo $TMP_DISPLAY`"
        print(fsleyes_render_cmd)
        run_command(fsleyes_render_cmd)
        print(f"Has the render been created? {outfile.exists()}")


def create_defacing_id_list(qc_dir):
    rel_paths_to_orig = [re.sub('/orig.nii.gz', '', str(o.relative_to(qc_dir))) for o in qc_dir.rglob('orig.nii.gz')]
    with open(qc_dir / 'defacing_id_list.txt', 'w') as f:
        f.write('\n'.join(rel_paths_to_orig))


def vqcdeface_prep(input_dir, defacing_output_dir):
    defacing_qc_dir = defacing_output_dir.parent / 'QC_prep' / 'defacing_QC'
    interested_files = [f for f in defacing_output_dir.rglob('*.nii.gz') if
                        'workdir' not in str(f).split('/')]
    for defaced_img in interested_files:
        entities = defaced_img.name.split('.')[0].split('_')
        vqcd_subj_dir = defacing_qc_dir / f"{'/'.join(entities)}"
        vqcd_subj_dir.mkdir(parents=True, exist_ok=True)

        defaced_link = vqcd_subj_dir / 'defaced.nii.gz'
        if not defaced_link.exists():
            defaced_link.symlink_to(defaced_img)
        generate_3d_renders(defaced_img, vqcd_subj_dir)

        img = list(input_dir.rglob(defaced_img.name))[0]
        img_link = vqcd_subj_dir / 'orig.nii.gz'
        if not img_link.exists(): img_link.symlink_to(img)

    create_defacing_id_list(defacing_qc_dir)

    vqcdeface_cmd = f"vqcdeface -u {defacing_qc_dir} -i {defacing_qc_dir / 'defacing_id_list.txt'} -m orig.nii.gz -d defaced.nii.gz -r defaced_render"

    return vqcdeface_cmd


def main():
    # get command line arguments
    input_dir, output, subj_id, sess_id, no_clean = get_args()

    # run generate mapping script
    mapping_dict = generate_mappings.crawl(input_dir, output)

    # create a separate bids tree with only defaced scans
    defacing_outputs = output / 'bids_defaced'
    defacing_outputs.mkdir(parents=True, exist_ok=True)

    afni_refacer_failures = []  # list to capture afni_refacer_run failures

    if subj_id and not sess_id:  # parallel execution at subject level
        subj_dir = input_dir / subj_id
        subj_sess_list = [(subj_dir, sess_dir) for sess_dir in get_sess_dirs(subj_dir, mapping_dict)]

    elif subj_id and sess_id:  # parallel execution at session level
        subj_dir = input_dir / subj_id
        subj_sess_list = [(subj_dir, subj_dir / sess_id)]

    else:  # neither subjid nor sessid given; running pipeline serially
        subj_sess_list = []
        for subj_dir in list(input_dir.glob('sub-*')):
            subj_sess_list.extend([(subj_dir, sess_dir) for sess_dir in get_sess_dirs(subj_dir, mapping_dict)])

    # calling deface.py script
    for subj_sess in subj_sess_list:
        missing_refacer_out = deface.deface_primary_scan(input_dir, subj_sess[0], subj_sess[1], mapping_dict,
                                                         defacing_outputs, no_clean)
        if missing_refacer_out is not None:
            afni_refacer_failures.extend(missing_refacer_out)

    with open(output / 'logs' / 'failed_afni_refacer_output.txt', 'w') as f:
        f.write('\n'.join(afni_refacer_failures))  # TODO Not very useful when running the pipeline in parallel

    # unload fsl module and use fsleyes installed on conda env
    # os.environ['TMP_DISPLAY'] =

    # prep for visual inspection using visualqc deface
    print(f"Preparing for QC by visual inspection...\n")

    vqcdeface_cmd = vqcdeface_prep(input_dir, defacing_outputs)
    print(f"Run the following command to start a VisualQC Deface session:\n\t{vqcdeface_cmd}\n")
    with open(output / 'QC_prep' / 'defacing_qc_cmd', 'w') as f:
        f.write(vqcdeface_cmd + '\n')


if __name__ == "__main__":
    main()
