import argparse
from os import fspath
from pathlib import Path


def get_args():
    parser = argparse.ArgumentParser(
        description='Generate a swarm command file to deface T1w scans for a given BIDS dataset.')

    parser.add_argument('-in', action='store', dest='input',
                        help='Path to input BIDS dataset.')

    parser.add_argument('-out', action='store', dest='output',
                        help='Path to output dataset.')

    args = parser.parse_args()
    return Path(args.input), Path(args.output)


def write_cmds_to_file(cmds_list, filepath):
    with open(filepath, 'w') as f:
        for c in cmds_list:
            f.write(c)


def generate_cmds(output_dir, modality, scans_list):
    cmds_list = []
    for scan in scans_list:
        entities = scan.name.split('_')
        acq = [i.split('-')[1] for i in entities if i.startswith('acq-')]
        if acq:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], modality, acq[0])
        else:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], modality)

        # filename without the extensions
        prefix = scan.name.split('.')[0]

        # make output directories within subject directory for afni and fsl programs
        fsl = subj_outdir / 'fsl'
        afni = subj_outdir / 'afni'
        mkdir_cmds = f"mkdir -p {fsl}/{{bet,fsl_deface}} {afni}/{{refacer,skullstrip}}"

        # fsl commands
        fsl_anat = f"fsl_anat -o {fsl.joinpath('fsl')} --nocleanup -i {scan}"
        bet = f"bet {scan} {fsl.joinpath('bet', prefix + '_bet.nii.gz')} -S -d"

        deface_prefix = fsl.joinpath('fsl_deface', prefix)
        fsl_deface = f"fsl_deface {scan} {deface_prefix}_deface -d {deface_prefix}_defacing_mask " \
                     f"-n {deface_prefix}_cropped_struc -m13 {deface_prefix}_orig_2_std -m12 {deface_prefix}_orig_2_cropped " \
                     f"-m23 {deface_prefix}_cropped_2_std"

        # afni commands
        refacer = f"@afni_refacer_run -input {scan} -mode_deface -no_clean -prefix {fspath(afni.joinpath('refacer', prefix))}"

        skullstrip_prefix = afni.joinpath('skullstrip', prefix + '_skullstrip')
        skullstrip = f"3dSkullStrip -input {scan} -prefix {skullstrip_prefix}.nii.gz -push_to_edge; " \
                     f"fslmaths {skullstrip_prefix}.nii.gz -bin {skullstrip_prefix}_binarized.nii.gz"

        full_cmd = '; '.join(
            ["START=`date +%s`", mkdir_cmds, fsl_anat, bet, refacer, skullstrip, fsl_deface,
             "STOP=`date +%s`", "RUNTIME=$((STOP-START))", "echo ${RUNTIME}"]) + '\n'

        cmds_list.append(full_cmd)

    return cmds_list


def main():
    # generate bash commands and write to swarm file
    input, output = get_args()
    t1_scans = [s for s in list(input.glob('sub-*/ses-*/anat/*run-*1*T1w.nii.gz'))]
    defacing_cmds = generate_cmds(output, 'anat', t1_scans)
    write_cmds_to_file(defacing_cmds, f'intermediate_commands_{input.parent.name}.swarm')


if __name__ == "__main__":
    main()
