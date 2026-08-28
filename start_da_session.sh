#!/usr/bin/env bash

# Source this file to activate the version-controlled AMLCS environment:
#   source start_da_session.sh
if [[ "$(type -t conda)" != function ]]; then
    if [[ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
    else
        module load anaconda/3.11.5
        eval "$(conda shell.bash hook)"
    fi
fi

conda activate amlcs

echo "Environment loaded on $(hostname): $CONDA_DEFAULT_ENV"
echo "Repository: $ENSF_SPEEDY_ROOT"
