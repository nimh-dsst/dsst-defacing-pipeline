import json
import subprocess
from os import fspath
from pathlib import Path

import register

root = Path('/data/NIMH_scratch/defacing_comparisons/code/code_refactoring')
bids_toy_data = root.joinpath('toy_dataset')
output_dir = root.joinpath('toy_dataset_defaced')
if not output_dir.exists():
    output_dir.mkdir(parents=True)


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


def deface_primary_scan(subj_dir_path, mapping_dict, output_dir):
    subjid = subj_dir_path.name
    subj_sess_paths = list(subj_dir_path.glob('ses-*'))

    for subj_sess_path in subj_sess_paths:
        t1_sidecars = list(subj_sess_path.glob('anat/*T1w.json'))
        t1_acq_time_dict = dict()
        for sidecar in t1_sidecars:
            sidecar_fobj = open(sidecar, 'r')
            data = json.load(sidecar_fobj)
            t1_acq_time_dict[sidecar] = data["AcquisitionTime"]

        t1_acq_time_list = sorted(t1_acq_time_dict.items(), key=lambda key_val_tup: key_val_tup[1], reverse=True)

        # latest T1w scan in the session based on acquisition value
        nifti_fname = t1_acq_time_list[0][0].name.split('.')[0] + '.nii.gz'
        primary_t1 = t1_acq_time_list[0][0].parent.joinpath(nifti_fname)

        # TODO: Find a QC-based criteria for picking a T1w and provide the user the option to specify their preferrred T1w image for each subj
        others = [str(s) for s in list(subj_sess_path.glob('anat/*.nii*')) if s != primary_t1]

        # update primary t1 to others mapping
        mapping_dict[f"{subjid}/{subj_sess_path.name}"]['primary_t1'] = str(primary_t1)
        mapping_dict[f"{subjid}/{subj_sess_path.name}"]['others'] = others

        # constructing afni refacer command
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
        missing_refacer_out = None
        if len(workdir_list) > 0:
            logfile_obj.flush()
            new_afni_workdir = rename_afni_workdir(workdir_list[0], logfile_obj)

            # register other scans to the primary scan
            register.register_to_primary_scan(subj_dir_path, new_afni_workdir, primary_t1, others, logfile_obj)
        else:
            f"afni_refacer_run work directory not found. Most probably because the refacer command failed."
            missing_refacer_out = prefix

    return mapping_dict, missing_refacer_out


def main():
    return None


if __name__ == "__main__":
    main()
