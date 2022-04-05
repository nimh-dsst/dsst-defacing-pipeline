# dsst-defacing-sop

[defacing algorithm notes](https://docs.google.com/presentation/d/1-eNBUjRG89kgq1sxaphNEqWQ3KZQ0kpeCfGQprqlqWo/edit#slide=id.g116908c6bac_0_0)

# BASH Commands

Following is a list of useful commands that were used in the process of defacing.
 
## 3D render using `fsl_gen_3D`

```bash
for IN in `ls sub-*/*/anat/*/afni/refacer/__work*/tmp.99.result.deface.nii`; do \
OUT=$(echo $IN | sed "s|.nii|.render|g"); fsl_gen_3D $IN $OUT; \
done;
```


# References -

https://afni.nimh.nih.gov/afni/community/board/read.php?1,159053,159053#msg-159053

https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/fsl_anat

https://andysbrainbook.readthedocs.io/en/latest/fMRI_Short_Course/Preprocessing/Skull_Stripping.html
