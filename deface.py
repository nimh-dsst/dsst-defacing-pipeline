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
    required_file_prefixes = ('__work', 'defacing.log')
    to_be_deleted_files = [
        str(f) for f in list(workdir_path.parent.glob('*'))
        if not (f.name.startswith(required_file_prefixes) or f.name.endswith('QC'))]
    run_command(f"rm -rf {' '.join(to_be_deleted_files)}", '')

    new_workdir_path = workdir_path.parent / f'workdir_{default_prefix}'
    workdir_path.rename(new_workdir_path)

    print(f"Removing unwanted files and renaming AFNI workdirs..")

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


def run_afni_refacer(primary_t1, others, subj_input_dir, sess_dir, output_dir):
    # constructing afni refacer command
    if primary_t1:
        subj_id = subj_input_dir.name
        sess_id = sess_dir.name if sess_dir else ""

        primary_t1 = Path(primary_t1)

        # setting up directory structure
        entities = primary_t1.name.split('_')
        for i in entities:
            if i.startswith('acq-'):
                acq = i.split('-')[1]
            else:
                acq = ""

        # TODO test on hv_protocol dataset to confirm. Is this directory even necessary with the new pipeline?
        subj_outdir = output_dir / subj_id / sess_id / 'anat' / acq

        prefix = primary_t1.name.split('.')[0]  # filename without the extension

        subj_outdir.mkdir(parents=True, exist_ok=True)  # make output directories within subject directory
        # afni refacer commands
        refacer_cmd = f"@afni_refacer_run -input {primary_t1} -mode_deface -no_clean -prefix {fspath(subj_outdir / prefix)}"

        # TODO remove module load afni
        full_cmd = f"module load afni ; {refacer_cmd}"

        # TODO make log text less ugly; perhaps in a separate function
        log_filename = subj_outdir / 'defacing_pipeline.log'
        log_fileobj = open(log_filename, 'w')
        log_fileobj.write(
            f"================================ afni_refacer_run command ================================\n"
            f"{full_cmd}\n"
            f"==========================================================================================\n")
        log_fileobj.flush()  # clear file object buffer

        # stdout text
        print(f"Running @afni_refacer_run on {primary_t1.name}\nFind command logs at {log_filename}")
        run_command(full_cmd, log_fileobj)
        print(f"@afni_refacer_run command completed on {primary_t1.name}\n")

        # rename afni workdirs
        workdir_list = list(subj_outdir.glob('*work_refacer*'))
        if len(workdir_list) > 0:
            missing_refacer_out = ""
            log_fileobj.flush()
            new_afni_workdir = rename_afni_workdir(workdir_list[0])

            # register other scans to the primary scan
            register.register_to_primary_scan(subj_input_dir, new_afni_workdir, primary_t1, others, log_fileobj)
        else:
            log_fileobj.write(
                f"@afni_refacer_run work directory not found. Most probably because the refacer command failed.")
            missing_refacer_out = prefix

        return missing_refacer_out


def deface_primary_scan(subj_input_dir, sess_dir, mapping_dict, output_dir):
    missing_refacer_outputs = []  # list to capture missing afni refacer workdirs

    subj_id = subj_input_dir.name
    sess_id = sess_dir.name if sess_dir else None

    if sess_dir:
        primary_t1 = mapping_dict[subj_id][sess_id]['primary_t1']
        others = [str(s) for s in mapping_dict[subj_id][sess_id]['others'] if s != primary_t1]
        missing_refacer_outputs.append(run_afni_refacer(primary_t1, others, subj_input_dir, sess_dir, output_dir))
    else:
        primary_t1 = mapping_dict[subj_id]['primary_t1']
        others = [str(s) for s in mapping_dict[subj_id]['others'] if s != primary_t1]
        missing_refacer_outputs.append(run_afni_refacer(primary_t1, others, subj_input_dir, "", output_dir))

    return missing_refacer_outputs


def main():
    return None


if __name__ == "__main__":
    main()
