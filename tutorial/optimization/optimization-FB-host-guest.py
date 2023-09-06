import os
import subprocess as sp

from forcebalance.evaluator_io import Evaluator_SMIRNOFF
from openff.evaluator import unit
from openff.evaluator.backends import ComputeResources
from openff.evaluator.backends.dask import DaskLocalCluster
from openff.evaluator.client import ConnectionOptions, RequestOptions
from openff.evaluator.datasets.taproom import TaproomDataSet
from openff.evaluator.properties import HostGuestBindingAffinity
from openff.evaluator.protocols.paprika.openmm import APRSimulationSteps
from openff.evaluator.server import EvaluatorServer
from openff.evaluator.utils import setup_timestamp_logging
from openff.toolkit.typing.engines.smirnoff import ForceField
from pkg_resources import resource_filename

os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2,3"


def main():
    setup_timestamp_logging()
    server_port = 3241

    os.makedirs("forcefield", exist_ok=True)
    os.makedirs("targets/host_guest_data", exist_ok=True)

    # Define the force field.
    GBSA = resource_filename(
        "openff.toolkit",
        os.path.join("data", "test_forcefields", "GBSA_OBC1-1.0.offxml"),
    )
    force_field = ForceField("openff-2.0.0.offxml", GBSA)

    # Tag the Oxygen atom radius
    gbsa_handler = force_field.get_parameter_handler("GBSA")
    for smirks in ["[#8:1]"]:
        parameter = gbsa_handler.parameters[smirks]
        parameter.add_cosmetic_attribute("parameterize", "radius")

    # Save force field to JSON file
    force_field.to_file("forcefield/openff-2.0.0-GBSA_OBC1-tagged.offxml")

    # Select training data from Taproom data set
    host_guest_data_set = TaproomDataSet(
        host_codes=["bcd"],
        guest_codes=["hex"],
        in_vacuum=True,
    )
    host_guest_data_set.json("targets/host_guest_data/training_set.json")

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
    gradient_settings = APRSimulationSteps(
        n_thermalization_steps=25000,
        n_equilibration_steps=100000,
        n_production_steps=5000000,
        out_production=2500,
        dt_thermalization=1.0 * unit.femtosecond,
        dt_equilibration=2.0 * unit.femtosecond,
        dt_production=2.0 * unit.femtosecond,
    )
    host_guest_schema = HostGuestBindingAffinity.default_paprika_schema(
        simulation_settings=APR_settings,
        end_states_settings=gradient_settings,
        use_implicit_solvent=True,
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

    # Save options to JSON - will be read in ForceBalance
    with open("targets/host_guest_data/options.json", "w") as file:
        file.write(target_options.to_json())

    # Create Pool of Dask Workers
    calculation_backend = DaskLocalCluster(
        number_of_workers=4,
        resources_per_worker=ComputeResources(
            number_of_threads=1,
            number_of_gpus=1,
            preferred_gpu_toolkit=ComputeResources.GPUToolkit.CUDA,
        ),
    )

    # Start the Evaluator Server
    with calculation_backend:
        evaluator_server = EvaluatorServer(
            calculation_backend=calculation_backend,
            port=server_port,
        )
        with evaluator_server:

            # Run ForceBalance
            force_balance_arguments = ["ForceBalance.py", "optimize.in"]
            with open("force_balance.log", "w") as file:
                sp.check_call(force_balance_arguments, stderr=file, stdout=file)


if __name__ == "__main__":
    main()
