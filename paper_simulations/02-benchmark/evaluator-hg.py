import os
import sys

from openff.evaluator.backends import QueueWorkerResources
from openff.evaluator.backends.dask import DaskSLURMBackend
from openff.evaluator.client import ConnectionOptions, EvaluatorClient, RequestOptions
from openff.evaluator.datasets.taproom import TaproomDataSet
from openff.evaluator.forcefield import SmirnoffForceFieldSource
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

    # Define the force field.
    GBSA = resource_filename(
        "openff.toolkit",
        os.path.join("data", "test_forcefields", "GBSA_OBC2-1.0.offxml"),
    )
    force_field = ForceField("openff-2.0.0.offxml", GBSA)
    force_field_source = SmirnoffForceFieldSource.from_object(force_field)

    # Load in data from FreeSolv
    host_guest_data_set = TaproomDataSet(
        exclude_systems={
            "acd": ["coc", "chp", "hep", "hx2", "ham", "pam"],
            "bcd": ["coc", "cbu", "mo3", "mp4", "rim", "oam"],
            "cb7": ["hxm", "c8m", "haz", "hpm", "cha", "chm"],
            "cb8": ["amm", "con", "mpa", "qui", "thp", "mth"],
            "oah": ["ben", "c3b", "c7c", "c4b", "trz", "hxa"],
            "oam": ["hxa", "trz", "nbn", "hxy", "bra", "m4p"],
        },
        in_vacuum=True,
    )
    host_guest_data_set.json("test_set.json")

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
    host_guest_schema = HostGuestBindingAffinity.default_paprika_schema(
        simulation_settings=APR_settings,
        use_implicit_solvent=True,
        enable_hmr=True,
    )

    estimation_options = RequestOptions()
    estimation_options.calculation_layers = ["SimulationLayer"]
    estimation_options.add_schema(
        "SimulationLayer", "HostGuestBindingAffinity", host_guest_schema
    )

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
    calculation_backend.start()

    # Start the Evaluator Server
    evaluator_server = EvaluatorServer(
        calculation_backend=calculation_backend,
        working_directory="working-data",
        port=server_port,
    )
    evaluator_server.start(asynchronous=True)

    # Start the Evaluator Client
    evaluator_client = EvaluatorClient(ConnectionOptions(server_port=server_port))
    request, exception = evaluator_client.request_estimate(
        property_set=host_guest_data_set,
        force_field_source=force_field_source,
        options=estimation_options,
    )
    assert exception is None

    # Wait for the results
    results, exception = request.results(synchronous=True)
    assert exception is None

    # Save the results
    results.json("test_set_results.json", format=True)


if __name__ == "__main__":
    main()
