# -*- coding: utf-8 -*-
#
# model_comparison.py
#

"""
"""

__author__ = 'Severin Langberg'
__email__ = 'langberg91@gmail.com'


import os
import utils
import ioutil
import shutil
import logging
import model_selection

import numpy as np
import pandas as pd

from multiprocessing import cpu_count

from sklearn.externals import joblib
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import ParameterGrid


TMP_RESULTS = 'tmp_model_comparison'


def model_comparison(*args, verbose=0, score_func=None, n_jobs=None, **kwargs):
    # Collecting repeated average performance data of optimal models.
    estimators, param_grids, X, y, random_states, n_splits = args

    global TMP_RESULTS

    #logger = logging.getLogger(__name__)
    #logger.info('Model comparison')

    # Set number of CPUs.
    if n_jobs is None:
        n_jobs = cpu_count() - 1 if cpu_count() > 1 else cpu_count()

    experiment, comparison_results = None, {}
    for name, estimator in estimators.items():

        # Setup hyperparameter grid.
        hparam_grid = ParameterGrid(param_grids[name])

        # Repeated experimental results.
        comparison_results[estimator.__name__] = joblib.Parallel(
            n_jobs=n_jobs, verbose=verbose
        )(
            joblib.delayed(model_selection.nested_cross_val)(
                X, y, estimator, hparam_grid, n_splits, random_state,
                verbose=verbose, score_func=score_func
            ) for random_state in random_states
        )
    # Write results to disk.
    ioutil.write_comparison_results(
        './comparison_results.csv', comparison_results
    )
    return comparison_results


if __name__ == '__main__':
    # NB:
    # Setup temp dirs holding prelim results.
    # Implement feature selection.

    # TODO checkout:
    # * ElasticNet + RF
    # * Upsampling/resampling
    # * Generate synthetic samples with SMOTE algorithm (p. 216).
    # * Display models vs feature sel in heat map with performance.
    # * Display model performance as function of num selected features.

    from sklearn.linear_model import LogisticRegression
    from sklearn.linear_model import ElasticNet

    from sklearn.datasets import load_breast_cancer
    from sklearn.metrics import roc_auc_score

    cancer = load_breast_cancer()
    # NB: roc_auc_score requires binary <int> target values.
    y = cancer.target
    X = cancer.data

    # SETUP
    # NOTE: Number of CV folds
    n_splits = 2

    # NOTE: Number of experiments
    random_states = np.arange(3)

    estimators = {
        'logreg': LogisticRegression,
        'elnet': ElasticNet
    }
    param_grids = {
        'logreg': {
            'C': [0.001, 0.05, 0.1]
        },
        'elnet': {
            'alpha': [0.05, 0.1], 'l1_ratio':[0.1, 0.5]
        }
    }
    results = model_comparison(
        estimators, param_grids, X, y, random_states, n_splits,
        score_func=roc_auc_score
    )
