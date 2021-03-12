# Validation
This folder contains:
- `supermaas_types.py`: A definition of valid types encountered in SuperMaaS. The complete type system spec can be found [here](https://gitlab-ext.galois.com/world-modelers/galois-internal/model-types-spec).
- `schemas.py`:
  - Metadata schemas for modelers as defined [here](https://gitlab-ext.galois.com/world-modelers/galois-internal/supermaas/-/blob/master/docs/metadata.md).
  - Additional schemas for validating SuperMaaS internal metadata (experiments / jobs / etc).
- `validate_parameters.py`: Methods to validate passed parameters during model run.
- `validate_metadata.py`: Executable to validate metadata (see [Running metadata validation](#run-metadata)).


## <a id="run-metadata">Running metadata validation</a>
Modelers can use `validate_metadata.py` to validate their model and/or cube metadata. This can be done either standalone, or as part of model/cube registration scripts. Input metadata files must be in `.json` format. Invoke as:
```
./validate_metadata.py <path/to/metadata/file> [-c/--cube]
```
Set the `-c/--cube` flag only if you want to validate cube metadata.

- If validation is successful, the script saves the validated metadata file as `<path/to/metadata/file>_validated`. This may be reformatted (e.g. [reordered parameters according to dependency](https://gitlab-ext.galois.com/world-modelers/galois-internal/supermaas/-/blob/master/docs/metadata.md#depends_on)).
- If validation is unsuccessful, the errors are stored in `<path/to/metadata/file>_errors`.
