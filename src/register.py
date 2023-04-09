import subprocess


def run_command(cmdstr, logfile):
    if not logfile:
        logfile = subprocess.PIPE
    subprocess.run(cmdstr, stdout=logfile, stderr=subprocess.STDOUT, encoding='utf8', shell=True)


def preprocess_facemask(fmask_path, logfile_obj):
    prefix = fmask_path.parent.joinpath('afni_facemask')
    defacemask = fmask_path.parent.joinpath('afni_defacemask.nii.gz')

    # load fsl module
    c0 = f"module load fsl"

    # split the 4D volume
    c1 = f"fslroi {fmask_path} {prefix} 1 1"

    # arithmetic on the result from above
    c2 = f"fslmaths {prefix}.nii.gz -abs -binv {defacemask}"
    print(f"Splitting the facemask volume at {fmask_path} and binarizing the resulting volume... \n ")
    run_command('; '.join([c0, c1, c2]), logfile_obj)
    try:
        if defacemask.exists():
            return defacemask
    except OSError as err:
        print(f"OS Error: {err}")
        print(
            f"Cannot find the binarized facemask. Please check is fsl module is loaded before running the script again.")
        raise


def get_intermediate_filenames(outdir, prefix):
    mat = f"{outdir.joinpath(prefix)}_reg.mat"
    reg_out = f"{outdir.joinpath('registered.nii.gz')}"
    mask = f"{outdir.joinpath(prefix)}_mask.nii.gz"
    defaced_out = f"{outdir.joinpath(prefix)}_defaced.nii.gz"
    return mat, reg_out, mask, defaced_out


def register_to_primary_scan(subj_dir, afni_workdir, primary_scan, other_scans_list, log_fileobj):
    log_fileobj.flush()
    modality = "anat"

    # preprocess facemask
    raw_facemask_volumes = afni_workdir.joinpath('tmp.05.sh_t2a_thr.nii')
    t1_mask = preprocess_facemask(raw_facemask_volumes, log_fileobj)

    for other in other_scans_list:
        log_fileobj.flush()
        entities = other.split('_')

        # changing other scan name to other scan full path
        other = subj_dir.joinpath(entities[1], modality, other)
        other_prefix = other.name.split('.')[0]  # filename without the extension
        other_outdir = afni_workdir.joinpath(other_prefix)

        matrix, reg_out, other_mask, other_defaced = get_intermediate_filenames(other_outdir, other_prefix)

        mkdir_cmd = f"mkdir -p {other_outdir}; cp {other} {other_outdir.joinpath('original.nii.gz')}"

        flirt_cmd = f"flirt -dof 6 -cost mutualinfo -searchcost mutualinfo -in {primary_scan} "f"-ref {other} -omat {matrix} -out {reg_out}"

        # t1 mask can be found in the afni work directory
        applyxfm_cmd = f"flirt -interp nearestneighbour -applyxfm -init {matrix} "f"-in {t1_mask} -ref {other} -out {other_mask}"

        mask_cmd = f"fslmaths {other} -mas {other_mask} {other_defaced}"
        full_cmd = " ; ".join(["module load fsl", mkdir_cmd, flirt_cmd, applyxfm_cmd, mask_cmd]) + '\n'
        run_command(full_cmd, log_fileobj)
