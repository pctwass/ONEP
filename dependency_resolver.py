import os
import sys

reference_module_paths = [
    './',  
    './utils',
    './plotly_services',
    './projector',  
    './projector/projection_methods/submodules/CEBRA', # CEBRA submodule
    './projector/projection_methods/submodules/CEBRA/cebra' # CEBRA submodule
]

for module_path in reference_module_paths:
    reference_path = os.path.abspath(module_path)
    sys.path.append(reference_path)
