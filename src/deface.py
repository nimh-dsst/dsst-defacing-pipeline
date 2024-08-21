import gzip
import re
import shutil
import subprocess
from os import fspath
from pathlib import Path

import register


def run_command(cmdstr, logfile):
    if not logfile:
        logfile = subprocess.PIPE
    subprocess.run(cmdstr, stdout=logfile, stderr=subprocess.STDOUT, encoding='utf8', shell=True)


def rename_afni_workdir(workdir_path):
    default_prefix = workdir_path.name.split('.')[1]
    required_file_suffixes = ('QC', 'defacing_pipeline.log')
    to_be_deleted_files = [
        str(f) for f in list(workdir_path.parent.glob('*'))
        if not (f.name.startswith('__work') or f.name.endswith(required_file_suffixes))]
    run_command(f"rm -rf {' '.join(to_be_deleted_files)}", '')

    new_workdir_path = workdir_path.parent / f'workdir_{default_prefix}'
    workdir_path.rename(new_workdir_path)

    print(f"Removing unwanted files and renaming AFNI workdirs..\n")

    return new_workdir_path


def get_anat_dir_paths(subj_dir_path):
    """Given subject directory path, finds all anat directories in subject directory tree.

    :param Path subj_dir_path : Absolute path to subject directory.
    :return: A list of absolute paths to anat directory(s) within subject tree.
    """
    anat_dirs = []
    # check if there are session directories
    sessions = list(subj_dir_path.glob('ses-*'))
    if not sessions:
        anat_dir = subj_dir_path / 'anat'
        if not anat_dir.exists():
            print(f'No anat directories found for {subj_dir_path.name}.\n')
        anat_dirs.append(anat_dir)
    else:
        for sess in sessions:
            anat_dir = sess.joinpath('anat')
            if not anat_dir.exists():
                print(f'No anat directories found for {subj_dir_path.name} and {sess.name}.\n')
            anat_dirs.append(anat_dir)

    return anat_dirs


def compress_to_gz(input_file, output_file):
    if not output_file.exists():
        with open(input_file, 'rb') as f_input:
            with gzip.open(output_file, 'wb') as f_output:
                f_output.writelines(f_input)


def copy_over_sidecar(scan_filepath, input_anat_dir, output_anat_dir):
    prefix = '_'.join([i for i in re.split('_|\.', scan_filepath.name) if i not in ['defaced', 'nii', 'gz']])
    filename = prefix + '.json'
    json_sidecar = input_anat_dir / filename
    shutil.copy2(json_sidecar, output_anat_dir / filename)


def generate_3d_renders(defaced_img, render_outdir):
    rotations = [(45, 5, 10), (-45, 5, 10)]
    for idx, rot in enumerate(rotations):
        yaw, pitch, roll = rot[0], rot[1], rot[2]
        outfile = render_outdir.joinpath('defaced_render_0' + str(idx) + '.png')
        if not outfile.exists():
            fsleyes_render_cmd = f"module load fsl; fsleyes render --scene 3d -rot {yaw} {pitch} {roll} --outfile {outfile} {defaced_img} --displayRange 20 250 --interpolation spline --cmap render1 --blendFactor 0.3 -r 100 --numSteps 500"

            print(fsleyes_render_cmd)
            run_command(fsleyes_render_cmd, "")
            print(f"Has the render been created? {outfile.exists()}")


def vqcdeface_prep(bids_input_dir, defaced_anat_dir, bids_defaced_outdir):
    defacing_qc_dir = bids_defaced_outdir.parent / 'defacing_QC'
    interested_files = [f for f in defaced_anat_dir.rglob('*.nii.gz') if
                        'work_dir' not in str(f).split('/')]
    print(interested_files)
    for defaced_img in interested_files:
        entities = defaced_img.name.split('.')[0].split('_')
        vqcd_subj_dir = defacing_qc_dir / f"{'/'.join(entities)}"
        vqcd_subj_dir.mkdir(parents=True, exist_ok=True)

        defaced_link = vqcd_subj_dir / 'defaced.nii.gz'
        if not defaced_link.is_symlink():
            defaced_link.symlink_to(defaced_img)
        print(list(bids_input_dir.rglob(defaced_img.name)))
        img = list(bids_input_dir.rglob(defaced_img.name))[0]
        img_link = vqcd_subj_dir / 'orig.nii.gz'
        if not img_link.is_symlink(): img_link.symlink_to(img)


def reorganize_into_bids(input_bids_dir, subj_id, sess_id, primary_scan, bids_defaced_outdir, no_clean):
    if sess_id:
        anat_dirs = list(bids_defaced_outdir.joinpath(subj_id, sess_id).rglob('anat'))
    else:
        anat_dirs = list(bids_defaced_outdir.joinpath(subj_id).rglob('anat'))

    # make workdir for each session within anat dir
    for anat_dir in anat_dirs:
        # iterate over all nii files within an anat dir to rename all primary and "other" scans
        for nii_filepath in anat_dir.rglob('*nii*'):
            if nii_filepath.name.startswith('tmp.99.result'):
                # convert to nii.gz, rename and copy over to anat dir
                gz_file = anat_dir / Path(primary_scan).name
                compress_to_gz(nii_filepath, gz_file)

                # copy over corresponding json sidecar
                copy_over_sidecar(Path(primary_scan), input_bids_dir / anat_dir.relative_to(bids_defaced_outdir),
                                  anat_dir)

            elif nii_filepath.name.endswith('_defaced.nii.gz'):
                new_filename = '_'.join(nii_filepath.name.split('_')[:-1]) + '.nii.gz'
                shutil.copy2(nii_filepath, str(anat_dir / new_filename))

                copy_over_sidecar(nii_filepath, input_bids_dir / anat_dir.relative_to(bids_defaced_outdir), anat_dir)

        # move QC images and afni intermediate files to a new directory
        intermediate_files_dir = anat_dir / 'work_dir'
        intermediate_files_dir.mkdir(parents=True, exist_ok=True)
        for dirpath in anat_dir.glob('*'):
            if dirpath.name.startswith('workdir'):
                new_name = '_'.join(['afni', dirpath.name])
                shutil.move(str(dirpath), str(intermediate_files_dir / new_name))
            elif dirpath.name.endswith('QC'):
                shutil.move(str(dirpath), str(intermediate_files_dir))

        vqcdeface_prep(input_bids_dir, anat_dir, bids_defaced_outdir)

        if not no_clean:
            shutil.rmtree(intermediate_files_dir)


def run_afni_refacer(primary_t1, others, subj_input_dir, sess_dir, output_dir, mode):
    # constructing afni refacer command
    subj_id = subj_input_dir.name

    all_primaries = []
    if primary_t1:
        all_primaries.append(primary_t1)
        all_others = others
    else:
        # if there is no T1w scan in the session, then process every "other" scan as a primary scan
        all_primaries = others
        all_others = []

    for primary in all_primaries:
        primary = Path(primary)

        # setting up directory structure
        entities = primary.name.split('_')
        for i in entities:
            if i.startswith('acq-'):
                acq = i.split('-')[1]
            else:
                acq = ""

        subj_output_dir = output_dir / subj_id / sess_id / 'anat' / acq
        if not subj_output_dir.exists():
            subj_output_dir.mkdir(parents=True, exist_ok=True)  # make output directories within subject directory

        prefix = primary.name.split('.')[0]  # filename without the extension

        subj_outdir.mkdir(parents=True, exist_ok=True)  # make output directories within subject directory
        # construct afni refacer commands
        if mode == 'aggressive':
            refacer_cmd = f"@afni_refacer_run -input {primary_t1} -mode_deface -no_clean -prefix {fspath(subj_outdir / prefix)} -shell afni_refacer_shell_sym_2.0.nii.gz"

        else:
            refacer_cmd = f"@afni_refacer_run -input {primary_t1} -mode_deface -no_clean -prefix {fspath(subj_outdir / prefix)}"


        # TODO remove module load afni
        full_cmd = f"module load afni ;  {refacer_cmd}"

        # TODO make log text less ugly; perhaps in a separate function
        if sess_id:
            log_filename = subj_output_dir / f'{subj_id}_{sess_id}_defacing_pipeline.log'
        else:
            log_filename = subj_output_dir / f'{subj_id}_defacing_pipeline.log'

        log_fileobj = open(log_filename, 'w')
        log_fileobj.write(
            f"================================ afni_refacer_run command ================================\n"
            f"{full_cmd}\n"
            f"==========================================================================================\n")
        log_fileobj.flush()  # clear file object buffer

        # stdout text
        print(f"Running @afni_refacer_run on {primary.name}\nCommand logs at {log_filename}")
        run_command(full_cmd, log_fileobj)
        print(f"@afni_refacer_run command completed on {primary.name}\n")

        # rename afni workdirs
        workdir_list = list(subj_output_dir.glob('*work_refacer*'))
        if len(workdir_list) > 0:
            missing_refacer_out = ""
            log_fileobj.flush()
            new_afni_workdir = rename_afni_workdir(workdir_list[0])

            # register other scans to the primary scan
            register.register_to_primary_scan(subj_input_dir, new_afni_workdir, primary, all_others, log_fileobj)

        else:
            log_fileobj.write(
                f"@afni_refacer_run work directory not found. Most probably because the refacer command failed.")
            missing_refacer_out = prefix

        return missing_refacer_out


def deface_primary_scan(input_bids_dir, subj_input_dir, sess_dir, mapping_dict, output_dir, mode, no_clean):
    
    missing_refacer_outputs = []  # list to capture missing afni refacer workdirs
    
    subj_id = Path(subj_input_dir).name
    sess_id = Path(sess_dir).name if sess_dir else ""

    if not sess_id:
        primary_t1 = mapping_dict[subj_id]['primary_t1']
        others = [str(s) for s in mapping_dict[subj_id]['others'] if s != primary_t1]
        missing_refacer_outputs.append(run_afni_refacer(primary_t1, others, subj_input_dir, "", output_dir, mode))
        print(f"Reorganizing {subj_input_dir} with defaced images into BIDS tree...\n")
    else:
        primary_t1 = mapping_dict[subj_id][sess_id]['primary_t1']
        others = [str(s) for s in mapping_dict[subj_id][sess_id]['others'] if s != primary_t1]
        missing_refacer_outputs.append(run_afni_refacer(primary_t1, others, subj_input_dir, sess_dir, output_dir, mode))
        print(f"Reorganizing {sess_dir} with defaced images into BIDS tree...\n")

    # reorganizing the directory with defaced images into BIDS tree
    reorganize_into_bids(input_bids_dir, subj_input_dir, sess_dir, primary_t1, output_dir, no_clean)
    
    return missing_refacer_outputs
