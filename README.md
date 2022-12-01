# DSST Defacing Pipeline

The defacing workflow for datasets curated by the Data Science and Sharing Team will be completed in three major steps.

1. Determine "primary" scans for each session in the dataset and ensure that they are good quality images.
2. Deface primary scans
   with [@afni_refacer_run](https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/refacer/refacer_run.html) program
   developed by the AFNI Team. To deface remaining scans in the session, register them to the primary scan and use
   it's defacemask to generate a defaced image.
3. Visually QC defaced scans. For scans that fail QC, figure out how to fix them and if they can't be fixed, consider
   excluding the scan from the dataset after checking with the collaborator. @TODO: Need a more specific SoP of sorts
   for this step.

**NOTE:** It's assumed throughout this document that the input dataset to defacing algorithm is in BIDS valid format.
Here's an example of a BIDS tree:

```bash
input_bids_dataset
├── dataset_description.json
├── README
├── sub-ON02747
│   └── ses-01
│       ├── anat
│       │   ├── sub-ON02747_ses-01_acq-CUBE_T2w.json
│       │   ├── sub-ON02747_ses-01_acq-CUBE_T2w.nii.gz
│       │   ├── sub-ON02747_ses-01_acq-MPRAGE_T1w.json
│       │   ├── sub-ON02747_ses-01_acq-MPRAGE_T1w.nii.gz
│       │   ├── sub-ON02747_ses-01_rec-SCIC_T2starw.json
│       │   └── sub-ON02747_ses-01_rec-SCIC_T2starw.nii.gz
│       ├── func
│       │   ├── sub-ON02747_ses-01_task-rest_dir-forward_bold.json
│       │   ├── sub-ON02747_ses-01_task-rest_dir-forward_bold.nii.gz
│       │   ├── sub-ON02747_ses-01_task-rest_dir-reverse_bold.json
│       │   └── sub-ON02747_ses-01_task-rest_dir-reverse_bold.nii.gz
│       └── perf
│           ├── sub-ON02747_ses-01_asl.json
│           └── sub-ON02747_ses-01_asl.nii.gz
│── sub-ON02811
│── sub-ON03748
...
├── sub-ON99620
└── sub-ON99871

```

## Terminology

- **Primary Scan:** The best quality T1w scan within a session. For programmatic selection, we assume that the most
  recently acquired T1w scan is of the best quality.
- **Other/Secondary Scans:** All scans *except* the primary scan are grouped together and referred to as "other" or "
  secondary" scans for a given session.
- **[VisualQC](https://raamana.github.io/visualqc):** A suite of QC tools developed by Pradeep Raamana (Assistant
  Professor at University of Pittsburgh). While a noun, it's sometimes also used as a verb to refer to "QC-ing scans
  visually". Within the team, a sentence like "We'll be Visual QC-ing primary scans." means that we'll be eyeball-ing
  the primary scans using VisualQC.

## Workflow

### **1:** Generate and finalize "primary" scans to "other" scans mapping file.

Generate a mapping file using the `generate_mappings.py` script. Edit the generated mapping file, if necessary. Use the
flowchart below as reference while making decisions about or changes to the mapping file. The time and effort required
to complete this step is dependent on the dataset. For example:

1. Do all sessions within the dataset have a T1w scan associated with them? If there are sessions without a T1w image,
   then the user will have to decide which other scan in the session is of good enough quality to be used as a primary
   scan. This might require some back and forth with the collaborator we're curating the dataset for.
2. What's the general quality of acquired scans? Might depend on the scanner used, age group of participants (children
   might be prone to more head motion in the scanner than adults), QA/QC practices during acquisition, etc.

Of all the other steps in the workflow, this is the most important one. Most scans that were flagged as `failed` while
QC-ing them at the end were found to be because the primary scan wasn't of good quality which messed up registration of
other/secondary scans within the session.

@TODO: How do we define "good quality"?

Here's a flow chart of what this process might look like.

![Generate and finalize "primary" scans to "other" scans mapping file.](images/dsst_defacing_wf_fig.png)

```
usage: generate_mappings.py [-h] [-i INPUT_DIR] [-o SCRIPT_OUTPUT_DIR]

Generates Primary to "others" mapping file and prints VisualQC's T1 MRI utility command.

    Terminology
    -----------

    "primary scan" : Best quality T1w scan, ideally. If T1s not available, we'll need another strategy to pick a primary scan.
    "other scans" : Apart from the primary scan, every "other" scan within the subject-session anat directory is considered a secondary or "other" scan.

    References
    ----------
    visualqc T1 MRI utility : https://raamana.github.io/visualqc/cli_t1_mri.html

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT_DIR, --input INPUT_DIR
                        Path to input BIDS directory.
  -o SCRIPT_OUTPUT_DIR, --output SCRIPT_OUTPUT_DIR
                        Path to directory that'll contain this script's outputs.

```

Example command and it's stdout:

```
(conda)[arshithab@helix dsst_defacing_wf]$ python generate_mappings.py -i /data/NIMH_scratch/defacing_comparisons/autism_subtypes/bids_20220527 -o examples/
==================================
VisualQC's visualqc_t1_mri command
==================================
Run the following command to QC primary scans:
 visualqc_t1_mri -u /gpfs/gsfs12/users/NIMH_scratch/defacing_comparisons/code/code_refactoring/dsst_defacing_wf/examples/visualqc_prep/t1_mri -i /gpfs/gsfs12/users/NIMH_scratch/defacing_comparisons/code/code_refactoring/dsst_defacing_wf/examples/visualqc_prep/id_list_t1.txt -m primary.nii.gz

====================
Dataset Summary
====================
Total number of sessions in the dataset: 263
Total number of sessions with at least one T1w scan: 250
Total number of sessions WITHOUT a T1w scan: 13
List of sessions without a T1w scan:
 ['sub-NDAREM381WD9/ses-01', 'sub-NDARINVKO353UAS/ses-01', 'sub-NDARBN729RG0/ses-01', 'sub-NDARINVHE728FXQ/ses-01', 'sub-NDARVG708MPB/ses-01', 'sub-NDARINVSE216ZSO/ses-02', 'sub-NDARZN020RY3/ses-04', 'sub-NDARWF021EZF/ses-01', 'sub-NDARBP915LD8/ses-01', 'sub-NDARWE296DLJ/ses-01', 'sub-NDARYN672VGP/ses-02', 'sub-NDARNB146TBN/ses-01', 'sub-NDARTX478BEP/ses-02']

Please find the mapping file in JSON format and other helpful logs at /gpfs/gsfs12/users/NIMH_scratch/defacing_comparisons/code/code_refactoring/dsst_defacing_wf/examples.
```

For sessions with T1w images, the user can quality check using the visualqc command output by the script. See above for
an example.

### **2:** Actually deface scans.

At this point, a big chunk of the job is done. Run `main.py` script that calls on `deface.py` and `register.py` to
deface scans in the dataset.

```
usage: main.py [-h] --input INPUT --output OUTPUT --mapping-file MAPPING [--subject-id SUBJID]

Deface anatomical scans for a given BIDS dataset or a subject directory in BIDS format.

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
                        Path to input BIDS dataset.
  --output OUTPUT, -o OUTPUT
                        Path to output BIDS dataset with defaced scan.
  --mapping-file MAPPING, -m MAPPING
                        Path to primary to other/secondary scans mapping file.
  --subject-id SUBJID, -s SUBJID
                        Subject ID associated with the participant. Since the input dataset is assumed to be BIDS valid, this argument expects subject IDs with 'sub-' prefix.

```

Example:

```bash
python main.py -i /data/NIMH_scratch/defacing_comparisons/code/code_refactoring/defacing_wf_data/as_toy_data/ -o output_testing/ -m scripts_outputs/primary_to_others_mapping.json
```

### **3:** Visually QC defaced scans.

To use VisualQC, the command line utilities will need to be installed. Please refer
to [VisualQC's documentation](https://raamana.github.io/visualqc/installation.html) for
installation instructions.

#### Primary Scans

The following criteria was used to judge the success of defacing:

* No brain tissue had been removed during defacing
* The 3D render didn’t contain more than one partial feature (eyes, nose or mouth)

Example:

```bash
vqcdeface -u /data/NIMH_scratch/defacing_comparisons/autism_subtypes/defacing_outputs \
-m tmp.00.INPUT_iso_1mm.nii.gz -d tmp.99.result.deface_iso_1mm.nii.gz \
-r tmp.99.result.deface_iso_1mm_render \
-o visualqc -i as_visualqc_arsh.txt
```

#### "Other"/Secondary Scans

Evaluate registration accuracy of ["other"](#terminology) scans within the session to the chosen primary scan.

```bash
```

## References

1. Theyers AE, Zamyadi M, O'Reilly M, Bartha R, Symons S, MacQueen GM, Hassel S, Lerch JP, Anagnostou E, Lam RW, Frey
   BN, Milev R, Müller DJ, Kennedy SH, Scott CJM, Strother SC, and Arnott SR (2021)
   [Multisite Comparison of MRI Defacing Software Across Multiple Cohorts](10.3389/fpsyt.2021.617997). Front. Psychiatry
   12:617997. doi:10.3389/fpsyt.2021.617997
2. The workflow is developed around
   the [AFNI Refacer program](https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/refacer/refacer_run.html).
3. FSL's [`flirt`](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FLIRT)
   and [`fslmaths`](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Fslutils?highlight=%28fslmaths%29) programs have been used
   for registration and masking steps in the workflow.
4. [VisualQC's T1 MRI](https://raamana.github.io/visualqc/gallery_t1_mri.html) utility.
5. [VisualQC's defacing accuracy checker](https://raamana.github.io/visualqc/gallery_defacing.html) utility.
6. [VisualQC's alignment quality checker](https://raamana.github.io/visualqc/gallery_registration_unimodal.html)
   utility.
7. [Skullstripping](https://andysbrainbook.readthedocs.io/en/latest/fMRI_Short_Course/Preprocessing/Skull_Stripping.html)
8. [Relevant thread about 3dSkullStrip on AFNI message board](https://afni.nimh.nih.gov/afni/community/board/read.php?1,159053,159053#msg-159053)

## Acknowledgements

We'd like to thank [Pradeep Raamana](https://www.aimi.pitt.edu/people/ant), Assistant Professor at the Department of
Radiology at University of Pittsburgh, and [Paul Taylor](https://afni.nimh.nih.gov/Staff), Acting Director of Scientific
and Statistical Computing Core (SSCC) at NIMH for their timely help in resolving and adapting VisualQC and AFNI Refacer,
respectively, for the specific needs of this project.

@TODO: Revise wording here. 
