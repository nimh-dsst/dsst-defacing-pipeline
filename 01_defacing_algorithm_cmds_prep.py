from os import fspath
from pathlib import Path

import constants


def write_cmds_to_file(cmds_list, filepath):
    with open(filepath, 'w') as f:
        for c in cmds_list:
            f.write(c)


def generate_cmds(output_dir, modality, scans_list):
    cmds_list = []
    for scan in scans_list:
        entities = scan.name.split('_')
        subj_outdir = output_dir.joinpath(entities[0], entities[1], modality)

        # make output directories within subject directory for afni_refacer, fsl_bet and fsl_anat outputs
        fa_outdir = subj_outdir / 'fsl_anat'
        ar_outdir = subj_outdir / 'afni_refacer'
        fb_outdir = subj_outdir / 'fsl_bet'
        mkdir_cmds = f"mkdir -p {fa_outdir} {ar_outdir} {fb_outdir}"

        # filename without the extensions
        prefix = scan.name.split('.')[0]

        # individual commands
        fa_cmd = f"fsl_anat -o {subj_outdir} --nocleanup -i {scan}"
        ar_cmd = f"@afni_refacer_run -input {scan} -mode_deface -no_clean -prefix {fspath(ar_outdir.joinpath(prefix))}"
        fb_cmd = f"bet {scan} {fb_outdir.joinpath(prefix + '_bet.nii.gz')} -S -d"

        full_cmd = '; '.join(
            ["START=`date +%s`", mkdir_cmds, fa_cmd, ar_cmd, fb_cmd, "STOP=`date +%s`",
             "RUNTIME=$((STOP-START))", "echo ${RUNTIME}"]) + '\n'

        cmds_list.append(full_cmd)

    return cmds_list


def main():
    # generate bash commands and write to swarm file
    defacing_cmds = generate_cmds(constants.OUTPUTS_DIR, 'anat', constants.T1W_SCANS)
    write_cmds_to_file(defacing_cmds, 'new_algorithm_part1.swarm')


if __name__ == "__main__":
    main()
