import argparse
import json
import re
import subprocess
from multiprocessing.pool import Pool
from pathlib import Path

import deface
import generate_mappings


def get_args():
    parser = argparse.ArgumentParser(
        description='Deface anatomical scans for a given BIDS dataset or a subject directory in BIDS format.')

    parser.add_argument('bids_dir', type=Path,
                        help='The directory with the input dataset '
                             'formatted according to the BIDS standard.')
    parser.add_argument('output_dir', type=Path,
                        help='The directory where the output files should be stored.')
    parser.add_argument('-n', '--n-cpus', type=int, default=1,
                        help='Number of parallel processes to run when there is more than one folder. '
                             'Defaults to 1, meaning "serial processing".')
    parser.add_argument('-p', '--participant-label', nargs="+", type=str, default=None,
                        help='The label(s) of the participant(s) that should be defaced. The label '
                             'corresponds to sub-<participant_label> from the BIDS spec '
                             '(so it does not include "sub-"). If this parameter is not '
                             'provided all subjects should be analyzed. Multiple '
                             'participants can be specified with a space separated list.')
    parser.add_argument('-s', '--session-id', nargs="+", type=str, default=None,
                        help='The ID(s) of the session(s) that should be defaced. The label '
                             'corresponds to ses-<session_id> from the BIDS spec '
                             '(so it does not include "ses-"). If this parameter is not '
                             'provided all subjects should be analyzed. Multiple '
                             'sessions can be specified with a space separated list.')
    parser.add_argument('-m', '--mode', type=str, choices=['regular', 'aggressive'], default='regular',
                        help=f"In the 'regular' mode, the pipeline runs AFNI refacer the default template and "
                             f"in the 'aggressive' mode, the pipeline runs AFNI refacer with  the alternative shell "
                             f"that removes more of the chin, neck and brows. ")
    parser.add_argument('--no-clean', dest='no_clean', action='store_true', default=False,
                        help='If this argument is provided, then AFNI intermediate files are preserved.')

    return parser.parse_args()


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


def construct_vqcdeface_cmd(qc_dir):
    rel_paths_to_orig = [re.sub('/orig.nii.gz', '', str(o.relative_to(qc_dir))) for o in qc_dir.rglob('orig.nii.gz')]
    with open(qc_dir / 'defacing_id_list.txt', 'w') as f:
        f.write('\n'.join(rel_paths_to_orig))

    vqcdeface_cmd = f"vqcdeface -u {qc_dir} -i {qc_dir / 'defacing_id_list.txt'} -m orig.nii.gz -d defaced.nii.gz -r defaced_render"

    return vqcdeface_cmd


def main():
    # get command line arguments
    args = get_args()

    input_dir = args.bids_dir.resolve()
    output = args.output_dir.resolve()
    mode = args.mode
    no_clean = args.no_clean

    # run generate mapping script
    mapping_dict = generate_mappings.crawl(input_dir, output)

    # create a separate bids tree with only defaced scans
    bids_defaced_outdir = output / 'bids_defaced'
    bids_defaced_outdir.mkdir(parents=True, exist_ok=True)

    afni_refacer_failures = []  # list to capture afni_refacer_run failures

    to_deface = []
    # for one subject or list of subjects (and all their sessions, if present)
    if args.participant_label is not None and args.session_id is None:
        for p in args.participant_label:
            to_deface.extend(list(args.bids_dir.joinpath(f'sub-{p}').glob("ses-*")))

            if not to_deface:
                to_deface = list(args.bids_dir.glob(f'sub-{p}'))

    # for one subject or list of subjects and a specific session, if present
    elif args.participant_label is not None and args.session_id is not None:
        for p in args.participant_label:
            for s in args.session_id:
                to_deface.extend(list(args.bids_dir.glob(f'sub-{p}/ses-{s}/')))

                if not to_deface:
                    to_deface = list(args.bids_dir.glob(f'sub-{p}/ses-{s}/'))

    # only for one subset of sessions
    elif args.participant_label is None and args.session_id is not None:
        for s in args.session_id:
            to_deface = list(args.bids_dir.rglob(f'ses-{s}'))

    # for all subjects and all sessions
    elif args.participant_label is None and args.session_id is None:
        session_check = list(args.bids_dir.rglob("ses-*"))
        if session_check:
            to_deface = session_check

        # for all subjects (without "ses-*" session directories)
        else:
            to_deface = list(args.bids_dir.glob("sub-*"))

    # running processing style
    if args.n_cpus == 1:
        print('Defacing in Serial, one at a time')
        for defaceable in to_deface:
            subj_sess = defaceable.parts[-2:]

            if subj_sess[0].startswith('sub-'):
                subject = Path(subj_sess[0])
            elif subj_sess[1].startswith('sub-'):
                subject = Path(subj_sess[1])
            else:
                raise ValueError(f'Could not find subject name in path: {defaceable}')

            if subj_sess[1].startswith('ses-'):
                session = Path(subj_sess[1])
            else:
                session = None

            missing_refacer_out = deface.deface_primary_scan(
                input_dir,
                subject,
                session,
                mapping_dict,
                bids_defaced_outdir,
                mode,
                no_clean

            )

            if missing_refacer_out is not None:
                afni_refacer_failures.extend(missing_refacer_out)

    elif args.n_cpus > 1:
        print(f'Defacing in Parallel with {args.n_cpus} cores')
        # initialize pool
        with Pool(processes=args.n_cpus) as p:

            # run over defaceables subjects and sessions
            subject_list = []
            session_list = []
            subj_sess_list = [defaceable.parts[-2:] for defaceable in to_deface]
            for subj_sess in subj_sess_list:
                if subj_sess[0].startswith('sub-'):
                    subject_list.append(Path(subj_sess[0]))
                elif subj_sess[1].startswith('sub-'):
                    subject_list.append(Path(subj_sess[1]))
                else:
                    raise ValueError(f'Could not find subject name in path: {defaceable}')

                if subj_sess[1].startswith('ses-'):
                    session_list.append(Path(subj_sess[1]))
                else:
                    session_list.append(None)

            # parallel processing
            missing_refacer_outs = p.starmap(deface.deface_primary_scan,
                                             zip(
                                                 [input_dir] * len(subject_list),
                                                 subject_list,
                                                 session_list,
                                                 [mapping_dict] * len(subject_list),
                                                 [bids_defaced_outdir] * len(subject_list),
                                                 [mode] * len(subject_list),
                                                 [no_clean] * len(subject_list)
                                             ))

        # collect failures
        for missing_refacer_out in missing_refacer_outs:
            if missing_refacer_out is not None:
                afni_refacer_failures.extend(missing_refacer_out)

        vqcdeface_cmd = construct_vqcdeface_cmd(output / 'defacing_QC')
        print(f"Run the following command to start a VisualQC Deface session:\n\t{vqcdeface_cmd}\n")
        with open(output / 'defacing_qc_cmd', 'w') as f:
            f.write(vqcdeface_cmd + '\n')

    else:
        raise ValueError("Invalid processing type. Must be either 'serial' or 'parallel'.")


if __name__ == "__main__":
    main()
