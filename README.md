# DSST SoP for Defacing Anatomical scans

[defacing algorithm notes](https://docs.google.com/presentation/d/1-eNBUjRG89kgq1sxaphNEqWQ3KZQ0kpeCfGQprqlqWo/edit#slide=id.g116908c6bac_0_0)

# bash commands

Following is a list of useful commands that were used in the process of defacing.
 
## 3D render using `fsl_gen_3D`


```bash
$ fsl_gen_3D

Usage: fsl_gen_3D <input> <output> 

       Tool to generate a 3D snapshot of a structural image.
```
Example command to generate 3D renders for a given dataset

```bash
for IN in `ls sub-*/*/anat/*/afni/refacer/__work*/tmp.99.result.deface.nii`; do \
OUT=$(echo $IN | sed "s|.nii|.render|g"); fsl_gen_3D $IN $OUT; \
done;
```

## 3D render using `fsleyes render`

`fsleyes render` offers more flexibility compared to `fsl_gen_3D`. 

```bash 
fsleyes render --scene 3d --rot 45 0 90 --outfile ${OUT}.png ${INPUT}.nii.gz -dr 30 250 -cr 30 500 -in spline -bf 0.225 -r 100 -ns 500
```



# References -

https://afni.nimh.nih.gov/afni/community/board/read.php?1,159053,159053#msg-159053

https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/fsl_anat

https://andysbrainbook.readthedocs.io/en/latest/fMRI_Short_Course/Preprocessing/Skull_Stripping.html
