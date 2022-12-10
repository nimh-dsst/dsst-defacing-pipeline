# DSST Defacing Pipeline

The defacing workflow for datasets curated by the Data Science and Sharing Team (DSST) will be completed in three steps. Each of these steps are explained in more detail later in the document.

1. Generate and finalize ["primary" scans](#glossary) to ["other scans'"](#glossary) mapping file. 
2. Deface primary scans
   with [@afni_refacer_run](https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/refacer/refacer_run.html) program
   developed by the AFNI Team. To deface remaining scans in the session, register them to the primary scan and use
   it's defacemask to generate a defaced image.
3. Visually inspect defaced scans with your preferred QC tool. 
4. Fix defacings that failed QC.

## Workflow

**NOTE:** It's assumed throughout this document that the input dataset to defacing algorithm is in BIDS valid format.
Here's an example of a BIDS tree:

```bash
input_bids_dataset
├── dataset_description.json
├── README
├── sub-ON02747
│   └── ses-01
│       ├── anat
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
└── sub-ON99871
```

### **1:** Generate and finalize "primary" scans to "other" scans mapping file.

Generate a mapping file using the `generate_mappings.py` script. Edit the generated mapping file, if necessary. Use the
flowchart below as blueprint while making decisions about or changes to the mapping file. The time and effort required
to complete this step is dependent on the dataset. 

Here's a flow chart of what this process might look like.

![Generate and finalize "primary" scans to "other" scans mapping file.](images/dsst_defacing_wf_fig.png)

Example:

```
$ python generate_mappings.py -i ../datasets/ds000031 -o ./examples                                                                              
==================================
VisualQC's visualqc_t1_mri command
==================================
Run the following command to QC primary scans:
 visualqc_t1_mri -u /Users/arshithab/dsst-defacing-pipeline/examples/visualqc_prep/t1_mri -i /Users/arshithab/dsst-defacing-pipeline/examples/visualqc_prep/id_list_t1.txt -m primary.nii.gz

====================
Dataset Summary
====================
Total number of sessions with 'anat' directory in the dataset: 24
Sessions with 'anat' directory with at least one T1w scan: 22
Sessions without a T1w scan: 2
List of sessions without a T1w scan:
 ['sub-01/ses-053', 'sub-01/ses-016']

Please find the mapping file in JSON format and other helpful logs at /Users/arshithab/dsst-defacing-pipeline/examples
```

For sessions with T1w images, the user can quality check using the visualqc command output by the script. See above for
an example.

### **2:** Actually deface scans.

At this point, a big chunk of the job is done. Run `dsst_defacing_wf.py` script that calls on `deface.py` and `register.py` to
deface scans in the dataset.

Example:

```bash
python dsst_defacing_wf.py -i ../datasets/ds000031 -m examples/primary_to_others_mapping.json -o examples
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


## Glossary

- **Primary Scan:** The best quality T1w scan within a session. For programmatic selection, we assume that the most
  recently acquired T1w scan is of the best quality.
- **Other/Secondary Scans:** All scans *except* the primary scan are grouped together and referred to as "other" or "
  secondary" scans for a given session.
- **[VisualQC](https://raamana.github.io/visualqc):** A suite of QC tools developed by Pradeep Raamana (Assistant
  Professor at University of Pittsburgh). While a noun, it's sometimes also used as a verb to refer to "QC-ing scans
  visually". Within the team, a sentence like "We'll be Visual QC-ing primary scans." means that we'll be eyeball-ing
  the primary scans using VisualQC.


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
