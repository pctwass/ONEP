import abc
import pandas as pd
from projection_methods.projection_methods_enum import ProjectionMethodEnum


class IProjectionMethod(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'get_method_type') and 
                callable(subclass.get_method_type) and 
                hasattr(subclass, 'fit_new') and 
                callable(subclass.fit_new) and 
                hasattr(subclass, 'fit_update') and 
                callable(subclass.fit_update) and 
                hasattr(subclass, 'produce_projection') and 
                callable(subclass.produce_projection))
    

    # Returns the projection method of the wrapper class.
    def get_method_type(self) -> ProjectionMethodEnum:
        pass


    # Creates a new instance of the projection model, trained on the provided data. 
    def fit_new(self, data: pd.DataFrame, labels = None, time_points = None, past_projections = None):
        pass


    # Fits unlabeled data to the current projection model. 
    # NOTE this method is currently not in use. May be implemented by throwing an "not implemented" exception. 
    def fit_update(self, data : pd.DataFrame, time_points = None):
        pass


    # Produces projections by transforming the provided data using the projection model of the wrapper class.
    def project(self, data: pd.DataFrame, existing_data: pd.DataFrame):
        pass