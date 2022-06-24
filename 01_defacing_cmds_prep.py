import argparse
import json
from collections import defaultdict
from os import fspath
from pathlib import Path


def get_args():
    parser = argparse.ArgumentParser(prog='prepare_defacing_cmds',
                                     description='Generate a swarm command file to deface T1w scans for a given BIDS dataset.')

    parser.add_argument('-i', '--input', action='store', dest='input', type=Path, required=True,
                        help='Path to input BIDS dataset.')
    parser.add_argument('-o', '--output', action='store', dest='output', type=Path, required=True,
                        help='Path to output dataset.')
    parser.add_argument('--afni-refacer-options', action='store', dest='afni_refacer_opt',
                        help=f'''Additional options the user would like to add apart from `-mode_deface`, 
                        `-no_clean` and `prefix`. Available @afni_refacer_run options can be found on
                        https://afni.nimh.nih.gov/pub/dist/doc/program_help/@afni_refacer_run.html''')

    args = parser.parse_args()
    return Path(args.input), Path(args.output), args.afni_refacer_opt


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

        # make output directories within subject directory for afni
        afni = subj_outdir / 'afni'
        mkdir_cmds = f"mkdir -p {afni}/{{refacer,skullstrip}}"

        # afni commands
        refacer = f"@afni_refacer_run -input {scan} -mode_deface -no_clean -prefix {fspath(afni.joinpath('refacer', prefix))}"

        skullstrip_prefix = afni.joinpath('skullstrip', prefix + '_skullstrip')
        skullstrip = f"3dSkullStrip -input {scan} -prefix {skullstrip_prefix}.nii.gz -push_to_edge; " \
                     f"fslmaths {skullstrip_prefix}.nii.gz -bin {skullstrip_prefix}_binarized.nii.gz"

        full_cmd = ' ; '.join(
            ["START=`date +%s`", mkdir_cmds, refacer, skullstrip, "STOP=`date +%s`", "RUNTIME=$((STOP-START))",
             "echo ${RUNTIME}"]) + '\n'

        cmds_list.append(full_cmd)

    return cmds_list


def find_scans(subjs: list):
    """
    Find all the T1w and corresponding non-T1w scans for each
    subject and session.

    :parameter subjs: List of paths to subject bids directories

    :return paths_dict: Nested default dictionary with T1s and
    their associated non-T1w scans' info.
    """
    paths_dict = defaultdict(lambda: defaultdict())
    t1_not_found = []
    for subj in subjs:
        subjid = subj.name
        scans = list(subj.glob('ses-*/anat/*nii*'))
        t1_suffix = ('T1w.nii.gz', 'T1w.nii')
        t1s = sorted([s for s in scans if s.name.endswith(t1_suffix)])
        if not t1s:
            t1_not_found.append(subjid)
            primary_t1 = "n/a"
        else:
            primary_t1 = t1s.pop(-1)
        paths_dict[subjid][primary_t1] = [s for s in scans if s != primary_t1]
    return paths_dict, t1_not_found


def main():
    # get command line arguments
    input, output, afni_refacer_opt = get_args()
    script_output_dir = output.joinpath('script_outputs')

    if not script_output_dir.exists():
        script_output_dir.mkdir(exist_ok=True, parents=True)

    # generate a t1 to other scans mapping
    subjs = list(input.glob('sub-*'))
    mapping_dict, missing_t1s = find_scans(subjs)

    # list
    t1_list = [k for i in mapping_dict.keys() for k, v in mapping_dict[i].items() if k != "n/a"]

    # write defacing commands to a swarm file
    defacing_cmds = deface(output, 'anat', t1_list)
    write_cmds_to_file(defacing_cmds, script_output_dir.joinpath(f'defacing_commands_{input.parent.name}.swarm'))

    # writing missing info to file
    with open(script_output_dir.joinpath('missing_t1s.txt'), 'w') as f:
        for s in missing_t1s:
            f.write(s+' \n')

    # writing mapping_dict to file
    human_readable_mapping_dict = defaultdict(dict)

    for subjid, value in mapping_dict.items():
        for t1, others in mapping_dict[subjid].items():
            if t1 != "n/a":
                human_readable_mapping_dict[subjid]["primary_t1"] = t1.name
                human_readable_mapping_dict[subjid]["other_scans"] = [other.name for other in others]
    with open(script_output_dir.joinpath('primary_t1s_to_non-t1s_mapping.json'), 'w') as map_f:
        json.dump(human_readable_mapping_dict, map_f, indent=4)


if __name__ == "__main__":
    main()
