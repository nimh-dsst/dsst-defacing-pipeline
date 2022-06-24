import argparse
import json
from os import fspath
from pathlib import Path


def get_args():
    parser = argparse.ArgumentParser(prog='prepare_defacing_cmds',
                                     description='Generate a swarm command file to deface T1w scans for a given BIDS dataset.')

    parser.add_argument('-i', '--input', action='store', dest='input', type=Path, required=True,
                        help='Path to input BIDS dataset.')
    parser.add_argument('-o', '--output', action='store', dest='output', type=Path, required=True,
                        help='Path to output dataset.')
    parser.add_argument('--mapping-file', action='store', dest='mapping_file', type=Path, required=True,
                        help="Path to JSON file that maps primary T1w scans to 'other' (additional runs of T1w and "
                             "non-T1w anatomical scans) 'primary_t1s_to_non-t1s_mapping.json'.")

    args = parser.parse_args()
    return args.input, args.output, args.mapping_file


def write_cmds_to_file(cmds_list, filepath):
    with open(filepath, 'w') as f:
        for c in cmds_list:
            f.write(c)


def registration(output_dir, mapping_dict):
    afni_workdir_not_found = []
    cmds = []
    modality = 'anat'
    for subj in mapping_dict.keys():
        t1 = Path(mapping_dict[subj]['primary_t1'])
        others = [Path(s) for s in mapping_dict[subj]['other_scans']]
        entities = t1.name.split('_')
        acq = [i.split('-')[1] for i in entities if i.startswith('acq-')]
        if acq:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], modality, acq[0])
        else:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], modality)

        flirt = subj_outdir / 'flirt'

        # make output directories within subject directory for fsl flirt
        afni_workdir = list(subj_outdir.joinpath('afni', 'refacer').glob('__work*'))
        if not afni_workdir:
            afni_workdir_not_found.append(t1.name)
        else:
            t1_mask = afni_workdir[0].joinpath('afni_defacemask.nii.gz')
            for other in others:
                other_prefix = other.name.split('.')[0]
                matrix = f"{flirt.joinpath(other_prefix)}_reg.mat"
                out = f"{flirt.joinpath(other_prefix)}_reg.nii.gz"
                other_mask = f"{flirt.joinpath(other_prefix)}_mask.nii.gz"
                other_defaced = f"{flirt.joinpath(other_prefix)}_defaced.nii.gz"

                mkdir_cmd = f"mkdir -p {flirt}"

                flirt_cmd = f"flirt -dof 6 -cost mutualinfo -searchcost mutualinfo -in {t1} " \
                            f"-ref {other} -omat {matrix} -out {out}"

                # t1 mask can be found in the afni work directory
                applyxfm_cmd = f"flirt -interp nearestneighbour -applyxfm -init {matrix} " \
                               f"-in {t1_mask} -ref {other} -out {other_mask}"

                mask_cmd = f"fslmaths {other} -mas {other_mask} {other_defaced}"
                full_cmd = " ; ".join([mkdir_cmd, flirt_cmd, applyxfm_cmd, mask_cmd]) + '\n'
                cmds.append(full_cmd)

    return cmds, afni_workdir_not_found


def main():
    # get command line arguments
    input, output, mapping_file = get_args()

    # list
    mapping_file_pointer = open(fspath(mapping_file), 'r')
    data = json.load(mapping_file_pointer)

    # write registration commands to a swarm file
    registration_cmds, missing_afni_workdirs = registration(output, data)
    write_cmds_to_file(registration_cmds, output.joinpath(f'registration_commands_{input.parent.name}.swarm'))

    # write list of t1s without afni workdirs to file
    filename = output.joinpath('script_outputs', 'missing_afni_workdirs.txt')
    with open(filename, 'w') as f:
        for t1 in missing_afni_workdirs:
            f.write(t1+' \n')


if __name__ == "__main__":
    main()
