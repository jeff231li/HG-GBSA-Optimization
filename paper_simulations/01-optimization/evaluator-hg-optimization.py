import os
import subprocess as sp
import sys

from forcebalance.evaluator_io import Evaluator_SMIRNOFF
from openff.evaluator.backends import QueueWorkerResources
from openff.evaluator.backends.dask import DaskSLURMBackend
from openff.evaluator.client import ConnectionOptions, RequestOptions
from openff.evaluator.datasets.taproom import TaproomDataSet
from openff.evaluator.properties import HostGuestBindingAffinity
from openff.evaluator.protocols.paprika.openmm import APRSimulationSteps
from openff.evaluator.server import EvaluatorServer
from openff.evaluator.utils import setup_timestamp_logging
from openff.toolkit.typing.engines.smirnoff import ForceField
from openff.units import unit
from pkg_resources import resource_filename

os.environ["OE_LICENSE"] = "/gpfs/jsetiadi/oe_license.txt"


def main():
    setup_timestamp_logging()
    server_port = 3241

    os.makedirs("forcefield", exist_ok=True)
    os.makedirs("targets/host_guest_data", exist_ok=True)

    # Define the force field.
    GBSA = resource_filename(
        "openff.toolkit",
        os.path.join("data", "test_forcefields", "GBSA_OBC2-1.0.offxml"),
    )
    force_field = ForceField(
        "openff-2.0.0.offxml",
        GBSA,
    )
    gbsa_handler = force_field.get_parameter_handler("GBSA")

    for smirks in ["[#1:1]", "[#1:1]~[#7]", "[#6:1]", "[#7:1]", "[#8:1]"]:
        parameter = gbsa_handler.parameters[smirks]
        parameter.add_cosmetic_attribute("parameterize", "radius")

    force_field.to_file("forcefield/openff-2.0.0-GBSA_OBC2-tagged.offxml")

    # Load in data from FreeSolv
    host_guest_data_set = TaproomDataSet(
        host_guest_codes={
            "acd": ["coc", "chp", "hep", "hx2", "ham", "pam"],
            "bcd": ["coc", "cbu", "mo3", "mp4", "rim", "oam"],
            "cb7": ["hxm", "c8m", "haz", "hpm", "cha", "chm"],
            "cb8": ["amm", "con", "mpa", "qui", "thp", "mth"],
            "oah": ["ben", "c3b", "c7c", "c4b", "trz", "hxa"],
            "oam": ["hxa", "trz", "nbn", "hxy", "bra", "m4p"],
        },
        in_vacuum=True,
    )
    host_guest_data_set.json("targets/host_guest_data/training_set.json")

    # Set up the calculation
    APR_settings = APRSimulationSteps(
        n_thermalization_steps=50000,
        n_equilibration_steps=250000,
        n_production_steps=1500000,
        out_production=2500,
        dt_thermalization=1.0 * unit.femtosecond,
        dt_equilibration=2.0 * unit.femtosecond,
        dt_production=2.0 * unit.femtosecond,
    )
    gradient_settings = APRSimulationSteps(
        n_thermalization_steps=50000,
        n_equilibration_steps=250000,
        n_production_steps=10000000,
        out_production=2500,
        dt_thermalization=1.0 * unit.femtosecond,
        dt_equilibration=2.0 * unit.femtosecond,
        dt_production=2.0 * unit.femtosecond,
    )
    host_guest_schema = HostGuestBindingAffinity.default_paprika_schema(
        simulation_settings=APR_settings,
        end_states_settings=gradient_settings,
        use_implicit_solvent=True,
        enable_hmr=True,
    )

    estimation_options = RequestOptions()
    estimation_options.calculation_layers = ["SimulationLayer"]
    estimation_options.add_schema(
        "SimulationLayer", "HostGuestBindingAffinity", host_guest_schema
    )

    # Create the ForceBalance options object
    target_options = Evaluator_SMIRNOFF.OptionsFile()
    target_options.data_set_path = "training_set.json"
    target_options.weights = {
        "HostGuestBindingAffinity": 1.0,
    }
    target_options.denominators = {
        "HostGuestBindingAffinity": 1.0 * unit.kcal / unit.mole,
    }
    target_options.estimation_options = estimation_options
    target_options.connection_options = ConnectionOptions(server_port=server_port)

    with open("targets/host_guest_data/options.json", "w") as file:
        file.write(target_options.to_json())

    # Create Pool of Dask Workers
    setup_script_commands = [
        "# Load conda 3 and load environment",
        "# >>> conda initialize >>>",
        "# !! Contents within this block are managed by 'conda init' !!",
        "__conda_setup=\"$('/gpfs/jsetiadi/anaconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)\"",
        "if [ $? -eq 0 ]; then",
        '    eval "$__conda_setup"',
        "else",
        '    if [ -f "/gpfs/jsetiadi/anaconda3/etc/profile.d/conda.sh" ]; then',
        '        . "/gpfs/jsetiadi/anaconda3/etc/profile.d/conda.sh"',
        "    else",
        '        export PATH="/gpfs/jsetiadi/anaconda3/bin:$PATH"',
        "    fi",
        "fi",
        "unset __conda_setup",
        "# <<< conda initialize <<<",
        "conda activate forcebalance",
        "module load mpi/openmpi-x86_64",
        "LD_LIBRARY_PATH=/gpfs/jsetiadi/anaconda3/lib/:${LD_LIBRARY_PATH}",
        "# OpenEye License",
        "export OE_LICENSE=/gpfs/jsetiadi/oe_license.txt",
        "# Change directory to working folder",
        f"cd {sys.argv[1]}",
        "# Create temporary directory for DASK memory spill",
        "SCRATCH=/scratch/${USER}/job_${SLURM_JOB_ID}",
        "mkdir -p ${SCRATCH}/jsetiadi/working_directory",
        "export DASK_TEMPORARY_DIRECTORY=${SCRATCH}/jsetiadi/working_directory",
        "# Extra Commands to print more info",
        'echo "SLURM Job ID: ${SLURM_JOB_ID}"',
        'echo "Current directory: $(pwd)"',
        'echo "Dask temporary directory: ${DASK_TEMPORARY_DIRECTORY}"',
        'echo "Using CUDA device no: ${CUDA_VISIBLE_DEVICES}"',
        'echo "List of vnodes: ${SLURM_JOB_NODELIST}"',
    ]

    # Create Pool of Dask Workers
    calculation_backend = DaskSLURMBackend(
        minimum_number_of_workers=1,
        maximum_number_of_workers=28,
        resources_per_worker=QueueWorkerResources(
            number_of_threads=1,
            number_of_gpus=1,
            preferred_gpu_toolkit=QueueWorkerResources.GPUToolkit.CUDA,
            per_thread_memory_limit=6 * unit.gigabyte,
            wallclock_time_limit="48:00:00",
        ),
        queue_name="CLUSTER",
        setup_script_commands=setup_script_commands,
        extra_script_options=["--gres=gpu:1080ti:1"],
        disable_nanny_process=False,
    )

    # Start the Evaluator Server
    with calculation_backend:
        evaluator_server = EvaluatorServer(
            calculation_backend=calculation_backend,
            port=server_port,
            delete_working_files=False,
        )
        with evaluator_server:
            # Run ForceBalance
            force_balance_arguments = ["ForceBalance.py", "optimize.in"]
            with open("force_balance.log", "w") as file:
                sp.check_call(force_balance_arguments, stderr=file, stdout=file)


if __name__ == "__main__":
    main()
