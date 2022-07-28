from fileinput import filename
import logging
import os

import pandas as pd
import xarray as xr
from raster2xyz.raster2xyz import Raster2xyz

from mixmasta import mixmasta as mix
from base_annotation import BaseProcessor
from utils import get_rawfile, put_rawfile

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


class FileLoadProcessor(BaseProcessor):
    @staticmethod
    def run(context, rawfile):
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
                    df = processor().run(df, context)
                    # df.columns = [str(x).strip() for x in df.columns]
                    return df
        t = type(fp)
        raise ValueError(f"Unable to map '{fp} to a processor, type: {t}")


class CsvLoadProcessor(BaseProcessor):
    @staticmethod
    def run(df, context):
        """load csv"""
        ft = "csv"
        context["ft"] = ft
        fp = context["uploaded_file_fp"]
        df = pd.read_csv(fp)
        return df


class NetcdfLoadProcessor(BaseProcessor):
    @staticmethod
    def run(df, context):
        """load netcdf"""
        ft = "netcdf"
        context["ft"] = ft

        fp = context["uploaded_file_fp"]
        df = mix.netcdf2df(fp)
        return df


class ExcelLoadProcessor(BaseProcessor):
    @staticmethod
    def run(df, context):
        """load excel"""
        ft = "excel"
        context["ft"] = ft

        fp = context["uploaded_file_fp"]
        sheet = context.get("excel_Sheet", None)
        if sheet == None:
            df = pd.read_excel(fp)
        else:
            df = pd.read_excel(fp, sheet_name=sheet)
        return df


class GeotiffLoadProcessor(BaseProcessor):
    @staticmethod
    def run(context):
        """load geotiff"""
        fp = context["annotations"]["metadata"]["uploaded_file_fp"]
        ft = "geotiff"
        context["annotations"]["metadata"]["ft"] = ft
        context_annotations_meta = context["annotations"]["metadata"]

        def single_band_run():
            feature_name, band, date, nodataval = (
                context_annotations_meta["geotiff_feature_name"],
                context_annotations_meta.get("band", 1),
                context_annotations_meta["geotiff_date"],
                context_annotations_meta["geotiff_null_value"],
            )

            df = mix.raster2df(
                fp, feature_name=feature_name, band=band, date=date, nodataval=nodataval
            )
            return df

        def multiband_run():
            fp = context_annotations_meta["uploaded_file_fp"]

            # time
            logging.info(f"context is: {context}")
            df = mix.raster2df(
                fp,
                feature_name=context_annotations_meta.get(
                    "geotiff_feature_name", "feature"
                ),
                band_name=context_annotations_meta.get(
                    "geotiff_feature_name", "feature"
                ),
                date=context_annotations_meta.get("geotiff_date", "01/01/2001"),
                bands=context_annotations_meta.get("geotiff_bands", {}),
                band_type=context_annotations_meta.get("geotiff_band_type", "category"),
            )
            return df.sort_values(by="date")

        if context.get("geotiff_bands", False):
            return multiband_run()
        else:
            return single_band_run()


class SaveProcessorCsv(BaseProcessor):
    @staticmethod
    def run(df, context):
        """save df to output_path"""
        output_path = context.get("output_path")
        df.to_csv(output_path, index=False)
        return df


def file_conversion(context, filename=None):
    # Get raw file
    uuid = context["uuid"]
    # Changing the file name if it is passed in, i.e. from an append action.
    if not filename:
        filename = context["annotations"]["metadata"]["rawFileName"]
        # Replacing the file metadata in the case where we pass them into the metadata context for an append action.
        context["annotations"]["metadata"] = context["annotations"]["metadata"][
            filename
        ]  # This change to context is not persisted.
    raw_file = get_rawfile(uuid, filename)
    excel_tuple = ("xlsx", "xls")
    tif_tuple = ("tif", "tiff")

    if filename.endswith(excel_tuple):
        sheet = context["annotations"]["metadata"].get(
            "excel_sheet", 0
        )  # 0 is the first sheet if none is provided.

        read_file = pd.read_excel(raw_file, sheet_name=sheet)

        read_file.to_csv("./xlsx_to.csv", index=None, header=True)

        with open("./xlsx_to.csv", "rb") as fileobj:
            put_rawfile(uuid, None, fileobj)

        os.remove("./xlsx_to.csv")

    elif filename.endswith(tif_tuple):

        response = geotif_to_CSV(context, raw_file)

        return response

    elif filename.endswith(".nc"):
        response = netCDF_to_CSV(uuid, raw_file)

        return response


def netCDF_to_CSV(uuid, fileobj):
    """Convert NETCDF to CSV"""
    original_file = fileobj

    open_netcdf = xr.open_dataset(original_file)
    df = open_netcdf.to_dataframe()
    df.reset_index().to_csv("./convertedCSV.csv")
    with open("./convertedCSV.csv", "rb") as f:
        put_rawfile(uuid, None, f)

    os.remove("./convertedCSV.csv")


def geotif_to_CSV(context, fileobj):
    original_file = fileobj
    uuid = context["uuid"]
    context_metadata = context["annotations"]["metadata"]

    with open("./tempGeoTif.tif", "wb") as f:
        f.write(original_file.read())

    glp = GeotiffLoadProcessor()
    context["annotations"]["metadata"]["uploaded_file_fp"] = "./tempGeoTif.tif"
    context["annotations"]["metadata"]["geotiff_feature_name"] = "feature"
    # Makes the band/bands dictionary. Band is set for single band runs, bands is set for multiband runs.
    context["geotiff_null_value"] = context_metadata.get("geotiff_null_value", 0)
    if len(context_metadata["geotiff_bands"]) > 1:
        context["geotiff_bands"] = context_metadata["geotiff_bands"]
        context["annotations"]["metadata"]["geotiff_date"] = (
            context_metadata["geotiff_value"]
            if context_metadata["geotiff_band_type"] == "category"
            else "01/01/2001"
        )
    else:
        context["annotations"]["metadata"]["geotiff_band"] = (
            context_metadata["geotiff_bands"].keys()
        )[0]
        context["annotations"]["metadata"]["geotiff_date"] = context_metadata[
            "geotiff_value"
        ]

    df = glp.run(context)
    df.to_csv("./convertedCSV.csv", index=None, header=True)

    with open("./convertedCSV.csv", "rb") as f:
        put_rawfile(uuid, None, f)

    os.remove("./tempGeoTif.tif")
    os.remove("./convertedCSV.csv")
