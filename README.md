# DSST Defacing Workflow

1. Run [@afni_refacer_run](https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/refacer/refacer_run.html) on **a T1w scan per subject** of a given dataset. 
2. [VisualQC](https://raamana.github.io/visualqc/gallery_defacing.html) defaced T1 images and correct/flag any that fail the QC Criteria. 
3. Register other **T1w and non-T1w scans** of each subject to the T1w image in step 1 and apply its defacemask to the remaining scans. 

## Defacing Workflow Instructions

**Step 1**

The `01_defacing_algorithm_cmds_prep.py` script outputs two `.swarm` files with following filenames:
  1. `defacing_commands_{input-directory-name}.swarm`
  2. `registration_commands_{input-directory-name}.swarm`

```bash
(base) arshitha@Personal-MacBook dsst-defacing-sop % python 01_defacing_algorithm_cmds_prep.py -h
usage: 01_defacing_algorithm_cmds_prep.py [-h] [-in INPUT] [-out OUTPUT]

Generate a swarm command file to deface T1w scans for a given BIDS dataset.

optional arguments:
  -h, --help   show this help message and exit
  -in INPUT    Path to input BIDS dataset.
  -out OUTPUT  Path to output dataset.

```

**Step 2**

Run `defacing_commands_{input-directory-name}.swarm` through an interactive session on biowulf. Example command: 

```bash
swarm -f <path/to/defacing_commands_{input-directory-name}.swarm> --module afni --logdir <path/to/swarm/logdir> --job-name afni_refacer_t1_defacing --merge-output 
```

## VisualQC Deface Prep Commands

Following is a list of useful commands that were used in the process of defacing.

- **Generating 3D renders for QC** 

  - **`fsl_gen_3D`**

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

  - **`fsleyes render`**

      Offers more flexibility compared to `fsl_gen_3D`. 
    
      ```bash 
      fsleyes render --scene 3d --rot 45 0 90 --outfile ${OUT}.png ${INPUT}.nii.gz -dr 30 250 -cr 30 500 -in spline -bf 0.225 -r 100 -ns 500
      ```

- **Resampling**

    Anisotropic images were resampled to 1mm isotropic images to improve VisualQC's display. This is temporary fix while matplotlib's display issues can be resolved.

    ```bash
    for i in `cat as_visualqc_arsh.txt`; do 
     for j in `ls $i/{tmp.00.INPUT.nii,tmp.99.result.deface.nii}`; do 
      INPUT=$j; 
      OUTPUT=$(echo $j | sed "s|.nii|_iso_1mm|g"); 
      flirt -interp nearestneighbour -in ${INPUT} -ref ${INPUT} -applyisoxfm 1 -out ${OUTPUT}; 
     done; 
    done;
    ```

- **Launching VisualQC**

    An example command to setup visualqc deface for autism subtypes dataset
    ```bash
    vqcdeface -u /data/NIMH_scratch/defacing_comparisons/autism_subtypes/defacing_outputs \
    -m tmp.00.INPUT_iso_1mm.nii.gz -d tmp.99.result.deface_iso_1mm.nii.gz \
    -r tmp.99.result.deface_iso_1mm_render \
    -o visualqc -i as_visualqc_arsh.txt
    ```

## Meeting Notes
Links to documents used to jot down our thoughts/ideas in the process of testing various tools and procedures 

- [Slides from early days of the Project](https://docs.google.com/presentation/d/1-eNBUjRG89kgq1sxaphNEqWQ3KZQ0kpeCfGQprqlqWo/edit#slide=id.g116908c6bac_0_0)

## References

https://afni.nimh.nih.gov/afni/community/board/read.php?1,159053,159053#msg-159053

https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/fsl_anat

https://andysbrainbook.readthedocs.io/en/latest/fMRI_Short_Course/Preprocessing/Skull_Stripping.html
