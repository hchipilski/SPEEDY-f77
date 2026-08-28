####################################################################################
####################################################################################
####################################################################################

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import scipy.sparse as spa
import pandas as pd
import time
from netCDF4 import Dataset

from numerical_model import numerical_model
from grid_resolution import grid_resolution
from observation import observation
from reference_solution import reference_solution
from sequential_methods import EnKF_MC_obs, sequential_method
from error_metric import error_metric
from time_metric import time_metric
            

def _read_bool(value, default=False):
    """Parse booleans from CSV values without treating ``"False"`` as true."""
    if value is None or pd.isna(value):
        return default
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError(f"Cannot interpret {value!r} as a boolean")


def _optional_value(df, column, default):
    if column not in df.columns or pd.isna(df[column].iloc[0]):
        return default
    return df[column].iloc[0]


def _git_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


####################################################################################
####################################################################################
####################################################################################
def main():
    
    
    input_file = sys.argv[1];
    print('* ENDJ - Input file {0}'.format(input_file));
    df_par = pd.read_csv(input_file);
    for c in df_par.columns:
        print(' - {0} = {1}'.format(c, df_par[c].iloc[0]));

        
    #1. Prepaging
    r            = int(df_par['r'].iloc[0]);
    s            = int(df_par['s'].iloc[0]);
    method       = df_par['method'].iloc[0].strip();	
    exp_settings = df_par['exp_settings'].iloc[0];
    infla        = float(df_par['infla'].iloc[0]);  
    data_obs     = df_par['err_obs'].iloc[0].strip().split(',');
    err_obs      = [float(v) for v in data_obs];   
    plac_obs     = df_par['obs_plc'].iloc[0].strip().split(',');
    obs_plc      = [int(v) for v in plac_obs];
    l_snap       = df_par['list_snapshots'].iloc[0].strip().split(',');
    option_mask  = int(df_par['option_mask'].iloc[0]);

    # These options were present in Jack's driver but were dropped in commit
    # 0a2f8fe. Without this wiring, case 2 and the derived-wind part of case 3
    # silently execute with the default linear observation operators.
    nonlinear_obs = _read_bool(_optional_value(df_par, 'nonlinear_obs', False))
    scalefact = float(_optional_value(df_par, 'scalefact', 1.0))
    wind_nonlinear_operator = _read_bool(
        _optional_value(df_par, 'wind_nonlinear_operator', False)
    )
    normalize_nonlinear = _read_bool(
        _optional_value(df_par, 'normalize_nonlinear', True), default=True
    )
    nonlinear_operator_type = str(
        _optional_value(df_par, 'nonlinear_operator_type', 'arctan')
    ).strip()

    print(
        'Observation operators: '
        f'nonlinear={nonlinear_obs}, scale={scalefact}, '
        f'wind-derived={wind_nonlinear_operator}, '
        f'normalize={normalize_nonlinear}, type={nonlinear_operator_type}'
    )

    list_k = [int(v) for v in l_snap];

    print(f'plac_obs = {obs_plc}');
    print(f'err_obs  = {err_obs}');
    
    df_con = pd.read_csv(f'{exp_settings}/config.csv');
    print(df_con);
    
    Nens      = df_con['Nens'].iloc[0];
    M         = df_con['M'].iloc[0];
    res_name  = df_con['res_name'].iloc[0];
    per       = df_con['per'].iloc[0];
    obs_steps = df_con['obs_steps'].iloc[0];
    ini_steps = df_con['ini_steps'].iloc[0];
    ini_times = df_con['ini_times'].iloc[0];
    syn_tests = df_con['syn_tests'].iloc[0];
    data_prep = df_con['folder_prep'].iloc[0];
    code_prep = df_con['code'].iloc[0];
    code_path = df_con['code_path'].iloc[0];
    par       = _read_bool(df_con['par'].iloc[0]);
    
    args = [0, obs_steps, 1];
    ini0 = [ini_steps, 0, 1];
    ini0_no_restart = [ini_times, 0, 0];
    #print(df_par['code'])
     
    method_path = (
        f'{code_path}_{method}_{r}_{s}_{int(round(100 * infla))}'
        f'_mask_{option_mask}'
    )

    path = Path('../runs')
    if not df_par['code'].isnull().values.any():
        path = Path(str(df_par['code'].iloc[0]))

    output_dir = path / method_path
    output_dir.mkdir(parents=True, exist_ok=True)
    path_method = f'{output_dir}/'

    input_path = Path(input_file).resolve()
    input_sha256 = hashlib.sha256(input_path.read_bytes()).hexdigest()
    shutil.copy2(input_path, output_dir / 'runner.csv')
    metadata = {
        'driver': str(Path(__file__).resolve()),
        'git_commit': _git_commit(),
        'input_file': str(input_path),
        'input_sha256': input_sha256,
        'output_directory': str(output_dir.resolve()),
        'method': method,
        'r': r,
        's': s,
        'inflation': infla,
        'option_mask': option_mask,
        'nonlinear_obs': nonlinear_obs,
        'scalefact': scalefact,
        'wind_nonlinear_operator': wind_nonlinear_operator,
        'normalize_nonlinear': normalize_nonlinear,
        'nonlinear_operator_type': nonlinear_operator_type,
    }
    (output_dir / 'run_metadata.json').write_text(
        json.dumps(metadata, indent=2) + '\n', encoding='utf-8'
    )
    
    print('* The method reads {0}'.format(method));
    
    #exit();
    
    #1.2 Grid resolution
    gs = grid_resolution(res_name);
    data_obs = df_par['err_obs'].iloc[0].strip().split(',');
    err_obs = [float(v) for v in data_obs];#[0.1, 0.1, 0.1, 1e-4, 0.01, 0.1, 0.1, 0.1, 1e-4, 0.01]; #[u,v,T,H,p]
    #obs_plc = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1];
    #print (err_obs)
    
    plac_obs = df_par['obs_plc'].iloc[0].strip().split(',');
    obs_plc = [int(v) for v in plac_obs];
    #print (obs_plc)
    ob = observation(
        err_obs,
        obs_plc,
        nonlinear_obs=nonlinear_obs,
        scalefact=scalefact,
        normalize_nonlinear=normalize_nonlinear,
        nonlinear_operator_type=nonlinear_operator_type,
    );

    
    #1.1 Numerical model
    nm = numerical_model(path_method, gs, Nens, par=par);
    nm.define_relations(option=option_mask);
    nm.load_settings(exp_settings, args);
    #print(nm.mask_cor);
     
    
    #1.3 Mesh grid is created
    gs.create_mesh(nm);
    gs.compute_sub_domains(r);
    rs = reference_solution(nm, M);
    
    
    #Setting the sequential data assimilation method
    wind_err = {}
    if len(err_obs) > 10:
        wind_err['WDG1'] = err_obs[10]
    if len(err_obs) > 11:
        wind_err['WSG1'] = err_obs[11]

    seq_da = sequential_method(method).get_instance(
        nm,
        infla,
        Nens,
        nonlinear_obs=nonlinear_obs,
        scalefact=scalefact,
        wind_nonlinear_operator=wind_nonlinear_operator,
        wind_err=wind_err,
        normalize_nonlinear=normalize_nonlinear,
        nonlinear_operator_type=nonlinear_operator_type,
    );
    
    ob.build_observational_network(gs, nm, s=s);
    ob.build_synthetic_observations(nm, rs, M); 
    
    #Metric
    em_bck = error_metric(nm, 'bck', M);
    em_ana = error_metric(nm, 'ana', M);
    tm_bck =  time_metric(nm, 'bck');
    tm_ana =  time_metric(nm, 'ana');
    
    for k in range(0, M):
        seq_da.load_background_ensemble();
        
        tm_bck.start_time();
        seq_da.prepare_background();
        tm_bck.check_time();
        
        tm_ana.start_time();
        seq_da.prepare_analysis(ob, k);
        seq_da.perform_assimilation(ob);
        tm_ana.check_time();
        
        em_bck.compute_error_step(k, seq_da.XB, rs.x_ref[k]);
        em_ana.compute_error_step(k, seq_da.XA, rs.x_ref[k]);
        
        em_bck.store_all_results();
        em_ana.store_all_results();
        tm_bck.store_all_results();
        tm_ana.store_all_results();
        
        seq_da.check_time_store(k, list_k);
        
        seq_da.perform_forecast();
    
    seq_da.clear_all();

    exit();
    
if __name__ == "__main__":
    main();
