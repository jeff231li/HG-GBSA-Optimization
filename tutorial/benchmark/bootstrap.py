import numpy as np
from tqdm import tqdm
from scipy import stats


def summarize(x, y):

    summary_statistics = np.empty(8)
    # Slope, intercept, R
    (
        summary_statistics[0],
        summary_statistics[1],
        summary_statistics[2],
        pval,
        stderr,
    ) = stats.linregress(x, y)
    # R**2
    summary_statistics[3] = summary_statistics[2] ** 2
    # RMSE
    summary_statistics[4] = np.sqrt(np.mean((y - x) ** 2))
    # MSE
    summary_statistics[5] = np.mean(y - x)
    # MUE
    summary_statistics[6] = np.mean(np.absolute(y - x))
    # Tau
    summary_statistics[7], prob = stats.kendalltau(x, y)

    return summary_statistics


def bootstrap(
    x, x_sem, y, y_sem, cycles=1000, with_replacement=True, with_uncertainty=True
):
    summary_statistics = np.empty((cycles, 8))
    for cycle in range(cycles):
        new_x = np.empty_like(x)
        new_y = np.empty_like(y)
        for index in range(len(x)):
            if with_replacement:
                j = np.random.randint(len(x))
            else:
                j = index
            if with_uncertainty and x_sem is not None:
                new_x[index] = np.random.normal(x[j], x_sem[j])
            elif with_uncertainty and x_sem is None:
                new_x[index] = x[j]
            if with_uncertainty and y_sem is not None:
                new_y[index] = np.random.normal(y[j], y_sem[j])
            elif with_uncertainty and y_sem is None:
                new_y[index] = y[j]
        summary_statistics[cycle] = summarize(new_x, new_y)

    ci = np.empty((8, 2))
    for statistic in range(8):
        sorted_statistic = np.sort(summary_statistics[:, statistic])
        ci[statistic][0] = sorted_statistic[int(0.025 * cycles)]
        ci[statistic][1] = sorted_statistic[int(0.975 * cycles)]

    results = {
        "mean": {
            "slope": np.mean(summary_statistics[:, 0]),
            "intercept": np.mean(summary_statistics[:, 1]),
            "R": np.mean(summary_statistics[:, 2]),
            "R**2": np.mean(summary_statistics[:, 3]),
            "RMSE": np.mean(summary_statistics[:, 4]),
            "MSE": np.mean(summary_statistics[:, 5]),
            "MUE": np.mean(summary_statistics[:, 6]),
            "Tau": np.mean(summary_statistics[:, 7]),
        },
        "sem": {
            "slope": np.std(summary_statistics[:, 0]),
            "intercept": np.std(summary_statistics[:, 1]),
            "R": np.std(summary_statistics[:, 2]),
            "R**2": np.std(summary_statistics[:, 3]),
            "RMSE": np.std(summary_statistics[:, 4]),
            "MSE": np.std(summary_statistics[:, 5]),
            "MUE": np.std(summary_statistics[:, 6]),
            "Tau": np.std(summary_statistics[:, 7]),
        },
        "ci_low": {
            "slope": ci[0][0],
            "intercept": ci[1][0],
            "R": ci[2][0],
            "R**2": ci[3][0],
            "RMSE": ci[4][0],
            "MSE": ci[5][0],
            "MUE": ci[6][0],
            "Tau": ci[7][0],
        },
        "ci_high": {
            "slope": ci[0][1],
            "intercept": ci[1][1],
            "R": ci[2][1],
            "R**2": ci[3][1],
            "RMSE": ci[4][1],
            "MSE": ci[5][1],
            "MUE": ci[6][1],
            "Tau": ci[7][1],
        },
    }
    return results


def dG_bootstrap(
    x, x_sem, y, y_sem, cycles=1000, with_replacement=True, with_uncertainty=True
):
    summary_statistics = np.empty((cycles))
    R = 1.987204118e-3  # kcal/mol-K
    temperature = 300  # K
    beta = 1.0 / (R * temperature)

    for cycle in tqdm(range(cycles)):
        new_x = np.empty_like(x)
        new_y = np.empty_like(y)

        if with_uncertainty and x_sem is not None:
            new_x = np.random.normal(x, x_sem)
        elif with_uncertainty and x_sem is None:
            new_x = x
        if with_uncertainty and y_sem is not None:
            new_y = np.random.normal(y, y_sem)
        elif with_uncertainty and y_sem is None:
            new_y = y
        summary_statistics[cycle] = (
            -R * temperature * np.log(np.exp(-beta * new_x) + np.exp(-beta * new_y))
        )

        sorted_statistic = np.sort(summary_statistics)
        ci = np.empty((2))
        ci[0] = sorted_statistic[int(0.025 * cycles)]
        ci[1] = sorted_statistic[int(0.975 * cycles)]

    results = {
        "mean": np.mean(summary_statistics),
        "sem": np.std(summary_statistics),
        "ci": ci,
    }
    return results


def dH_bootstrap(
    dH_x,
    dH_x_sem,
    dH_y,
    dH_y_sem,
    dG_x,
    dG_x_sem,
    dG_y,
    dG_y_sem,
    cycles=1000,
    with_replacement=True,
    with_uncertainty=True,
):
    summary_statistics = np.empty((cycles))
    R = 1.987204118e-3  # kcal/mol-K
    temperature = 300  # K
    beta = 1.0 / (R * temperature)

    for cycle in tqdm(range(cycles)):
        new_dH_x = np.empty_like(dH_x)
        new_dH_y = np.empty_like(dH_y)

        new_dG_x = np.empty_like(dG_x)
        new_dG_y = np.empty_like(dG_y)

        # Resample dH
        if with_uncertainty and dH_x_sem is not None:
            new_dH_x = np.random.normal(dH_x, dH_x_sem)
        elif with_uncertainty and dH_x_sem is None:
            new_dH_x = dH_x
        if with_uncertainty and dH_y_sem is not None:
            new_dH_y = np.random.normal(dH_y, dH_y_sem)
        elif with_uncertainty and dH_y_sem is None:
            new_dH_y = dH_y

        # Resample dG
        if with_uncertainty and dG_x_sem is not None:
            new_dG_x = np.random.normal(dG_x, dG_x_sem)
        elif with_uncertainty and dG_x_sem is None:
            new_dG_x = dG_x
        if with_uncertainty and dG_y_sem is not None:
            new_dG_y = np.random.normal(dG_y, dG_y_sem)
        elif with_uncertainty and dG_y_sem is None:
            new_dG_y = dG_y

        summary_statistics[cycle] = (
            new_dH_x * np.exp(-beta * new_dG_x) + new_dH_y * np.exp(-beta * new_dG_y)
        ) / (np.exp(-beta * new_dG_x) + np.exp(-beta * new_dG_y))

    sorted_statistic = np.sort(summary_statistics)
    ci = np.empty((2))
    ci[0] = sorted_statistic[int(0.025 * cycles)]
    ci[1] = sorted_statistic[int(0.975 * cycles)]

    results = {
        "mean": np.mean(summary_statistics),
        "sem": np.std(summary_statistics),
        "ci": ci,
    }
    return results
