#!/usr/local/bin/python3
"""
Generates 3D renders of defaced images using FSLeyes. More info on FSLeyes can be found\
 https://open.win.ox.ac.uk/pages/fsl/fsleyes/fsleyes/userdoc/install.html#install-from-conda-forge-recommended
"""
import argparse
import subprocess
from pathlib import Path


def get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description=__doc__)

    parser.add_argument('-o', '--output', type=Path, action='store', dest='outdir', metavar='OUTPUT_DIR',
                        default=Path('.'), help="Path to defacing outputs directory.")

    return parser.parse_args()


def run_command(cmdstr):
    """Runs the given command str as shell subprocess. If logfile object is provided, then the stdout and stderr of the
    subprocess is written to the log file.
    :param str cmdstr: A shell command formatted as a string variable.
    :param io.TextIOWrapper logfile: optional, File object to log the stdout and stderr of the subprocess.
    """
    p = subprocess.run(cmdstr, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8', shell=True)
    print(p.stdout)


def generate_3d_renders(defaced_img, render_outdir):
    rotations = [(45, 5, 10), (-45, 5, 10)]
    for idx, rot in enumerate(rotations):
        yaw, pitch, roll = rot[0], rot[1], rot[2]
        outfile = render_outdir.joinpath('defaced_render_99' + str(idx) + '.png')
        fsleyes_render_cmd = f"export TMP_DISPLAY=$DISPLAY; unset DISPLAY; fsleyes render --scene 3d -rot {yaw} {pitch} {roll} --outfile {outfile} {defaced_img} -dr 20 250 -in spline -bf 0.3 -r 100 -ns 500; export DISPLAY=$TMP_DISPLAY"
        print(fsleyes_render_cmd)
        run_command(fsleyes_render_cmd)
        print(f"Has the render been created? {outfile.exists()}")


def main():
    args = get_args()
    defaced_imgs = list(args.outdir.rglob('defaced.nii.gz'))
    for img in defaced_imgs:
        generate_3d_renders(img, img.parent)
    # print(defaced_imgs)


if __name__ == "__main__":
    main()
