#!/bin/bash

set -eu

generate() {
	# more details might come on https://github.com/ReproNim/neurodocker/issues/330
	[ "$1" == singularity ] && add_entry=' "$@"' || add_entry=''
	#neurodocker generate "$1" \
	ndversion=0.9.5
	#ndversion=master
	#docker run --rm repronim/neurodocker:$ndversion \
	# ATM needs devel version  of neurodocker for a fix to AFNI recipe
	neurodocker \
		generate "$1" \
		--base-image neurodebian:bookworm \
		--ndfreeze date=20240320 \
		--copy environment.yml /opt/environment.yml \
		--miniconda \
			version=latest \
			env_name=dsstdeface \
			env_exists=false \
			yaml_file=/opt/environment.yml \
		--pkg-manager=apt \
		--install vim wget strace time ncdu gnupg curl procps pigz less tree \
		--run "apt-get update && apt-get -y dist-upgrade" \
		--afni method=binaries version=latest \
		--user=dsst \
		--entrypoint "bash"
		#--run "curl -sL https://deb.nodesource.com/setup_16.x | bash - " \
		#--install nodejs npm \
		#--run "npm install -g bids-validator@1.14.4" \
		#--fsl version=6.0.7.1 \
}

generate docker > Dockerfile
# generate singularity > Singularity
