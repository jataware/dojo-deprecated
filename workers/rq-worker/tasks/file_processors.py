from fileinput import filename
import logging
import os
import requests
import tempfile

import pandas as pd
import xarray as xr
from raster2xyz.raster2xyz import Raster2xyz

from mixmasta import mixmasta as mix
from base_annotation import BaseProcessor
from utils import DATASET_STORAGE_BASE_URL, get_rawfile, put_rawfile

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


class FileLoadProcessor(BaseProcessor):
    @staticmethod
    def run(context):
        """loads the file into a dataframe"""
        fp = context["uploaded_file_fp"]
        logging.info(f"{context.get('logging_preface', '')} - Loading file {fp}")

        extension_mapping = {
            "xlsx": ExcelLoadProcessor,
            "xls": ExcelLoadProcessor,
            "tif": GeotiffLoadProcessor,
            "tiff": GeotiffLoadProcessor,
            "csv": CsvLoadProcessor,
            "nc": NetcdfLoadProcessor,
        }

        if isinstance(fp, str):
            for extension, processor in extension_mapping.items():
                if fp.lower().endswith(extension):
                    df = processor().run(context)
                    return df
        t = type(fp)
        raise ValueError(f"Unable to map '{fp} to a processor, type: {t}")


class CsvLoadProcessor(BaseProcessor):
    @staticmethod
    def run(context):
        """load csv"""
        ft = "csv"
        context["ft"] = ft
        fp = context["uploaded_file_fp"]
        df = pd.read_csv(fp)
        return df


class NetcdfLoadProcessor(BaseProcessor):
    @staticmethod
    def run(context):
        """load netcdf"""
        ft = "netcdf"
        context["ft"] = ft

        fp = context["uploaded_file_fp"]
        df = mix.netcdf2df(fp)
        return df


class ExcelLoadProcessor(BaseProcessor):
    @staticmethod
    def run(context):
        """load excel"""
        ft = "excel"
        context["ft"] = ft
        file_context = context["annotations"]["metadata"]["files"][context["current_filename"]]

        fp = context["uploaded_file_fp"]
        sheet = file_context.get("excel_Sheet", None)
        if sheet == None:
            df = pd.read_excel(fp)
        else:
            df = pd.read_excel(fp, sheet_name=sheet)
        return df


class GeotiffLoadProcessor(BaseProcessor):
    @staticmethod
    def run(context):
        """load geotiff"""
        fp = context["uploaded_file_fp"]
        ft = "geotiff"
        file_context = context["annotations"]["metadata"]["files"][context["current_filename"]]
        context["annotations"]["metadata"]["ft"] = ft
        context_annotations_meta = context["annotations"]["metadata"]

        def single_band_run():
            feature_name, band, date, nodataval = (
                file_context["geotiff_feature_name"],
                file_context.get("band", 1),
                file_context["geotiff_date"],
                file_context["geotiff_null_value"],
            )

            df = mix.raster2df(
                fp, feature_name=feature_name, band=band, date=date, nodataval=nodataval
            )
            return df

        def multiband_run():
            fp = context["uploaded_file_fp"]

            # time
            logging.info(f"context is: {context}")
            df = mix.raster2df(
                fp,
                feature_name=file_context.get(
                    "geotiff_feature_name", "feature"
                ),
                band_name=file_context.get(
                    "geotiff_feature_name", "feature"
                ),
                date=file_context.get("geotiff_date", "01/01/2001"),
                bands=file_context.get("geotiff_bands", {}),
                band_type=file_context.get("geotiff_band_type", "category"),
            )
            return df.sort_values(by="date")

        if file_context.get("geotiff_bands", False):
            return multiband_run()
        else:
            return single_band_run()


# class SaveProcessorCsv(BaseProcessor):
#     @staticmethod
#     def run(context, df):
#         """save df to output_path"""
#         output_path = context.get("output_path")
#         df.to_csv(output_path, index=False)
#         return df


def file_conversion(context, filename=None):
    # Get raw file
    uuid = context["uuid"]
    processor = FileLoadProcessor()

    # Grabbing filename from context if it isn't passed in.
    if filename is None:
        filename = list(context["annotations"]["metadata"]["files"].keys())[0]
    # TODO: Determine if we still need this
    # else:
    #     # Replacing the file metadata in the case where we pass them into the metadata context for an append action.
    #     context["annotations"]["metadata"] = context["annotations"]["metadata"][
    #         "files"
    #     ][
    #         filename
    #     ]  # This change to context is not persisted.

    raw_path = os.path.join(DATASET_STORAGE_BASE_URL, uuid, filename)
    raw_file = get_rawfile(raw_path)

    with tempfile.TemporaryDirectory() as tmpdirname:
        local_file_fp = os.path.join(tmpdirname, filename)
        with open(local_file_fp, 'wb') as local_file:
            for chunk in raw_file:
                local_file.write(chunk)

        context["uploaded_file_fp"] = local_file_fp  # Unpersisted update
        context["current_filename"] = filename
        df = processor.run(context=context)

        basename, _ = os.path.splitext(filename)
        temp_output_file = os.path.join(tmpdirname, "output.csv")
        csv_file_path = os.path.join(DATASET_STORAGE_BASE_URL, uuid, f'{basename}.csv')
        df.to_csv(temp_output_file, index=False)
        with open(temp_output_file, 'rb') as csv_file:
            put_rawfile(csv_file_path, csv_file)

        # with open(os.path.join(tmpdirname, "output.csv"), 'wb') as csv_file:
        # sample_output_path = os.path.join(DATASET_STORAGE_BASE_URL, file_path)
        # with open(sample_fp, 'rb') as sample_file:
        #     put_rawfile(sample_output_path, sample_file)

    # excel_tuple = ("xlsx", "xls")
    # tif_tuple = ("tif", "tiff")

    # if filename.endswith(excel_tuple):
    #     sheet = context["annotations"]["metadata"].get(
    #         "excel_sheet", 0
    #     )  # 0 is the first sheet if none is provided.

    #     read_file = pd.read_excel(raw_file, sheet_name=sheet)

    #     read_file.to_csv("./xlsx_to.csv", index=None, header=True)

    #     with open("./xlsx_to.csv", "rb") as fileobj:
    #         output_filename = filename.split(".")[0] + ".csv"
    #         dest_path = os.path.join(DATASET_STORAGE_BASE_URL, uuid, output_filename)
    #         put_rawfile(dest_path, fileobj)

    #     os.remove("./xlsx_to.csv")

    # elif filename.endswith(tif_tuple):

    #     response = geotif_to_CSV(context, raw_file, filename)

    #     return response

    # elif filename.endswith(".nc"):
    #     response = netCDF_to_CSV(uuid, raw_file, filename)

    #     return response

    return csv_file_path

def netCDF_to_CSV(uuid, fileobj, filename):
    """Convert NETCDF to CSV"""
    original_file = fileobj

    open_netcdf = xr.open_dataset(original_file)
    df = open_netcdf.to_dataframe()
    df.reset_index().to_csv("./convertedCSV.csv", index=False)
    with open("./convertedCSV.csv", "rb") as f:
        output_filename = filename.split(".")[0] + ".csv"
        dest_path = os.path.join(DATASET_STORAGE_BASE_URL, uuid, output_filename)
        put_rawfile(dest_path, f)

    os.remove("./convertedCSV.csv")


def geotif_to_CSV(context, fileobj, filename):
    original_file = fileobj
    uuid = context["uuid"]
    context_metadata = context["annotations"]["metadata"]["files"][filename]

    with open("./tempGeoTif.tif", "wb") as f:
        f.write(original_file.read())

    glp = GeotiffLoadProcessor()
    context["annotations"]["metadata"]["uploaded_file_fp"] = "./tempGeoTif.tif"
    context["annotations"]["metadata"]["geotiff_feature_name"] = "feature"
    # Makes the band/bands dictionary. Band is set for single band runs, bands is set for multiband runs.
    context["geotiff_null_value"] = context_metadata.get("geotiff_null_value", 0)
    if len(context_metadata.get("geotiff_bands", [])) > 1:
        context["geotiff_bands"] = context_metadata["geotiff_bands"]
        band_type = context_metadata["geotiff_band_type"]
        if band_type == "temporal":
            band_type = "datetime"
            context["annotations"]["metadata"][
                "geotiff_feature_name"
            ] = context_metadata["geotiff_value"]
        elif band_type == "category":
            context["annotations"]["metadata"]["geotiff_date"] = (
                context_metadata["geotiff_value"]
                if context_metadata["geotiff_band_type"] == "category"
                else "01/01/2001"
            )

        context["annotations"]["metadata"]["geotiff_band_type"] = band_type
    else:
        context["annotations"]["metadata"]["geotiff_feature_name"] = context_metadata[
            "geotiff_value"
        ]
        context["annotations"]["metadata"]["geotiff_date"] = context_metadata[
            "geotiff_date_value"
        ]

    df = glp.run(context)
    df.to_csv("./convertedCSV.csv", index=None, header=True)

    with open("./convertedCSV.csv", "rb") as f:
        output_filename = filename.split(".")[0] + ".csv"
        dest_path = os.path.join(DATASET_STORAGE_BASE_URL, uuid, output_filename)
        put_rawfile(dest_path, f)

    os.remove("./tempGeoTif.tif")
    os.remove("./convertedCSV.csv")


def model_output_preview(context, *args, **kwargs):
    fileurl = context['annotations']['metadata']['fileurl']
    filepath = context['annotations']['metadata']['filepath']
    file_uuid = context['annotations']['metadata']['file_uuid']

    url = f"{os.environ['CLOUSEAU_ENDPOINT']}{fileurl}"

    req = requests.get(url, stream=True)
    stream = req.raw

    filename = os.path.basename(filepath)
    processor = FileLoadProcessor()

    with tempfile.TemporaryDirectory() as tmpdirname:
        local_file_fp = os.path.join(tmpdirname, filename)
        with open(local_file_fp, 'wb') as local_file:
            for chunk in stream:
                local_file.write(chunk)

        context["uploaded_file_fp"] = local_file_fp  # Unpersisted update
        df = processor.run(context=context)
        
        sample = df.head(100)
        sample_fp = os.path.join(tmpdirname, "sample.csv")
        sample.to_csv(sample_fp, index=False)

        file_path = os.path.join('model-output-samples', context['uuid'], f'{file_uuid}.csv')
        sample_output_path = os.path.join(DATASET_STORAGE_BASE_URL, file_path)
        with open(sample_fp, 'rb') as sample_file:
            put_rawfile(sample_output_path, sample_file)

    return file_path
        

