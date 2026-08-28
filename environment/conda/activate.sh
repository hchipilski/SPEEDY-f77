#!/usr/bin/env bash
# Conda activation hook for the EnSF_SPEEDY AMLCS environment.
# This file is sourced by Conda; do not execute it directly.

if ! type module &>/dev/null; then
    [[ -f /etc/profile.d/z00_lmod.sh ]] && . /etc/profile.d/z00_lmod.sh
    [[ -f /etc/profile.d/modules.sh ]] && . /etc/profile.d/modules.sh
fi

_ensf_speedy_save_variable() {
    local variable_name="$1"
    local set_name="_ENSF_SPEEDY_SAVED_SET_${variable_name}"
    local value_name="_ENSF_SPEEDY_SAVED_VALUE_${variable_name}"

    if [[ -v "$variable_name" ]]; then
        printf -v "$set_name" '%s' 1
        printf -v "$value_name" '%s' "${!variable_name}"
        export "$set_name" "$value_name"
    else
        printf -v "$set_name" '%s' 0
        unset "$value_name"
        export "$set_name"
    fi
}

_ensf_speedy_managed_variables=(
    LD_LIBRARY_PATH PYTHONPATH PYTHONNOUSERSITE MPLBACKEND
    XDG_CACHE_HOME MPLCONFIGDIR
    FC F77 NETCDF NETCDF_INSTALL_PATH SPEEDY_NETCDF_ROOT
    ENSF_SPEEDY_ROOT AMLCS_DIR SPEEDY_MODEL_DIR
)

for variable_name in "${_ensf_speedy_managed_variables[@]}"; do
    _ensf_speedy_save_variable "$variable_name"
done
unset variable_name

export _ENSF_SPEEDY_SAVED_LOADEDMODULES="${LOADEDMODULES-}"

_ensf_speedy_restore_modules() {
    local module_list="$1"
    local module_name
    local -a modules

    module purge || return 1
    if [[ -n "$module_list" ]]; then
        IFS=: read -r -a modules <<< "$module_list"
        for module_name in "${modules[@]}"; do
            [[ -z "$module_name" ]] || module load "$module_name" || return 1
        done
    fi
}

_ensf_speedy_restore_variables() {
    local variable_name set_name value_name

    for variable_name in "${_ensf_speedy_managed_variables[@]}"; do
        set_name="_ENSF_SPEEDY_SAVED_SET_${variable_name}"
        value_name="_ENSF_SPEEDY_SAVED_VALUE_${variable_name}"
        if [[ "${!set_name-0}" == 1 ]]; then
            export "$variable_name=${!value_name-}"
        else
            unset "$variable_name"
        fi
    done
}

_ensf_speedy_abort_activation() {
    echo "ERROR: amlcs native activation failed; restoring the previous shell state" >&2
    _ensf_speedy_restore_modules "${_ENSF_SPEEDY_SAVED_LOADEDMODULES-}" || \
        echo "ERROR: could not restore the pre-activation module list" >&2
    _ensf_speedy_restore_variables
}

hook_path="${BASH_SOURCE[0]}"
if command -v readlink &>/dev/null; then
    hook_path="$(readlink -f -- "$hook_path")"
fi
hook_dir="$(cd "$(dirname "$hook_path")" && pwd -P)"
export ENSF_SPEEDY_ROOT="$(cd "$hook_dir/../.." && pwd -P)"
unset hook_path hook_dir

export AMLCS_DIR="$ENSF_SPEEDY_ROOT/amlcs"
export SPEEDY_MODEL_DIR="$ENSF_SPEEDY_ROOT/models/speedy/t21"
export SPEEDY_NETCDF_ROOT=/opt/rcc/gnu
export NETCDF="$SPEEDY_NETCDF_ROOT"
export NETCDF_INSTALL_PATH="$SPEEDY_NETCDF_ROOT"
export FC=gfortran
export F77=gfortran
export PYTHONNOUSERSITE=1
export MPLBACKEND=Agg
export XDG_CACHE_HOME="$CONDA_PREFIX/var/cache"
export MPLCONFIGDIR="$XDG_CACHE_HOME/matplotlib"

if ! mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME/fontconfig"; then
    _ensf_speedy_abort_activation
    unset _ensf_speedy_managed_variables
    return 1
fi

if ! module load gnu/11; then
    _ensf_speedy_abort_activation
    unset _ensf_speedy_managed_variables
    return 1
fi

# The GNU module exposes the native compiler and headers, but its library and
# Python 3.9 paths can override Conda's Python 3.11 NetCDF stack. SPEEDY links
# NetCDF explicitly and embeds its runtime path, so retain the pre-activation
# LD_LIBRARY_PATH and add only the repository's Python source directory.
if [[ "${_ENSF_SPEEDY_SAVED_SET_LD_LIBRARY_PATH-0}" == 1 ]]; then
    export LD_LIBRARY_PATH="${_ENSF_SPEEDY_SAVED_VALUE_LD_LIBRARY_PATH-}"
else
    unset LD_LIBRARY_PATH
fi

if [[ "${_ENSF_SPEEDY_SAVED_SET_PYTHONPATH-0}" == 1 &&
      -n "${_ENSF_SPEEDY_SAVED_VALUE_PYTHONPATH-}" ]]; then
    export PYTHONPATH="$AMLCS_DIR:${_ENSF_SPEEDY_SAVED_VALUE_PYTHONPATH}"
else
    export PYTHONPATH="$AMLCS_DIR"
fi

activation_ok=1
for required_dir in "$AMLCS_DIR" "$SPEEDY_MODEL_DIR"; do
    if [[ ! -d "$required_dir" ]]; then
        echo "ERROR: required project directory is missing: $required_dir" >&2
        activation_ok=0
    fi
done
unset required_dir

for required_command in gfortran nf-config; do
    if ! command -v "$required_command" >/dev/null 2>&1; then
        echo "ERROR: required command is unavailable: $required_command" >&2
        activation_ok=0
    fi
done
unset required_command

for required_file in \
    "$SPEEDY_NETCDF_ROOT/include/netcdf.inc" \
    "$SPEEDY_NETCDF_ROOT/lib64/libnetcdff.so"; do
    if [[ ! -e "$required_file" ]]; then
        echo "ERROR: required NetCDF file is missing: $required_file" >&2
        activation_ok=0
    fi
done
unset required_file

if [[ "$activation_ok" -ne 1 ]]; then
    unset activation_ok
    _ensf_speedy_abort_activation
    unset _ensf_speedy_managed_variables
    return 1
fi
unset activation_ok

unset _ensf_speedy_managed_variables
unset -f _ensf_speedy_save_variable _ensf_speedy_restore_modules \
    _ensf_speedy_restore_variables _ensf_speedy_abort_activation

echo "AMLCS environment: GNU 11, RCC NetCDF, $ENSF_SPEEDY_ROOT"
