#!/usr/local/bin/python3
"""
Generates 3D renders of defaced images using FSLeyes. More info on FSLeyes can be found\
 https://open.win.ox.ac.uk/pages/fsl/fsleyes/fsleyes/userdoc/install.html#install-from-conda-forge-recommended
"""
import argparse
import re
import subprocess
from multiprocessing.pool import Pool
from pathlib import Path


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description=__doc__)

    parser.add_argument('-o', '--output', type=Path, action='store', dest='outdir', metavar='OUTPUT_DIR',
                        default=Path('.'), help="Path to defacing outputs directory.")
    parser.add_argument('-n', '--n-cpus', type=int, default=1,
                        help='Number of parallel processes to run. '
                             'Defaults to 1, meaning "serial processing" when not provided.')
    return parser.parse_args()


def run_command(cmdstr):
    """Runs the given command str as shell subprocess.
    :param str cmdstr: A shell command formatted as a string variable.
    """
    p = subprocess.run(cmdstr, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8', shell=True)
    print(p.stdout)


def construct_vqcdeface_cmd(qc_dir):
    rel_paths_to_orig = [re.sub('/orig.nii.gz', '', str(o.relative_to(qc_dir))) for o in qc_dir.rglob('orig.nii.gz')]
    with open(qc_dir / 'defacing_id_list.txt', 'w') as f:
        f.write('\n'.join(rel_paths_to_orig))

    vqcdeface_cmd = f"vqcdeface -u {qc_dir} -i {qc_dir / 'defacing_id_list.txt'} -m orig.nii.gz -d defaced.nii.gz -r defaced_render"

    return vqcdeface_cmd


def generate_3d_renders(defaced_img, render_outdir):
    rotations = [(45, 5, 10), (-45, 5, 10)]
    for idx, rot in enumerate(rotations):
        yaw, pitch, roll = rot[0], rot[1], rot[2]
        outfile = render_outdir.joinpath('defaced_render_0' + str(idx) + '.png')
        if not outfile.exists():
            if 'T2w' in render_outdir.parts:
                fsleyes_render_cmd = f"fsleyes render --scene 3d -rot {yaw} {pitch} {roll} --outfile {outfile} {defaced_img} -dr 80 1000 -in spline -cm render1 -bf 0.3 -r 100 -ns 500;"
            else:
                fsleyes_render_cmd = f"fsleyes render --scene 3d -rot {yaw} {pitch} {roll} --outfile {outfile} {defaced_img} -dr 20 250 -in spline -cm render1 -bf 0.3 -r 100 -ns 500;"
            cmd = f"export TMP_DISPLAY=$DISPLAY; unset DISPLAY; {fsleyes_render_cmd} export DISPLAY=$TMP_DISPLAY"

            print(cmd)
            run_command(cmd)
            print(f"Has the render been created? {outfile.exists()}")


def main():
    args = get_args()
    defaced_imgs = list(args.outdir.rglob('defaced.nii.gz'))

    if args.n_cpus == 1:
        print(f'Running in Serial, one render at a time')
        for img in defaced_imgs:
            generate_3d_renders(img, img.parent)

    elif args.n_cpus > 1:
        print(f'Running in Parallel with {args.n_cpus} cores')
        # initialize pool
        with Pool(processes=args.n_cpus) as p:
            p.starmap(generate_3d_renders, zip(defaced_imgs,
                                               [img.parent for img in defaced_imgs]))

    else:
        raise ValueError(f"Provided --n-cpus of {args.n_cpus} is not a valid number of CPUs.")

    # prep for visual inspection using visualqc deface
    print(f"Preparing for QC by visual inspection...\n")

    vqcdeface_cmd = construct_vqcdeface_cmd(args.outdir / 'QC_prep' / 'defacing_QC')
    print(f"Run the following command to start a VisualQC Deface session:\n\t{vqcdeface_cmd}\n")
    with open(args.outdir / 'QC_prep' / 'defacing_qc_cmd', 'w') as f:
        f.write(vqcdeface_cmd + '\n')

    print(f"All set to start visual inspection of defaced images!")


if __name__ == "__main__":
    main()
