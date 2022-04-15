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

## Resampling scans into 1mm isotropic images for visualqc

```bash
for i in `cat as_visualqc_arsh.txt`; do 
 for j in `ls $i/{tmp.00.INPUT.nii,tmp.99.result.deface.nii}`; do 
  INPUT=$j; 
  OUTPUT=$(echo $j | sed "s|.nii|_iso_1mm|g"); 
  flirt -interp nearestneighbour -in ${INPUT} -ref ${INPUT} -applyisoxfm 1 -out ${OUTPUT}; 
 done; 
done;
```

## visualqc deface

An example command to setup visualqc deface for autism subtypes dataset
```bash
vqcdeface -u /data/NIMH_scratch/defacing_comparisons/autism_subtypes/defacing_outputs \
-m tmp.00.INPUT_iso_1mm.nii.gz -d tmp.99.result.deface_iso_1mm.nii.gz \
-r tmp.99.result.deface_iso_1mm_render \
-o visualqc -i as_visualqc_arsh.txt
```



# References -

https://afni.nimh.nih.gov/afni/community/board/read.php?1,159053,159053#msg-159053

https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/fsl_anat

https://andysbrainbook.readthedocs.io/en/latest/fMRI_Short_Course/Preprocessing/Skull_Stripping.html
