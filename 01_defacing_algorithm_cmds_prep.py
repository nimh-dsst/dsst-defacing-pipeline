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


def deface(output_dir, modality, scans_list):
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

        full_cmd = ' ; '.join(
            ["START=`date +%s`", mkdir_cmds, fsl_anat, bet, refacer, skullstrip, fsl_deface,
             "STOP=`date +%s`", "RUNTIME=$((STOP-START))", "echo ${RUNTIME}"]) + '\n'

        cmds_list.append(full_cmd)

    return cmds_list


def registration(output_dir, anat_dirs, t1_list, non_t1_list):
    # @TODO define t1_mask somewhere/somehow
    cmds = []
    modality = 'anat'
    # @TODO check if anat_dirs and t1_list are of equal length
    for anat_dir in anat_dirs:

        for t1 in t1_list:
            if anat_dir in t1:
                # right now assumes only one T1w per anat_dir
                break

        entities = t1.name.split('_')
        acq = [i.split('-')[1] for i in entities if i.startswith('acq-')]
        if acq:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], modality, acq[0])
        else:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], modality)

        # make output directories within subject directory for fsl flirt
        flirt = subj_outdir / 'fsl' / 'flirt'

        for non_t1 in non_t1_list:
            if anat_dir in non_t1:
                matrix = f"{flirt.joinpath(non_t1.name)}_reg.mat"
                out = f"{flirt.joinpath(non_t1.name)}_reg.nii.gz"
                non_t1_mask = f"{flirt.joinpath(non_t1.name)}_mask.nii.gz"
                defaced_non_t1 = f"{flirt.joinpath(non_t1.name)}_defaced.nii.gz"

                mkdir_cmd = f"mkdir -p {flirt}"

                flirt_cmd = f"""flirt
                                -dof 6
                                -cost mutualinfo
                                -searchcost mutualinfo
                                -in {t1}
                                -ref {non_t1}
                                -omat {matrix}
                                -out {out}
                                """

                applyxfm_cmd = f"""flirt
                                -interp nearestneighbour
                                -applyxfm -init {matrix}
                                -in {t1_mask}
                                -ref {non_t1}
                                -out {non_t1_mask}
                                """

                mask_cmd = f"""fslmaths {non_t1} -mas {non_t1_mask} {defaced_non_t1}"""

                cmds.append(" ; ".join([mkdir_cmd, flirt_cmd, applyxfm_cmd, mask_cmd]) + '\n')

    return cmds


def main():
    # generate commands
    input, output = get_args()

    # @TODO this needs to be a regular expression search
    t1_set = set(list(input.glob('sub-*/ses-*/anat/*_run-*1_*T1w.nii.gz')))
    non_t1_set = set(list(input.glob('sub-*/ses-*/anat/*.nii.gz'))) - t1_set
    anat_dirs = list(input.glob('sub-*/ses-*/anat'))

    # write defacing commands to a swarm file
    defacing_cmds = deface(output, 'anat', list(t1_set))
    write_cmds_to_file(defacing_cmds, f'defacing_commands_{input.parent.name}.swarm')

    # write registration commands to a swarm file
    registration_cmds = registration(output, anat_dirs, list(t1_set), list(non_t1_set))
    write_cmds_to_file(registration_cmds, f'registration_commands_{input.parent.name}.swarm')


if __name__ == "__main__":
    main()
