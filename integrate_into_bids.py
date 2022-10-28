import argparse
import gzip
import json
import subprocess
from pathlib import Path

from bids import BIDSLayout


def parse_arguments():
    parser = argparse.ArgumentParser(description="Does something worth doing.")

    parser.add_argument("-d", "--defacing-outputs-dir", type=Path, action='store', dest='inputdir',
                        help="Path to BIDS-like directory with defaced scans.")
    parser.add_argument("-b", "--bids-dir", type=Path, action='store', dest='outdir',
                        help="Path to directory BIDS directory with original scans.")
    parser.add_argument("-m", "--mapping-file", type=Path, action='store', dest='mapping_file',
                        help="Path to primary_to_others_mapping.json file used for defacing.")

    args = parser.parse_args()
    return args.inputdir, args.outdir, args.mapping_file


def run(cmdstr, logfile):
    """Runs the given command str as shell subprocess. If logfile object is provided, then the stdout and stderr of the
    subprocess is written to the log file.
    :param str cmdstr: A shell command formatted as a string variable.
    :param io.TextIOWrapper logfile: optional, File object to log the stdout and stderr of the subprocess.
    """
    if not logfile:
        subprocess.run(cmdstr, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8', shell=True)
    else:
        subprocess.run(cmdstr, stdout=logfile, stderr=subprocess.STDOUT, encoding='utf8', shell=True)


def main():
    inputdir, outdir, mapping_file = parse_arguments()
    # load sourcedata mapping file as a dictionary
    layout = BIDSLayout(outdir)
    f = open(mapping_file, 'r')
    mapping_data = json.load(f)
    no_workdir = []

    for subj, _ in mapping_data.items():
        for sess, _ in mapping_data[subj].items():  # this won't work if the dataset doesn't have any ses-<index>
            # interested values
            primary = Path(mapping_data[subj][sess]["primary_t1"])
            others = [Path(scan) for scan in mapping_data[subj][sess]["others"]]

            # construct afni workdir path
            primary_file_entities = layout.parse_file_entities(str(primary))
            pattern = "sub-{subject}_ses-{session}_acq-{acquisition}_desc-{description}[_run-0{run}][_mt-{mt}]_{suffix}.nii.gz"

            primary_prefix = primary.name.split('.')[0]
            afni_workdir = f"{subj}/{sess}/anat/{primary_file_entities['acquisition']}/workdir_{primary_prefix}"
            afni_workdir_fpath = inputdir.joinpath(afni_workdir)

            if afni_workdir_fpath.exists():
                # primary t1 processing
                primary_curr_fname = 'tmp.99.result.deface.nii'
                primary_file_entities['description'] = 'defaced'

                # builds absolute path from current directory, so only taking the filename coz full path
                # might not always be accurate
                primary_new_fname = Path(layout.build_path(primary_file_entities, pattern, validate=False)).name

                # convert nii to nii.gz and write to desired destination
                gz_file = outdir.joinpath(subj, sess, 'anat', primary_new_fname)
                if not gz_file.exists():
                    with open(afni_workdir_fpath.joinpath(primary_curr_fname), 'rb') as f_input:
                        with gzip.open(gz_file, 'wb') as f_output:
                            f_output.writelines(f_input)

                # "others" processing
                for scan in others:
                    scan_entities = layout.parse_file_entities(str(scan))
                    curr_fname_prefix = scan.name.split('.')[0]
                    curr_fpath = afni_workdir_fpath.joinpath(curr_fname_prefix, curr_fname_prefix + '_defaced.nii.gz')
                    scan_entities['description'] = 'defaced'
                    # print(scan_entities)
                    scan_new_fname = Path(layout.build_path(scan_entities, pattern, validate=False)).name
                    scan_new_fpath = outdir.joinpath(subj, sess, 'anat', scan_new_fname)
                    # run cp cmd
                    run(f"cp {curr_fpath} {scan_new_fpath};", "")
            else:
                no_workdir.append(afni_workdir_fpath)


if __name__ == "__main__":
    main()

"""
subject key - top level
session key - subdir
'anat' dir
cp over json sidecars from the 
for primary scans - look for 'tmp.99.' files and [almost done]
for other scans - go into the specific directory same as the scan's prefix, 
    find _defaced.nii.gz file
    cp it over to new or existing bids tree with desc entity in filename
"""
