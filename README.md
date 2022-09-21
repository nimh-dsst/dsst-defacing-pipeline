# DSST Defacing Workflow

## Workflow Diagram

### STEP 1
![Generate and finalize "primary" scans to "other" scans mapping file.](images/generate_mappings.png)

1. Run [@afni_refacer_run](https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/refacer/refacer_run.html) on **a T1w scan per subject** of a given dataset. 
2. [VisualQC](https://raamana.github.io/visualqc/gallery_defacing.html) defaced T1 images and correct/flag any that fail the QC Criteria. 
3. Register other **T1w and non-T1w scans** of each subject to the T1w image in step 1 and apply its defacemask to the remaining scans. 
4. QC the scans from 3 using [VisualQC Align](https://raamana.github.io/visualqc/gallery_defacing.html)

## Instructions

**Step 1:** Run `01_defacing_cmds_prep.py`
Usage:
```bash
python 01_defacing_cmds_prep.py -i <path/to/input/bids/dataset> -o <path/to/output/directory>
```
The script requires two arguments:
  1. `-i/--input` Path to BIDS format dataset.
  2. `-o/--output` Path to output directory where the defaced scans will be stored. 

and outputs three files at `{OUTPUT_DIR}/script_outputs/`
  1. a `.swarm` file named `defacing_commands_{INPUT_DIRNAME}.swarm` with commands to deface T1w scans using @afni_refacer_run
  2. a `missing_t1.txt` file that lists subject-sessions that don't have an associated T1w scan.
  3. a `primary_t1s_to_non-t1s_mapping.json` mapping file that maps each subject and session with their primary T1w scan and
  a list of other T1w runs and non T1w scans. 
     - **"primary_t1"** is a T1w scan within the subject's session that's defaced with @afni_refacer_run.
     - **"other_scans"** refers to all other scans in the subject's session's `anat` directory apart from the T1 above. 
  Here's an example:
  ```json
{
  "sub-A": {
    "ses-01": {
      "primary_t1": "sub-A_ses-01_run-1_T1w.nii.gz",
      "other_scans": [
        "sub-A_ses-01_acq-axlowres_run-01_T2w.nii.gz",
        "sub-A_ses-01_acq-axlowres_run-01_PDw.nii.gz"]
    },
    "ses-02": {
      "primary_t1": "sub-A_ses-02_run-01_T1w.nii.gz",
      "other_scans": [
        "sub-A_ses-02_acq-axlowres_run-01_T2w.nii.gz",
        "sub-A_ses-02_acq-axlowres_run-01_FLAIR.nii.gz"]
    }
  }
}
```

**Step 2:** Run `02_registration_and_masking_cmds_prep.py`

Usage:
```bash
python 02_registration_and_masking_cmds_prep.py -i <path/to/input/bids/dataset> -o <path/to/output/directory> --mapping-file <path/to/json/file/mapping/primary/t1/to/other/scans>
```

The script requires two arguments:
1. `-i/--input` Path to BIDS format dataset.
2. `-o/--output` Path to output directory where the defaced scans will be stored.
3. `--mapping-file` Path to JSON file that maps 'primary T1s' to 'other scans'.

and outputs two files at `{OUTPUT_DIR}/script_outputs/`
1. a `.swarm` file named `registration_masking_commands_{INPUT_DIRNAME}.swarm` that contains commands to register "other_scans" to their respective "primary_t1" and apply primary_t1's defacemask to the registered scans using FSL tools.
2. a `missing_afni_workdir.txt` file that lists "primary_t1" scans that (for whatever reason) failed to be defaced afni refacer run.

**Step 3:** Generate 3D renders for VisualQC.

@TODO
- [ ] Add screenshots of visual qc deface as examples of the screen view. [Arsh]
- [ ] Detail how to use 03_vqc_generate_renders script. [Arsh]
- [ ] An example afni_workdir directory tree after generating renders. [Arsh]
- [ ] Explain the Visual QC deface command and it's components. [Eric]
- [ ] Similarly for Visual QC Align [Eric]

## VisualQC Deface Prep Commands

Following is a list of useful commands that were used in the process of defacing.

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

## Dealing with edge cases
**@TODO**
Add solutions or tweaks that the user could have in their arsenal when met with edge cases such as 
- [ ] subject-sessions with no T1s.
- [ ] anisotropic mri acquisitions are skewed in Visual QC. 

## Types of QC-failures we saw
**@TODO**
[ ]Add screenshots with example failures and a fix if available. 

## References
**@TODO**
- [ ] Links to afni_refacer_run, fsl flirt, fslmaths and visual qc documents. 
- [ ] other links with useful information about defacing example papers etc 

https://afni.nimh.nih.gov/afni/community/board/read.php?1,159053,159053#msg-159053

https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/fsl_anat

https://andysbrainbook.readthedocs.io/en/latest/fMRI_Short_Course/Preprocessing/Skull_Stripping.html

## Acknowledgements
**@TODO** 
Acknowledge
- [ ] Pradeep Ramanna
- [ ] Paul Taylor and AFNI team
