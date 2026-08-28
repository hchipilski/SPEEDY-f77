#!/usr/bin/env bash
# Conda deactivation hook for the EnSF_SPEEDY AMLCS environment.

if ! type module &>/dev/null; then
    [[ -f /etc/profile.d/z00_lmod.sh ]] && . /etc/profile.d/z00_lmod.sh
    [[ -f /etc/profile.d/modules.sh ]] && . /etc/profile.d/modules.sh
fi

if type module &>/dev/null; then
    module purge
    if [[ -n "${_ENSF_SPEEDY_SAVED_LOADEDMODULES-}" ]]; then
        IFS=: read -r -a saved_modules <<< "$_ENSF_SPEEDY_SAVED_LOADEDMODULES"
        for module_name in "${saved_modules[@]}"; do
            [[ -z "$module_name" ]] || module load "$module_name"
        done
        unset module_name saved_modules
    fi
fi
unset _ENSF_SPEEDY_SAVED_LOADEDMODULES

_ensf_speedy_restore_variable() {
    local variable_name="$1"
    local set_name="_ENSF_SPEEDY_SAVED_SET_${variable_name}"
    local value_name="_ENSF_SPEEDY_SAVED_VALUE_${variable_name}"

    if [[ "${!set_name-0}" == 1 ]]; then
        export "$variable_name=${!value_name-}"
    else
        unset "$variable_name"
    fi
    unset "$set_name" "$value_name"
}

managed_variables=(
    LD_LIBRARY_PATH PYTHONPATH PYTHONNOUSERSITE MPLBACKEND
    XDG_CACHE_HOME MPLCONFIGDIR
    FC F77 NETCDF NETCDF_INSTALL_PATH SPEEDY_NETCDF_ROOT
    ENSF_SPEEDY_ROOT AMLCS_DIR SPEEDY_MODEL_DIR
)

for variable_name in "${managed_variables[@]}"; do
    _ensf_speedy_restore_variable "$variable_name"
done
unset variable_name managed_variables
unset -f _ensf_speedy_restore_variable
