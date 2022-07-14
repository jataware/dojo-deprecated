import logging

import pandas as pd
import xarray as xr
from raster2xyz.raster2xyz import Raster2xyz

from mixmasta import mixmasta as mix
from base_annotation import BaseProcessor
from utils import get_rawfile, put_rawfile


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
        fp = context["uploaded_file_fp"]
        ft = "geotiff"
        context["ft"] = ft

        def single_band_run():
            geotiff_meta = {
                x.replace("geotiff_", ""): context[x]
                for x in context
                if x.find("geotiff_") != -1
            }
            feature_name, band, date, nodataval = (
                geotiff_meta["Feature_Name"],
                geotiff_meta.get("band", 1),
                geotiff_meta["date"],
                geotiff_meta["Null_Val"],
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
                feature_name=context.get("Feature_name", "feature"),
                band_name=context.get("Feature_name", "feature"),
                date=context.get("date", "01/01/2001"),
                bands=context.get("bands", {}),
                band_type=context.get("band_type", "categorical"),
            )
            return df.sort_values(by="date")

        if context.get("bands", False):
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


def file_conversion(context):
    # Get raw file
    uuid = context["uuid"]
    filepath = context["datasets"]["data_paths"][0]
    filename = filepath.split("/")[-1]
    raw_file = get_rawfile(uuid, filename)
    excel_tuple = ("xlsx", "xls")
    tif_tuple = ("tif", "tiff")

    if filename.endswith(".csv"):

        # Using filename of None defaults to the csv file name in the envfile
        put_rawfile(uuid, None, raw_file)

        # Probably dont need return here.
        return raw_file

    elif filename.endswith(excel_tuple):
        sheet = context.get(
            "excel_Sheet", 0
        )  # 0 is the first sheet if none is provided.

        read_file = pd.read_excel(raw_file, sheet_name=sheet)

        read_file.to_csv("xlsx_to.csv", index=None, header=True)

        put_rawfile(uuid, None, read_file)
        # Probably dont need return here.
        return read_file

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


def geotif_to_CSV(context, fileobj):
    original_file = fileobj
    uuid = context["uuid"]

    with open("./tempGeoTif.tif", "wb") as f:
        f.write(original_file.read())

    glp = GeotiffLoadProcessor()
    context["uploaded_file_fp"] = "./tempGeoTif.tif"
    # TODO HARDCODED VALUES THAT NEED TO BE POPULATED FROM THE FIRST PAGE FROM REGISTER DATASET
    context["geotiff_Null_Val"] = 0
    context["geotiff_Feature_Name"] = "feature"
    context["geotiff_band"] = 1
    context["geotiff_date"] = "01/01/2001"

    df = glp.run(context)
    df.to_csv("./convertedCSV.csv", index=None, header=True)

    with open("./convertedCSV.csv", "rb") as f:
        put_rawfile(uuid, None, f)
