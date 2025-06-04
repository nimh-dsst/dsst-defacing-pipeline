from deface import generate_3d_renders
from pathlib import Path
import sys

defaced_img = Path(sys.argv[1])
render_outdir = Path(sys.argv[2])

generate_3d_renders(defaced_img, render_outdir)
