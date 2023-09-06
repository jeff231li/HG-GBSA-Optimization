import os

from openff.evaluator import unit
from openff.evaluator.backends import ComputeResources
from openff.evaluator.backends.dask import DaskLocalCluster
from openff.evaluator.client import ConnectionOptions, EvaluatorClient, RequestOptions
from openff.evaluator.datasets.taproom import TaproomDataSet
from openff.evaluator.forcefield import SmirnoffForceFieldSource
from openff.evaluator.properties import HostGuestBindingAffinity
from openff.evaluator.protocols.paprika.openmm import APRSimulationSteps
from openff.evaluator.server import EvaluatorServer
from openff.evaluator.utils import setup_timestamp_logging
from openff.toolkit.typing.engines.smirnoff import ForceField

os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2,3"


def main():
    setup_timestamp_logging()
    server_port = 3241

    # Define the force field.
    GBSA = "GBSA_OBC1-optimized.offxml"
    force_field = ForceField("openff-2.0.0", GBSA)
    force_field_source = SmirnoffForceFieldSource.from_object(force_field)

    # Load in data from FreeSolv
    host_guest_data_set = TaproomDataSet(
        host_codes=["bcd"],
        guest_codes=["cbu", "m4c", "ben"],
        in_vacuum=True,
    )
    host_guest_data_set.json("test_set.json")

    # Set up the calculation
    APR_settings = APRSimulationSteps(
        n_thermalization_steps=25000,
        n_equilibration_steps=100000,
        n_production_steps=500000,
        out_production=2500,
        dt_thermalization=1.0 * unit.femtosecond,
        dt_equilibration=2.0 * unit.femtosecond,
        dt_production=2.0 * unit.femtosecond,
    )
    host_guest_schema = HostGuestBindingAffinity.default_paprika_schema(
        simulation_settings=APR_settings,
        use_implicit_solvent=True,
    )

    estimation_options = RequestOptions()
    estimation_options.calculation_layers = ["SimulationLayer"]
    estimation_options.add_schema(
        "SimulationLayer", "HostGuestBindingAffinity", host_guest_schema
    )

    # Create Pool of Dask Workers
    calculation_backend = DaskLocalCluster(
        number_of_workers=4,
        resources_per_worker=ComputeResources(
            number_of_threads=1,
            number_of_gpus=1,
            preferred_gpu_toolkit=ComputeResources.GPUToolkit.CUDA,
        ),
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
    results.json("results.json", format=True)


if __name__ == "__main__":
    main()
