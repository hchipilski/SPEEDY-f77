#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONDA_DEFAULT_ENV-}" != amlcs || -z "${CONDA_PREFIX-}" ]]; then
    echo "Activate the amlcs Conda environment before running this installer." >&2
    exit 1
fi

script_path="${BASH_SOURCE[0]}"
if command -v readlink &>/dev/null; then
    script_path="$(readlink -f -- "$script_path")"
fi
project_root="$(cd "$(dirname "$script_path")/.." && pwd -P)"

activate_source="$project_root/environment/conda/activate.sh"
deactivate_source="$project_root/environment/conda/deactivate.sh"
activate_target="$CONDA_PREFIX/etc/conda/activate.d/010-modules-load.sh"
deactivate_target="$CONDA_PREFIX/etc/conda/deactivate.d/010-modules-unload.sh"
backup_suffix="$(date +%Y%m%d-%H%M%S)"

for source_file in "$activate_source" "$deactivate_source"; do
    if [[ ! -f "$source_file" ]]; then
        echo "Hook source is missing: $source_file" >&2
        exit 2
    fi
done
unset source_file

mkdir -p "$(dirname "$activate_target")" "$(dirname "$deactivate_target")"

for target in "$activate_target" "$deactivate_target"; do
    if [[ -e "$target" && ! -L "$target" ]]; then
        mv "$target" "${target}.backup-${backup_suffix}"
    fi
done

ln -sfn "$activate_source" "$activate_target"
ln -sfn "$deactivate_source" "$deactivate_target"

if [[ "$(readlink -f -- "$activate_target")" != "$activate_source" ||
      "$(readlink -f -- "$deactivate_target")" != "$deactivate_source" ]]; then
    echo "Failed to verify the installed Conda hook links." >&2
    exit 3
fi

echo "Installed version-controlled amlcs hooks for $project_root"

