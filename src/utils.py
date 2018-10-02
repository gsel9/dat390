import os
import numpy as np

from numba import jit
from sklearn.preprocessing import StandardScaler


def multi_intersect(arrays):
    """Determines the intersection between multiple sets."""

    sets = [set(array) for array in arrays]
    matches = set.intersection(*sets)

    return list(matches)


def train_test_z_scores(X_train, X_test):
    """Compute Z-scores for training and test sets.

    Args:
        X_train (array-like): Training set.
        X_test (array-like): Test set.

    Returns:
        (tuple): Standard score values for training and test set.

    """

    # NOTE: Avoid leakage by transforming test data with training params.
    scaler = StandardScaler()
    X_train_std = scaler.fit_transform(X_train)
    X_test_std = scaler.transform(X_test)

    return X_train_std, X_test_std


def scale_fit_predict(*args, score_func=None, **kwargs):
    model, X_train, X_test, y_train, y_test = args

    X_train_std, X_test_std = train_test_z_scores(X_train, X_test)

    model.fit(X_train_std, y_train)

    # Aggregate model predictions with hparams combo and feature subset.
    train_score = score_func(y_train, model.predict(X_train_std))
    test_score = score_func(y_test, model.predict(X_test_std))

    return train_score, test_score


class BootstrapOutOfBag:

    def __init__(self, n_splits=10, random_state=None):

        self.n_splits = n_splits
        self.random_state = random_state

    def split(self, X, y, **kwargs):

        rand_gen = np.random.RandomState(self.random_state)

        nrows, _ = np.shape(X)
        sample_indicators = np.arange(nrows)
        for _ in range(self.n_splits):
            train_idx = rand_gen.choice(
                sample_indicators, size=nrows, replace=True
            )
            test_idx = np.array(
                list(set(sample_indicators) - set(train_idx)), dtype=int
            )
            yield train_idx, test_idx


@jit
def _point632p_score(weight, train_error, test_error):

    return (1 - weight) * train_error + weight * test_error


@jit
def _omega(train_error, test_error, gamma):

    rel_overfit_rate = (test_error - train_error) / (gamma - train_error)

    return 0.632 / (1 - (0.368 * rel_overfit_rate))


def _no_info_rate(y_true, y_pred):

    # NB: Only applicable to a dichotomous classification problem.
    p_one, q_one = np.sum(y_true == 1), np.sum(y_pred == 1)

    return p_one * (1 - q_one) + (1 - p_one) * q_one


def point632p_score(y_true, y_pred, train_score, test_score):

    train_error, test_error = 1.0 - train_score, 1.0 - test_score

    # Compute .632+ train score.
    weight = _omega(
        train_error, test_error, _no_info_rate(y_true, y_pred)
    )
    score = _point632p_score(weight, train_error, test_error)

    return score
