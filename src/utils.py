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
    model, X_train, X_test, y_train, y_test, random_state = args

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
            test_idx = np.array(list(set(sample_indicators) - set(train_idx)))
            yield train_idx, test_idx


@jit
def point632p_score(weight, train_score, test_score):

    return weight * train_score + (1 - weight) * test_score


@jit
def omega(rel_overfit_rate):

    return 0.632 / (1 - 0.632) * rel_overfit_rate


@jit
def rel_overfit_rate(train_score, test_score, gamma):

    return (test_score - train_score) / (gamma - 1 + train_score)


def no_info_rate(y_true, y_pred):

    true_unique, true_counts = np.unique(y_true, return_counts=True)
    pred_unique, pred_counts = np.unique(y_pred, return_counts=True)

    # Sanity check.
    #assert np.all(pred_unique in true_unique)

    true_proportions = true_counts / np.size(y_true)
    pred_proportions = 1 - (pred_counts / np.size(y_true))

    return np.sum(true_proportions * pred_proportions)
