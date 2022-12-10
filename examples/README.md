# Example Run

## Get Data 
We'll be using the [MyConnectome](https://openneuro.org/datasets/ds000031/versions/1.0.0) dataset to run the pipeline on.

Download data using datalad. More instructions [here](https://openneuro.org/datasets/ds000031/versions/1.0.0/download).
```bash
datalad install https://github.com/OpenNeuroDatasets/ds000031.git
```

Download sessions with `anat` directories in them.

```bash
datalad get sub-01/ses-*/anat
```



