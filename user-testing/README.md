# DSST L&L: User testing of DSST defacing pipeline

The defacing pipeline was developed to streamline the process of de-identifying large BIDS datasets and more importantly, to efficiently verify defacing accuracy by visual inspection. This is still under active development but we'd like to pause and receive some feedback on user-friendliness as it exists on GitHub right now at https://github.com/nih-fmrif/dsst-defacing-pipeline. 

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
2. Load required modules 
```bash
module load afni python # defaults to python v3.8
```
3. Now to the exciting stuff! Let's generate a mapping file: 
```bash
python dsst-defacing-pipeline/generate_mappings.py -i sample_dataset/ -o defaced_sample_dataset
```
4. Time to run the defacing algorithm that uses [@afni_refacer_run](https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/refacer/refacer_run.html) program under the hood. This algorithm can be run serially or parallel-y 

```bash
python dsst-defacing-pipeline/dsst_defacing_wf.py -i sample_dataset/ -m defaced_sample_dataset/primary_to_others_mapping.json -o defaced_sample_dataset
```
For non-NIH folks, the dataset can be downloaded using instructions [here](https://openneuro.org/datasets/ds000031/versions/2.0.2/download). I'd recommend datalad over the other two download methods, however, please note that this can get frustrating pretty quickly. 


