import os
import sys


def add_cebra_submodule_to_path():
    cebra_module_paths = [
        './projector/projection_methods/submodules/CEBRA'
        './projector/projection_methods/submodules/CEBRA/cebra'
    ]
    add_to_path(cebra_module_paths)


def add_to_path(module_paths : list[str]):
    for module_path in module_paths:
        reference_path = os.path.abspath(module_path)
        sys.path.append(reference_path)
