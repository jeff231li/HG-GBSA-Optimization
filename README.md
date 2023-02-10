# HG-GBSA-Optimization
This repository contains files for running force field optimization fitted to host-guest binding data using [OpenFF-Evaluator](https://github.com/openforcefield/openff-evaluator) and [ForceBalance](https://github.com/leeping/forcebalance). The example here optimizes the Generalized Born radius of oxygen atom to fit the binding free energy $\beta$-cyclodextrin with hexanoate acid compiled in [Taproom](https://github.com/slochower/host-guest-benchmarks). The binding free energy is estimated with the attach-pull-release (APR) method using the [pAPRika](https://github.com/slochower/pAPRika) package.


## Dependencies
There are a few additional packages that is required to run the scripts in this repository. In particular, the `openeye-toolkits` package is needed to run the host-guest binding calculations in `openff-evaluator`. In addition, we will need a forked version of ForceBalance/
* openeye-toolkits
* ForceBalance ([forked version](https://github.com/jeff231li/forcebalance))

## Installation instructions
Get the `openff-evaluator` package from the OpenFF GitHub repository
```bash
git clone https://github.com/openforcefield/openff-evaluator.git
```

change the current branch to `paprika-latest-features`

```bash
git checkout paprika-latest-features
```

Change the `name` field in `devtools/conda-envs/test_env.yaml` to be `openff-evaluator`. Then create the environment with conda (or [mamba](https://github.com/mamba-org/mamba) if you have it installed).

```bash
conda env create -f devtools/conda-envs/test_env.yaml
```
After the environment is created, activate the environment: `conda activate openff-evaluator` and install the `openff-evaluator` in the environment.

```bash
pip install .
```

We will also need to install the OpenEye-Toolkits in order to run host-guest binding calculations with `openff-evaluator`.

```bash
conda install -c openeye openeye-toolkits
```

Next, download a forked version of ForceBalance in a different folder
```bash
git clone https://github.com/jeff231li/forcebalance.git
```

and checkout to the evaluator-paprika-tleap branch
```bash
git checkout evaluator-paprika-tleap
```

Finally, install the repository in the conda environment

```bash
python setup.py install
```
