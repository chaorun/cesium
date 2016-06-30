from sklearn.externals import joblib
from sklearn.grid_search import GridSearchCV
import os
import numpy as np
import pandas as pd
import xarray as xr
from . import build_model
from . import featurize
from . import time_series
from . import util


__all__ = ['model_predictions', 'predict_data_files']


def model_predictions(featureset, model, return_probs=True):
    """Construct a DataFrame of model predictions for given featureset.

    Parameters
    ----------
    featureset : xarray.Dataset
        Dataset containing feature values for which predictions are desired
    model : scikit-learn model
        Fitted scikit-learn model to be used to generate predictions
    return_probs : bool, optional
        Parameter to control the type of prediction made in the classification
        setting (the parameter has no effect for regression models). If True,
        probabilities for each class are returned where possible; if False,
        only the top predicted label for each time series is returned.

    Returns
    -------
    pandas.DataFrame
        DataFrame of model predictions, indexed by `featureset.name`. Each row
        contains either a single class/target prediction or (for probabilistic
        predictions) a list of class probabilities.
    """
    feature_df = build_model.rectangularize_featureset(featureset)
    if return_probs and hasattr(model, 'predict_proba'):
        preds = model.predict_proba(feature_df)
    else:
        preds = model.predict(feature_df)

    predset = featureset.copy()
    if len(preds.shape) == 1:
        predset['prediction'] = (['name'], preds)
    else:
        if isinstance(model, GridSearchCV):
            columns = model.best_estimator_.classes_
        else:
            columns = model.classes_
        predset['class_label'] = columns
        predset['prediction'] = (['name', 'class_label'], preds)
    return predset


# TODO would be nice if model tracked the names of features so they didn't have
# to be passed in here
def predict_data_files(ts_paths, features_to_use, model, output_path=None,
                       custom_features_script=None):
    """Generate features from new TS data and perform model prediction.

    Generates features for new time series file, loads saved
    estimator model, calculates target predictions with extracted
    features, and returns a dictionary containing a list of target
    prediction probabilities, a string containing HTML markup for a
    table containing a list of the results, the time-series data itself
    used to generate features, and a dictionary of the features
    extracted. The respective dict keys of the above-mentioned values
    are: "pred_results", "results_str", "ts_data", "features_dict".

    Parameters
    ----------
    ts_paths : str
        Path to netCDF files containing seriealized TimeSeries objects to be
        used in prediction.
    features_to_use : list of str
        List of features to extract for new time series data
    model : scikit-learn model
        Model to use for making predictions on new input time series
    custom_features_script : str, optional
        Path to custom features script to be used in feature
        generation. Defaults to None.

    Returns
    -------
    dict
        Returns dictionary whose keys are the file names of the
        individual time-series data files used in prediction and whose
        corresponding values are dictionaries with the following
        key-value pairs:

            - "results_str": String containing table listing results in markup.
            - "ts_data": The original time-series data provided.
            - "features_dict": A dictionary containing the generated features.
            - "pred_results": A list of lists, each containing one of the
              most-probable targets and its probability.
    """
    fset = featurize.featurize_data_files(ts_paths,
               features_to_use=features_to_use,
               custom_script_path=custom_features_script)
    if output_path:
        fset.to_netcdf(output_path)
    return model_predictions(fset, model)