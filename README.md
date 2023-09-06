# HG-GBSA-Optimization
This repository contains files for running force field optimization fitted to host-guest binding data using [OpenFF-Evaluator](https://github.com/openforcefield/openff-evaluator) and [ForceBalance](https://github.com/leeping/forcebalance). This is part of the work of optimizing generalized Born surface area (GBSA) parameters to host-guest systems, detailed in the paper titled *"Tuning Potential Functions to Host-Guest Binding Data"*. Below, I will detail the installation process of the main program and the dependencies. I will show an example to optimize the generalized Born radius of oxygen atom to fit the binding free energy $\Delta G_{\rm b}$ of $\beta$-cyclodextrin ($\beta$CD) with hexanoate acid compiled in [Taproom](https://github.com/slochower/host-guest-benchmarks). The binding free energy $\Delta G_{\rm b}$ is estimated with the attach-pull-release (APR) method using the [pAPRika](https://github.com/slochower/pAPRika) package.


## Dependencies
The main programs that were modified for the work in the paper *"Tuning Potential Functions to Host-Guest Binding Data"* are:
* OpenFF-Evaluator (commit: d88465023ee66ce8ae19713fce0d8a39429faa7e)
* pAPRika (commit: d34f2729fd4ce4914642b332ed8f8417cd22a5b5)
* Taproom (commit: 0d136278ac7bfe00dcea1107cc2b2b207f5ede74)

The modified codes still lives in a separate branch called ***paprika_implicit_paper*** in all of the above repository. The SHA in the parenthesis are the latest commit I've tested for each of the repository listed. The modified code that enables the calculations of $\Delta G_{\rm b}$ and $\Delta G_{\rm solv}$ with implicit solvent is currently only available in a [forked](https://github.com/jeff231li/openff-evaluator.git) version of OpenFF-Evaluator. We will do our best to merge these codes in the not too distant future and release them as part of the main code base(s).

> **_NOTE:_** From [version 0.4.4](https://github.com/openforcefield/openff-evaluator/releases/tag/v0.4.4), Yank was removed from OpenFF-Evaluator and no longer supported in future releases. In the future, the solvation free energy $\Delta G_{\rm solv}$ workflow will be replaced with [Perses](https://github.com/choderalab/perses.git).

There are a few dependencies that is required to run the scripts in this repository. In particular, the `openeye-toolkits` package is needed to run the host-guest binding calculations in `openff-evaluator`. This toolkit takes care of generating the SMILES strings, MOL2 files and assigning partial charges. The optimization process is handled with ForceBalance.
* [OpenEye Toolkits](https://docs.eyesopen.com/toolkits/python/index.html)
* [ForceBalance](https://github.com/leeping/forcebalance)

> **_NOTE:_** You will need to have a valid license from OpenEye to use their toolkit!

I have not tested the optimization with the minimal forked version of ForceBalance -- [OpenFF-ForceBalance](https://github.com/openforcefield/openff-forcebalance.git). In principle, the OpenFF version should work as well.

## Manual Installation
The instructions below attempts to install the different dependencies manually with `conda`. The software dependencies are listed in the file `devtools/conda-envs/test_env.yaml` in the OpenFF-Evaluator repository.

### OpenFF-Evaluator 
* Get the `openff-evaluator` package from the OpenFF GitHub repository
```bash
git clone https://github.com/jeff231li/openff-evaluator.git
```

* change the current branch to `paprika_implicit_paper`

```bash
git checkout paprika_implicit_paper
```

* Change the `name` field in `devtools/conda-envs/test_env.yaml` to be `openff-evaluator`. Then create the environment with conda (or [mamba](https://github.com/mamba-org/mamba) if you have it installed).

```bash
conda env create -f devtools/conda-envs/test_env.yaml
```
* After the environment is created, activate the environment: `conda activate openff-evaluator` and install the `openff-evaluator` in the environment.

```bash
pip install .
```

### pAPRika
* Get the `paprika` package from the Gilson Lab GitHub repository
```bash
git clone https://github.com/GilsonLabUCSD/pAPRika.git
```

* change the current branch to `paprika_implicit_paper`

```bash
git checkout paprika_implicit_paper
```

* Install pAPRika in the conda environment
```bash
pip install .
```

### Taproom
* Get the `taproom` package
```bash
git clone https://github.com/slochower/host-guest-benchmarks.git
```

* change the current branch to `paprika_implicit_paper`

```bash
git checkout paprika_implicit_paper
```

* Install taproom in the conda environment
```bash
pip install .
```

### OpenEye Toolkits
We will also need to install the OpenEye-Toolkits in order to run host-guest binding calculations with `openff-evaluator`.

```bash
conda install -c openeye openeye-toolkits
```

### ForceBalance
Next, download ForceBalance from Lee-Ping's GitHub
```bash
git clone https://github.com/leeping/forcebalance.git
```

Finally, install the repository in the conda environment

```bash
python setup.py install
```

## Installing through YAML file
If the previous steps does not work, we can install the software using the YAML file [paprika_implicit_paper.yaml](installation_files/paprika_implicit_paper.yaml). This file was exported from my conda environment that was installed with Python version 3.9. Install the environment with 
```bash
conda env create -f paprika_implicit_paper.yaml python=3.9
```
Then you will need to install OpenFF-Evaluator, pAPRika, and Taproom as previously, i.e. by `git clone` and `pip install .` in the newly created environment.

> **_NOTE:_** I have also included in this repository my yaml files for **Dask** (`dask.yaml`, `distributed.yaml`, and `jobqueue.yaml`). If you are having issues with Dask when you run the Python script, copy these files to `~/.config/dask/`. 