# DSST Defacing Workflow

The defacing workflow for datasets curated by the Data Science and Sharing Team will be completed in three major steps.

1. Determine "primary" scans for each session in the dataset and ensure that they are good quality images.
2. Deface primary scans
   with [@afni_refacer_run](https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/refacer/refacer_run.html) program
   developed by the AFNI Team. To deface remaining scans in the session, register them to the primary scan and use
   it's defacemask to generate a defaced image.
3. Visually QC defaced scans. For scans that fail QC, figure out how to fix them and if they can't be fixed, consider
   excluding the scan from the dataset. @TODO Need a more specific SoP of sorts for this step.

**NOTE:** It's assumed throughout this document that the input dataset to defacing algorithm is in BIDS valid format.

## Terminology

- **Primary Scan:** The best quality T1w scan within a session. For programmatic selection, we assume that the most
  recently acquired T1w scan is of the best quality.
- **Other/Secondary Scans:** All scans *except* the primary scan are grouped together and referred to as "other" or "
  secondary" scans for a given session.
- **[VisualQC](https://raamana.github.io/visualqc):** A suite of QC tools developed by Pradeep Ramanna, an associate
  Professor at
  University of Pittsburgh. While a noun, it's sometimes also used as a verb to refer to "QC-ing scans visually". Within
  the team, a sentence like "We'll be Visual QC-ing primary scans." means that we'll eyeball-ing the primary scans using
  VisualQC.

## Workflow

### STEP 1: Generate and finalize "primary" scans to "other" scans mapping file.

The time and effort required to complete this step is highly dependent on the dataset. For example, some factors it
might depend on are:

1. Do all sessions within the dataset have a T1w scan associated with them? It might require a bit of back and forth
   with the collaborator to figure how to deal with sessions without a T1w scan.
2. What's the general quality of acquired scans? Might depend on the scanner used, age group of participants (children
   might be prone to more head motion in the scanner than adults), QA/QC practices during acquisition, etc.

Here's a flow chart of what this process might look like.

![Generate and finalize "primary" scans to "other" scans mapping file.](images/dsst_defacing_wf_fig.png)

**STEP 1 usage notes**

```bash
```

### STEP 2: Actually deface scans.

At this point, a big chunk of the job is done. Run `main.py` script that calls on `deface.py` and `register.py` to
deface scans in the dataset.

```bash
usage: main.py [-h] --input INPUT --output OUTPUT --mapping-file MAP [--level {group,participant}] [--participant SUBJID]

Deface anatomical scans for a given BIDS dataset.

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
                        Path to input BIDS dataset.
  --output OUTPUT, -o OUTPUT
                        Path to output BIDS dataset with defaced scan.
  --mapping-file MAP, -m MAP
                        Path to primary to other/secondary scans mapping file.
  --level {group,participant}, -l {group,participant}
                        'group': Runs defacing commands, serially, on all subjects in the dataset. 'participant': Runs defacing commands on a single subject and its associated sessions.
  --participant SUBJID, -p SUBJID
                        Subject ID associated with the participant. Since the input dataset is assumed to be BIDS valid, this argument expects subject IDs with 'sub-' prefix.

```

Example:

```bash
```

### STEP 3: Visually QC defaced scans.

**STEP 3 usage notes**

```bash
```

## Meeting Notes

Links to documents used to jot down our thoughts/ideas in the process of testing various tools and procedures

- [Slides from early days of the Project](https://docs.google.com/presentation/d/1-eNBUjRG89kgq1sxaphNEqWQ3KZQ0kpeCfGQprqlqWo/edit#slide=id.g116908c6bac_0_0)
- [Meeting notes with Adam and Dustin](https://docs.google.com/presentation/d/18MnazvqRg5nlVoA8SpqID5F0RzFHjfr40btpudNGOUw/edit#slide=id.g138febac7d2_0_25)

## Dealing with edge cases

**@TODO**
Add solutions or tweaks that the user could have in their arsenal when met with edge cases such as

- [ ] subject-sessions with no T1s.
- [ ] anisotropic mri acquisitions are skewed in Visual QC.

## Types of QC-failures we saw

**@TODO**
[ ] Add screenshots with example failures and a fix if available.

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
