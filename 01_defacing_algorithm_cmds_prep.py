import argparse
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


def find_scans(subjs: list):
    """
    Find all the T1w and corresponding non-T1w scans for each
    subject and session.

    :parameter subjs: List of paths to subject bids directories

    :return paths_dict: Nested default dictionary with T1s and
    their associated non-T1w scans' info.

    Example of a nested dictionary -
    paths_dict = {
        "sub-01":{
            "ses-01":{
                "sub-01_ses-01_run-01_T1w.nii.gz":[
                    "sub-01_ses-01_run-02_T1w.nii.gz",
                    "sub-01_ses-01_run-01_T2w.nii.gz",
                    "sub-01_ses-01_run-01_PDw.nii.gz"]
                    }
                }
            }
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

        paths_dict[subjid]["t1"] = primary_t1
        paths_dict[subjid]["others"] = [s for s in scans if s != primary_t1]
    return paths_dict


def main():
    # generate commands
    input, output = get_args()
    subjs = list(input.glob('sub-*'))
    paths_info_dict = find_scans(subjs)

    t1_set = [paths_info_dict[i]["t1"] for i in paths_info_dict.keys() if paths_info_dict[i]["t1"] != "n/a"]
    print(len(t1_set))

    # write defacing commands to a swarm file
    # defacing_cmds = deface(output, 'anat', list(t1_set))
    # write_cmds_to_file(defacing_cmds, f'defacing_commands_{input.parent.name}.swarm')
    #
    # # write registration commands to a swarm file
    # registration_cmds = registration(output, anat_dirs, list(t1_set), list(non_t1_set))
    # write_cmds_to_file(registration_cmds, f'registration_commands_{input.parent.name}.swarm')


if __name__ == "__main__":
    main()
