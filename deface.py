import subprocess
from os import fspath
from pathlib import Path

import register


def run(cmdstr, logfile):
    if not logfile:
        subprocess.run(cmdstr, stdout=logfile, stderr=subprocess.STDOUT, encoding='utf8', shell=True)
    else:
        subprocess.run(cmdstr, stdout=logfile, stderr=subprocess.STDOUT, encoding='utf8', shell=True)


def rename_afni_workdir(workdir_path, logfile_obj):
    default_prefix = workdir_path.name.split('.')[1]
    print(default_prefix)
    to_be_deleted_files = [fspath(f) for f in list(workdir_path.parent.glob('*')) if
                           not f.name.startswith('__work') and not f.name.startswith('logs')]
    remove_files = f"rm -rf {' '.join(to_be_deleted_files)}"
    new_workdir_path = workdir_path.parent.joinpath('workdir_' + default_prefix)

    rename = f"mv {workdir_path} {new_workdir_path}"
    cmd = '; '.join([remove_files, rename])
    print(f"Removing unwanted files and renaming AFNI workdirs..")
    run(cmd, logfile_obj)

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
        anat_dir = subj_dir_path.joinpath('anat')
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


# def get_primary_and_others(subjid, sessions, mapping_dict):


def run_afni_refacer(primary_t1, others, subj_input_dir, output_dir):
    # constructing afni refacer command
    if primary_t1:
        primary_t1 = Path(primary_t1)
        entities = primary_t1.name.split('_')
        acq = [i.split('-')[1] for i in entities if i.startswith('acq-')]
        if acq:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], 'anat', acq[0])
        else:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], 'anat')

        prefix = primary_t1.name.split('.')[0]  # filename without the extension

        mkdir_cmds = f"mkdir -p {subj_outdir}"  # make output directories within subject directory

        # afni commands
        refacer = f"@afni_refacer_run -input {primary_t1} -mode_deface -no_clean -prefix {fspath(subj_outdir.joinpath(prefix))}"

        full_cmd = ' ; '.join(['module load afni', mkdir_cmds, refacer]) + '\n'
        print(full_cmd)
        logfile_name = subj_outdir.joinpath('logs', f"{primary_t1.name.split('.')[0]}_log_deface.txt")
        if not logfile_name.parent.exists():
            logfile_name.parent.mkdir(parents=True)
        logfile_obj = open(subj_outdir.joinpath('logs', logfile_name), 'w')
        logfile_obj.write(
            f"================================ afni_refacer_run command ================================\n"
            f"{full_cmd}\n"
            f"==========================================================================================\n")
        logfile_obj.flush()  # clear file object buffer
        print(f"Starting a child process to run afni_refacer on {primary_t1.name}.")
        run(full_cmd, logfile_obj)
        print(f"Child process to run afni_refacer on {primary_t1.name} completed.\n")

        # rename afni workdirs
        workdir_list = list(subj_outdir.glob('__work_refacer*'))
        if len(workdir_list) > 0:
            logfile_obj.flush()
            new_afni_workdir = rename_afni_workdir(workdir_list[0], logfile_obj)
            # register other scans to the primary scan
            register.register_to_primary_scan(subj_input_dir, new_afni_workdir, primary_t1, others, logfile_obj)

        logfile_obj.write(
            f"afni_refacer_run work directory not found. Most probably because the refacer command failed.")
        missing_refacer_out = prefix

        return missing_refacer_out


def deface_primary_scan(subj_input_dir, mapping_dict, output_dir):
    subjid = subj_input_dir.name
    sessions = [k for k in mapping_dict[subjid].keys() if k.startswith('ses')]
    missing_refacer_outputs = []
    if sessions:

        for session in sessions:
            primary_t1 = mapping_dict[subjid][session]['primary_t1']
            others = [str(s) for s in mapping_dict[subjid][session]['others'] if s != primary_t1]
            missing_refacer_outputs.append(run_afni_refacer(primary_t1, others, subj_input_dir, output_dir))
    else:
        primary_t1 = mapping_dict[subjid]['primary_t1']
        others = [str(s) for s in mapping_dict[subjid]['others'] if s != primary_t1]
        missing_refacer_outputs.append(run_afni_refacer(primary_t1, others, subj_input_dir, output_dir))
    return missing_refacer_outputs
    # # constructing afni refacer command
    # if primary_t1:
    #     primary_t1 = Path(primary_t1)
    #     entities = primary_t1.name.split('_')
    #     acq = [i.split('-')[1] for i in entities if i.startswith('acq-')]
    #     if acq:
    #         subj_outdir = output_dir.joinpath(entities[0], entities[1], 'anat', acq[0])
    #     else:
    #         subj_outdir = output_dir.joinpath(entities[0], entities[1], 'anat')
    #
    #     prefix = primary_t1.name.split('.')[0]  # filename without the extension
    #
    #     mkdir_cmds = f"mkdir -p {subj_outdir}"  # make output directories within subject directory
    #
    #     # afni commands
    #     refacer = f"@afni_refacer_run -input {primary_t1} -mode_deface -no_clean -prefix {fspath(subj_outdir.joinpath(prefix))}"
    #
    #     full_cmd = ' ; '.join(['module load afni', mkdir_cmds, refacer]) + '\n'
    #     print(full_cmd)
    #     logfile_name = subj_outdir.joinpath('logs', f"{primary_t1.name.split('.')[0]}_log_deface.txt")
    #     if not logfile_name.parent.exists():
    #         logfile_name.parent.mkdir(parents=True)
    #     logfile_obj = open(subj_outdir.joinpath('logs', logfile_name), 'w')
    #     logfile_obj.write(
    #         f"================================ afni_refacer_run command ================================\n"
    #         f"{full_cmd}\n"
    #         f"==========================================================================================\n")
    #     logfile_obj.flush()  # clear file object buffer
    #     print(f"Starting a child process to run afni_refacer on {primary_t1.name}")
    #     run(full_cmd, logfile_obj)
    #     print(f"Child process to run afni_refacer on {primary_t1.name} completed.\n")
    #
    #     # rename afni workdirs
    #     workdir_list = list(subj_outdir.glob('__work_refacer*'))
    #     if len(workdir_list) > 0:
    #         logfile_obj.flush()
    #         new_afni_workdir = rename_afni_workdir(workdir_list[0], logfile_obj)
    #         # register other scans to the primary scan
    #         register.register_to_primary_scan(subj_dir_path, new_afni_workdir, primary_t1, others, logfile_obj)
    #
    #     logfile_obj.write(
    #         f"afni_refacer_run work directory not found. Most probably because the refacer command failed.")
    #     missing_refacer_out = prefix
    #
    #     return missing_refacer_out


def main():
    return None


if __name__ == "__main__":
    main()
