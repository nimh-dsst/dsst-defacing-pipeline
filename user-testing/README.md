# DSST L&L: User testing of DSST defacing pipeline

The defacing pipeline was developed to streamline the process of de-identifying large BIDS datasets and more importantly, to efficiently verify defacing accuracy by visual inspection. This is still under active development, but we'd like to pause and receive some feedback on user-friendliness as it exists on GitHub right now at https://github.com/nih-fmrif/dsst-defacing-pipeline. 

For this session of L&L, we'd like to: 
- Test ease of using [the repo](https://github.com/nih-fmrif/dsst-defacing-pipeline) on a sample dataset
- Receive feedback on how to enhance user-friendliness
- Facilitate a general discussion on defacing practices

To make a hands-on user-testing session less frustrating, NIH folks with biowulf accounts can access the sample subset of [MyConnectome dataset](https://openneuro.org/datasets/ds000031/versions/2.0.2) at `/data/NIMH_scratch/defacing-pipeline-testing`.

# Testing Steps

1. Create a new directory with your nih username and copy over the sample dataset to your directory
```bash
cd /data/NIMH_scratch/defacing-pipeline-testing
mkdir arshithab # replace your NIH username
cp -r sample_data arshithab
cd arshithab
```
2. Load python module and create an output directory 
```bash
module load python # defaults to python v3.8
mkdir output
```
3. Now to the exciting stuff! Let's generate a mapping file: 
```bash
python ../dsst-defacing-pipeline/generate_mappings.py -i sample_dataset/ -o output/
```
4. Time to run the defacing algorithm that uses [@afni_refacer_run](https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/refacer/refacer_run.html) program under the hood. This algorithm can be run serially or parallel-y 

```bash
python ../dsst-defacing-pipeline/dsst_defacing_wf.py -i sample_dataset/ -m output/primary_to_others_mapping.json -o output
```
5. Visual Inspection
To visually inspect the freshly defaced images, I'm using VisualQC on a TurboVNC session. Instructions to set up TurboVNC is available as part of NIH HPC's visual partition docs at https://hpc.nih.gov/docs/svis.html 

    a. [Visual QC installation ](https://raamana.github.io/visualqc/installation.html)
    
    b. [VQC deface command line usage](https://raamana.github.io/visualqc/cli_defacing.html)
    
    c. [VQC defacing algorithm accuracy gallery](https://raamana.github.io/visualqc/gallery_defacing.html)

For non-NIH folks, the dataset can be downloaded using instructions [here](https://openneuro.org/datasets/ds000031/versions/2.0.2/download). I'd recommend datalad over the other two download methods, however, please note that this can get frustrating pretty quickly. 
