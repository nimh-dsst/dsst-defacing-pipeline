import argparse
import re
from multiprocessing.pool import Pool
from pathlib import Path
import utils
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
                             'corresponds to sub-<participant_label> from the BIDS spec. '
                             'If this parameter is not provided all subjects should be analyzed. Multiple '
                             'participants can be specified with a space separated list.')
    parser.add_argument('-s', '--session-id', nargs="+", type=str, default=None,
                        help='The ID(s) of the session(s) that should be defaced. The label '
                             'corresponds to ses-<session_id> from the BIDS spec. '
                             'If this parameter is not provided all subjects should be analyzed. Multiple '
                             'sessions can be specified with a space separated list.')
    parser.add_argument('-m', '--mode', type=str, choices=['regular', 'aggressive'], default='regular',
                        help=f"In the 'regular' mode, the pipeline runs AFNI refacer the default template and "
                             f"in the 'aggressive' mode, the pipeline runs AFNI refacer with  the alternative shell "
                             f"that removes more of the chin, neck and brows. ")
    parser.add_argument('--no-clean', dest='no_clean', action='store_true', default=False,
                        help='If this argument is provided, then AFNI intermediate files are preserved.')
    parser.add_argument('--nih-hpc', dest='nih_hpc', action='store_true', default=False,
                        help='While running the pipeline on NIH HPC, if this argument is provided, then the required \
                        AFNI and FSL modules are loaded into the environment.')

    return parser.parse_args()


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
    output_dir = args.output_dir.resolve()
    mode = args.mode
    no_clean = args.no_clean

    defacing_log = output_dir / 'logs' / 'defacing_pipeline.log'
    if not defacing_log.parent.exists():
        defacing_log.parent.mkdir(parents=True, exist_ok=True)

    main_logger = utils.setup_logger(defacing_log)

    if not input_dir.exists():
        main_logger.error(f"Input directory {input_dir} does not exist.")
        raise FileNotFoundError("Please provide a valid path to input BIDS directory.")

    participant_labels = []
    if args.participant_label:
        participant_labels = [p.split('-')[1] if p.startswith('sub-') else p for p in args.participant_label]

    session_labels = []
    if args.session_id:
        session_labels = [s.split('-')[1] if s.startswith('ses-') else s for s in args.session_id]

    ## run generate mapping script
    mapping_dict = generate_mappings.crawl(input_dir, output_dir)
    main_logger.info(f"Mapping file at {str(output_dir / 'primary_to_others_mapping.json')} ")
    main_logger.info(f"Logs at {str(output_dir / 'logs')}\n")

    # create a separate bids tree with only defaced scans
    bids_defaced_outdir = output_dir / 'bids_defaced'
    bids_defaced_outdir.mkdir(parents=True, exist_ok=True)

    afni_refacer_failures = []  # list to capture afni_refacer_run failures

    to_deface = []

    if participant_labels and not session_labels:
        # for one subject or list of subjects (and all their sessions, if present)
        for p in participant_labels:
            to_deface.extend(list(input_dir.joinpath(f'sub-{p}').glob('ses-*')))
            if not to_deface:  # if no sess_dir found
                to_deface.extend([input_dir.joinpath(f'sub-{p}')])

    elif participant_labels and session_labels:
        # for one subject or list of subjects and a specific session, if present
        for p in participant_labels:
            for s in session_labels:
                to_deface.extend(list(args.bids_dir.joinpath(f'sub-{p}/ses-{s}/')))
                if not to_deface:
                    to_deface = list(args.bids_dir.joinpath(f'sub-{p}/ses-{s}/'))

    elif not participant_labels and not session_labels:
        # only for one subset of sessions
        for s in session_labels:
            to_deface = list(args.bids_dir.rglob(f'ses-{s}'))  # TODO: could match ses dirs within dot dirs. Fix this.

    elif args.participant_label is None and args.session_id is None:
        # for all subjects and all sessions
        session_list = list(args.bids_dir.rglob('ses-*'))  # TODO: could match ses dirs within dot dirs. Fix this.
        if session_list:
            to_deface = session_list
        else:  # for all subjects (without "ses-*" session directories)
            to_deface = list(args.bids_dir.glob('sub-*'))

    # running processing style
    if args.n_cpus == 1:
        main_logger.info('Defacing in Serial, one at a time')
        for defaceable in to_deface:
            subj_sess = defaceable.parts[-2:]

            if subj_sess[0].startswith('sub-'):
                subject = Path(subj_sess[0])
            elif subj_sess[1].startswith('sub-'):
                subject = Path(subj_sess[1])
            else:
                main_logger.error(f'Subject name not found in path.')
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
                no_clean,
                args.nih_hpc
            )

            if missing_refacer_out is not None:
                afni_refacer_failures.extend(missing_refacer_out)

    elif args.n_cpus > 1:
        main_logger.info(f'Defacing in Parallel with {args.n_cpus} cores')
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
                    main_logger.error(f'Subject name not found in path.')
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
                                                 [no_clean] * len(subject_list),
                                                 [args.nih_hpc] * len(subject_list)
                                             ))

        # collect failures
        for missing_refacer_out in missing_refacer_outs:
            if missing_refacer_out is not None:
                afni_refacer_failures.extend(missing_refacer_out)

        vqcdeface_cmd = construct_vqcdeface_cmd(output_dir / 'defacing_QC')
        main_logger.info(f"Run the following command to start a VisualQC Deface session:\n\t{vqcdeface_cmd}\n")
        with open(output_dir / 'defacing_qc_cmd', 'w') as f:
            f.write(vqcdeface_cmd + '\n')

    else:
        raise ValueError("Invalid processing type. Must be either 'serial' or 'parallel'.")


if __name__ == "__main__":
    main()
