import csv
import json
import subprocess
import time

import numpy as np
import pandas as pd

import constants


def run_command(cmdstr):
    p = subprocess.Popen(cmdstr, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                         encoding='utf8', shell=True)

    return p.stdout.readline().strip()


def get_brainmask_stats(bm_path):
    stats_cmd = f"fslstats {bm_path} -V"
    voxels, volume = run_command(stats_cmd).split(' ')
    return float(voxels), float(volume)


def get_bm_overlap_fm_stats(brainmask, facemask):
    stats_cmd = f"fslstats {brainmask} -k {facemask} -V"
    voxels, volume = run_command(stats_cmd).split(' ')
    return float(voxels), float(volume)


def get_fm_minus_dil_em_stats(facemask, dil_em):
    stats_cmd = f"fslstats {facemask} -k {dil_em} -V"
    voxels, volume = run_command(stats_cmd).split(' ')
    return float(voxels), float(volume)


def get_fm_minus_em_stats(facemask, em):
    stats_cmd = f"fslstats {facemask} -k {em} -V"
    voxels, volume = run_command(stats_cmd).split(' ')
    return float(voxels), float(volume)


def main():
    df_columns = ["subject_id", "acquisition", "brainmask_voxels", "brainmask_volume", "facemask_voxels",
                  "facemask_volume", "brainmask_overlap_facemask_voxels", "brainmask_overlap_facemask_volume",
                  "pc_overlap_bw_facemask_and_brainmask", "leftover_dil_eyemask_voxels", "leftover_dil_eyemask_volume",
                  "leftover_eyemask_voxels", "leftover_eyemask_volume"]
    index_range = range(len(constants.T1W_SCANS))
    df = pd.DataFrame(columns=df_columns, index=index_range)

    idx = 0
    for scan in constants.T1W_SCANS:
        subjid = scan.name.split('_')[0]
        acq = scan.name.split('_')[2].split('-')[1]

        prefix = scan.name.split('.')[0]

        # outdirs for intermediate files
        fa_outdir = constants.OUTPUTS_DIR.joinpath(subjid, 'ses-01', 'anat', 'fsl_anat', acq + '.anat')
        ar_outdir = constants.OUTPUTS_DIR.joinpath(subjid, 'ses-01', 'anat', 'afni_refacer', acq)

        # dilated brainmask in orig space
        brainmask = fa_outdir.parent.joinpath(acq + '_dil15box2orig.nii.gz')

        try:
            ar_wrkdir = list(ar_outdir.glob('__work*'))[0]
            print(subjid, acq)

            df.at[idx, 'subject_id'] = subjid
            df.at[idx, 'acquisition'] = acq

            # brainmask stats
            df.at[idx, 'brainmask_voxels'], df.at[idx, 'brainmask_volume'] = get_brainmask_stats(brainmask)

            # facemask stats
            facemask = ar_wrkdir.joinpath('afni_facemask_binarized.nii.gz')
            facemask_voxel, facemask_volume = run_command(f"fslstats {facemask} -V").split(' ')
            df.at[idx, "facemask_voxels"] = float(facemask_voxel)
            df.at[idx, "facemask_volume"] = float(facemask_volume)

            # brainmask & facemask overlap stats
            cmd_outs = get_bm_overlap_fm_stats(brainmask, facemask)
            df.at[idx, "brainmask_overlap_facemask_voxels"] = cmd_outs[0]
            df.at[idx, "brainmask_overlap_facemask_volume"] = cmd_outs[1]
            df.at[idx, "pc_overlap_bw_facemask_and_brainmask"] = df.at[idx, "brainmask_overlap_facemask_voxels"] / \
                                                                 df.at[idx, 'brainmask_voxels']

            # modified eyemasks, (no overlap with brain mask) and it's overlap with facemask
            dil_em_mod = constants.OUTPUTS_DIR.joinpath(subjid, 'ses-01', 'anat',
                                                        prefix + '_modified_dil_eye_mask.nii.gz')
            em_mod = constants.OUTPUTS_DIR.joinpath(subjid, 'ses-01', 'anat', prefix + '_modified_eye_mask.nii.gz')
            df.at[idx, "leftover_dil_eyemask_voxels"], df.at[
                idx, "leftover_dil_eyemask_volume"] = get_fm_minus_dil_em_stats(facemask, dil_em_mod)

            df.at[idx, "leftover_eyemask_voxels"], df.at[
                idx, "leftover_eyemask_volume"] = get_fm_minus_em_stats(facemask, em_mod)

            print(df.loc[idx, :].tolist())
            print("done.\n")
            idx += 1
        except:
            pass

    df.to_csv(f"evaluation_{time.strftime('%Y-%m-%d')}.csv", quoting=csv.QUOTE_MINIMAL, index=False, header=True)


if __name__ == "__main__":
    main()
