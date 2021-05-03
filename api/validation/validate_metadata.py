#!/usr/bin/env python

import argparse
import json
import os

from pydantic import ValidationError

from validation import schemas


def validate_metadata(schema, metadata_path):
    """
    Validate metadata according to a schema

    Inputs:
        schema: One of the classes defined in schemas
        metadata_path: Path to metadata file (preferably with extension JSON)

    If validation is successful:
        Returns the validated schema object
        Writes validated metadata to JSON file

    If validation is unsuccessful:
        Returns Pydantic validation error
        Writes errors to JSON file
    """
    print(f"Validating metadata file '{metadata_path}'...")

    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    metadata_filename, _ = os.path.splitext(metadata_path)

    try:
        metadata = schema(**metadata)
        result_complete_filename = f"{metadata_filename}_validated.json"
        with open(result_complete_filename, "w") as f:
            json.dump(metadata.dict(), f)
        print(
            f":-) Validation successful, validated metadata saved at '{result_complete_filename}'"
        )
        return metadata

    except ValidationError as e:
        result_complete_filename = f"{metadata_filename}_errors.json"
        with open(result_complete_filename, "w") as f:
            json.dump(e.errors(), f)
        print(
            f":-( Validation failed due to the following errors (also saved at '{result_complete_filename}')"
        )
        print(e)
        return e


# Make executable as well
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument(
        "-c",
        "--cube",
        action="store_true",
        help="If set, validate cube metadata instead of model",
    )
    args = parser.parse_args()

    if args.cube:
        validate_metadata(schemas.CubeMetadataFromModeler, args.input)
    else:
        validate_metadata(schemas.ModelMetadata, args.input)
