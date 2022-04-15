import argparse
import json
import subprocess
from collections import defaultdict
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


def run_command(cmdstr):
    p = subprocess.Popen(cmdstr, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                         encoding='utf8', shell=True)

    return p.stdout.readline().strip()


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


def registration(output_dir, t1_list, scans_dict):
    # @TODO define t1_mask somewhere/somehow
    afni_wrkdir_not_found = []
    cmds = []
    modality = 'anat'
    for t1 in t1_list:
        entities = t1.name.split('_')
        subjid = entities[0]
        # print(subjid)
        others = scans_dict[subjid][t1]
        acq = [i.split('-')[1] for i in entities if i.startswith('acq-')]
        if acq:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], modality, acq[0])
        else:
            subj_outdir = output_dir.joinpath(entities[0], entities[1], modality)

        flirt = subj_outdir / 'flirt'
        # make output directories within subject directory for fsl flirt
        afni_wrkdir = list(subj_outdir.joinpath('afni', 'refacer').glob('__work*'))
        if not afni_wrkdir:
            afni_wrkdir_not_found.append(t1.name)
        else:
            t1_mask = afni_wrkdir[0].joinpath('afni_defacemask.nii.gz')
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

    return cmds, afni_wrkdir_not_found


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
    input, output = get_args()

    # track missing files and directories
    missing = dict()

    # generate a t1 to other scans mapping
    subjs = list(input.glob('sub-*'))
    mapping_dict, missing_t1s = find_scans(subjs)

    # list
    t1_list = [k for i in mapping_dict.keys() for k, v in mapping_dict[i].items() if k != "n/a"]

    # write defacing commands to a swarm file
    defacing_cmds = deface(output, 'anat', t1_list)
    write_cmds_to_file(defacing_cmds, f'defacing_commands_{input.parent.name}.swarm')

    # write registration commands to a swarm file
    registration_cmds, missing_afni_wrkdirs = registration(output, t1_list, mapping_dict)
    write_cmds_to_file(registration_cmds, f'registration_commands_{input.parent.name}.swarm')

    # writing missing info to file
    missing["T1w scans"] = missing_t1s
    missing["afni workdirs"] = missing_afni_wrkdirs
    with open('missing_info.json', 'w') as f:
        json.dump(missing, f, indent=4)

    # writing mapping_dict to file
    human_readable_mapping_dict = defaultdict(dict)

    for subjid, value in mapping_dict.items():
        for t1, others in mapping_dict[subjid].items():
            if t1 != "n/a":
                human_readable_mapping_dict[subjid]["primary_t1"] = t1.name
                human_readable_mapping_dict[subjid]["other_scans"] = [other.name for other in others]
    print(len(human_readable_mapping_dict.keys()))
    with open('primary_t1s_to_non-t1s_mapping.json', 'w') as map_f:
        json.dump(human_readable_mapping_dict, map_f, indent=4)


if __name__ == "__main__":
    main()
