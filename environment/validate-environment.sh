#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONDA_DEFAULT_ENV-}" != amlcs || -z "${CONDA_PREFIX-}" ]]; then
    echo "Activate the amlcs Conda environment before validation." >&2
    exit 1
fi

test "$ENSF_SPEEDY_ROOT" = "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
test "$AMLCS_DIR" = "$ENSF_SPEEDY_ROOT/amlcs"
test "$SPEEDY_MODEL_DIR" = "$ENSF_SPEEDY_ROOT/models/speedy/t21"
test "$NETCDF" = /opt/rcc/gnu
test "$NETCDF_INSTALL_PATH" = /opt/rcc/gnu
test "$(command -v gfortran)" = /usr/bin/gfortran
test "$(command -v nf-config)" = /opt/rcc/gnu/bin/nf-config
test -e "$NETCDF/include/netcdf.inc"
test -e "$NETCDF/lib64/libnetcdff.so"
test "$XDG_CACHE_HOME" = "$CONDA_PREFIX/var/cache"
test "$MPLCONFIGDIR" = "$XDG_CACHE_HOME/matplotlib"
test -w "$MPLCONFIGDIR"

case "${PYTHONPATH-}" in
    *python3.9*)
        echo "GNU's Python 3.9 path leaked into PYTHONPATH: $PYTHONPATH" >&2
        exit 2
        ;;
esac

"$CONDA_PREFIX/bin/python" <<'PY'
import sys
from packaging.version import Version

if sys.version_info[:2] != (3, 11):
    raise SystemExit(f"Expected Python 3.11, found {sys.version.split()[0]}")

import cartopy
import imageio
import matplotlib
import netCDF4
import numpy
import pandas
import scipy
import seaborn
import sklearn
import torch
import xarray
from mpl_toolkits.basemap import Basemap

if Version(matplotlib.__version__) >= Version("3.11"):
    raise SystemExit(
        f"Basemap requires Matplotlib <3.11; found {matplotlib.__version__}"
    )

print(f"Python {sys.version.split()[0]}")
print(f"NumPy {numpy.__version__}")
print(f"Matplotlib {matplotlib.__version__}")
print(f"NetCDF4-Python {netCDF4.__version__}")
print(f"PyTorch {torch.__version__}")
print("AMLCS Python imports: OK")
PY

netcdf_extension="$($CONDA_PREFIX/bin/python -c \
    'import netCDF4._netCDF4 as module; print(module.__file__)')"
if ldd "$netcdf_extension" | grep -q 'not found'; then
    echo "Conda Python NetCDF has unresolved shared libraries." >&2
    exit 3
fi
if ldd "$netcdf_extension" | grep -q "$SPEEDY_NETCDF_ROOT"; then
    echo "Conda Python NetCDF resolves an RCC native library." >&2
    exit 4
fi
unset netcdf_extension

if ldd "$SPEEDY_MODEL_DIR/imp.exe" | grep -q 'not found'; then
    echo "SPEEDY has unresolved shared libraries." >&2
    exit 5
fi

echo "AMLCS native environment: OK"
