from enum import Enum

class ProjectionMethodEnum(Enum):
    UMAP = 1
    UMAP_Approx = 2
    CEBRA = 3

    @classmethod
    def from_string(cls, method_string : str):
        return cls[method_string]