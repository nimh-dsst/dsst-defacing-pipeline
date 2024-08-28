import utils


def preprocess_facemask(fmask_path, subj_logger):
    prefix = fmask_path.parent.joinpath('afni_facemask')
    defacemask = fmask_path.parent.joinpath('afni_defacemask.nii.gz')

    # split the 4D volume
    c1 = f"fslroi {fmask_path} {prefix} 1 1"

    # arithmetic on the result from above
    c2 = f"fslmaths {prefix}.nii.gz -abs -binv {defacemask}"
    subj_logger.info(f"Generating a defacemask\n")
    out, err = utils.run_command('; '.join([c1, c2]))
    subj_logger.info(out)
    if err:
        subj_logger.error(err)
        raise Exception(f"Error in generating deface mask: {err}")
    try:
        if defacemask.exists():
            return defacemask
    except OSError as err:
        subj_logger.error(f"OS Error: {err}")
        subj_logger.error(
            f"Cannot find the binarized facemask. Please check is fsl module is loaded before running the script again.")
        raise


def get_intermediate_filenames(outdir, prefix):
    mat = f"{outdir / prefix}_reg.mat"
    reg_out = f"{outdir / prefix}_registered.nii.gz"
    mask = f"{outdir / prefix}_mask.nii.gz"
    defaced_out = f"{outdir / prefix}_defaced.nii.gz"
    return mat, reg_out, mask, defaced_out


def register_to_primary_scan(subj_dir, afni_workdir, primary_scan, other_scans_list, subj_logger):
    modality = "anat"

    # preprocess facemask
    raw_facemask_volumes = afni_workdir.joinpath('tmp.05.sh_t2a_thr.nii')
    t1_mask = preprocess_facemask(raw_facemask_volumes, subj_logger)

    if other_scans_list:
        for other in other_scans_list:
            entities = other.split('_')

            # changing other scan name to other scan full path
            other = subj_dir.joinpath(entities[1], modality, other)
            other_prefix = other.name.split('.')[0]  # filename without the extension
            other_outdir = afni_workdir.joinpath(other_prefix)

            matrix, reg_out, other_mask, other_defaced = get_intermediate_filenames(other_outdir, other_prefix)

            other_outdir.mkdir(parents=True, exist_ok=True)
            cp_cmd = f"cp {other} {other_outdir / other_prefix}"

            flirt_cmd = f"flirt -dof 6 -cost mutualinfo -searchcost mutualinfo -in {primary_scan} -ref {other} -omat {matrix} -out {reg_out}"

            # t1 mask can be found in the afni work directory
            applyxfm_cmd = f"flirt -interp nearestneighbour -applyxfm -init {matrix} -in {t1_mask} -ref {other} -out {other_mask}"

            mask_cmd = f"fslmaths {other} -mas {other_mask} {other_defaced}"

            full_cmd = " ; ".join(["module load fsl", cp_cmd, flirt_cmd, applyxfm_cmd, mask_cmd]) + '\n'

            subj_logger.info(f"Registering {other.name} to {primary_scan.name} and applying defacemask...")
            out, err = utils.run_command(full_cmd)
            subj_logger.info(out)
            if err:
                subj_logger.error(err)
                raise Exception(f"Error in registering {other.name} to {primary_scan.name}: {err}")
