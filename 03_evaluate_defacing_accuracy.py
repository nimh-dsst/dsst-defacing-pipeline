# evaluation step
# fslmaths fslanat_bm2orig.nii.gz -sub afni_inv_facemask_plugged.nii.gz -thr 0 bm_min_ifm
# fslstats bm_min_ifm -V
