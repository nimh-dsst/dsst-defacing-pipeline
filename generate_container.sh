#!/bin/bash

set -eu

generate() {
	# more details might come on https://github.com/ReproNim/neurodocker/issues/330
	[ "$1" == singularity ] && add_entry=' "$@"' || add_entry=''
	#neurodocker generate "$1" \
	#ndversion=0.9.5
	#ndversion=master
	#docker run --rm repronim/neurodocker:$ndversion \
	# ATM needs devel version  of neurodocker for a fix to AFNI recipe
	#--base-image neurodebian:bookworm \
	#--ndfreeze date=20240320 \
	dest=/opt/dsst-defacing-pipeline
	neurodocker \
		generate "$1" \
		--pkg-manager portage \
		--base-image "docker.io/gentoo/portage:20240324 as portage" \
		--base-image "docker.io/gentoo/stage3:20240318" \
		--gentoo gentoo_hash=2d25617a1d085316761b06c17a93ec972f172fc6 \
		--install afni fsl \
		--copy environment.yml /opt/environment.yml \
		--copy src "$dest" \
		--miniconda \
			version=latest \
			env_name=dsstdeface \
			env_exists=false \
			yaml_file=/opt/environment.yml \
		--user=dsst \
		--entrypoint "$dest/run.py"
		#--run "curl -sL https://deb.nodesource.com/setup_16.x | bash - " \
		#--install nodejs npm \
		#--run "npm install -g bids-validator@1.14.4" \
		#--fsl version=6.0.7.1 \
}

generate docker > Dockerfile
# generate singularity > Singularity
