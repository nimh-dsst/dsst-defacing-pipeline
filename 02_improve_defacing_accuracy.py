from pathlib import Path


def run_shell_cmd(cmdstr):
    p = subprocess.Popen(cmdstr, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                         encoding='utf8', shell=True)

    return p.stdout.readline().strip()


def preprocess_brainmask(fsl_anat):
    bm = fsl_anat / 'T1_biascorr_brain_mask.nii.gz'
    orig = fsl_anat / 'T1_orig'
    roi2orig = fsl_anat / 'T1_roi2orig.mat'

    # dilate bm with 20 mm box kernel
    dil_bm = bm.split('.')[0] + '_dil15box.nii.gz'
    dil = f"fslmaths {bm} -dilD -kernel box 15 {dil_bm}"

    # apply roi2orig transformation
    dil_bm2orig = dil_bm.split('.')[0] + '2orig.nii.gz'
    to_orig = f"flirt -in {dil_bm} -ref {orig} -applyxfm -init {roi2orig} -out {dil_bm2orig}"

    # run commands
    print(f"Dilating and transforming the brainmask...")
    print(run_command('; '.join([dil, to_orig])))
    if dil_bm2orig.exists():
        return dil_bm2orig
    else:
        return f"Cannot find the dilated and transformed brainmask. Please check your commands."


if __name__ == "__main__":
    # cmd to find the overlap between dil brain mask and dil eye mask
    dil_em = fspath(fb_outdir.joinpath(prefix + '*tmp_eyes7dil.nii.gz'))
    dil_bm = preprocess_brainmask(fa_outdir)
    outfile = fspath(subj_outdir.joinpath(prefix + '_modified_eye_mask'))
    fm_cmd = f"fslmaths {dil_bm} -sub {dil_em} -uthr -1 -mul -1 {outfile}"
