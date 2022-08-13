To run the optimization script make sure you have your conda environement activated

```bash
conda activate openff-evaluator
```

Note: the input file for ForceBalance is defined in the configuration file [`optimize.in`](optimize.in).

Run the following either on your local machine or distributed cluster (see the Evaluator [docs](https://docs.openforcefield.org/projects/evaluator/en/latest/backends/daskbackends.html))

```bash
python optimization-FB-host-guest.py &> console_output.log
```

Once the optimization is complete, you can use the jupyter notebook provided herer [`plot_forcebalance_results.ipynb`](plot_forcebalance_results.ipynb) to extract and analyze the output from `ForceBalance` & `OpenFF-Evaluator`.


