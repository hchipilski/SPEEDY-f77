# AMLCS environment

This directory contains the version-controlled definition and Conda hooks for
the `amlcs` environment.

## Update the environment

```bash
source "$HOME/anaconda3/etc/profile.d/conda.sh"
conda env update --name amlcs --file environment/conda/environment.yml --prune
```

## Install the hooks

```bash
source "$HOME/anaconda3/etc/profile.d/conda.sh"
conda activate amlcs
./environment/install-conda-hooks.sh
conda deactivate
conda activate amlcs
./environment/validate-environment.sh
```

Activation loads GNU 11, exports the repository and SPEEDY locations, and
selects RCC's GNU NetCDF installation at `/opt/rcc/gnu`. It deliberately keeps
RCC native libraries out of the global `LD_LIBRARY_PATH` so Conda's Python
NetCDF package resolves its own compatible libraries. Matplotlib and
fontconfig caches are kept under the Conda environment, and plotting defaults
to the non-interactive `Agg` backend. Deactivation restores the exact module
list and managed variables that existed before activation.
