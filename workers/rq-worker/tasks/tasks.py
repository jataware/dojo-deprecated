import base64
import copy
import hashlib
import json
import logging
from operator import sub
import os
import time
from urllib.parse import urlparse
import uuid

from rename import rename as rename_function
from anomaly_detection import AnomalyDetector, sheet_tensor_to_img
from utils import get_rawfile, put_rawfile
import pandas as pd
import mixmasta as mx
import rasterio
import requests

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

# Anomaly detector instantiation; load_autoencoder() is comparatively resource intensive.
detector = AnomalyDetector()
detector.load_autoencoder()


def dupe(annotations, rename_list, new_names):
    """annotations is a list of dictionaries, if entry["name"] is in rename_list copy over an entry for every name in new_names and rename the entry["name"] to the new name"""
    added = []
    new_list = []
    rename_count = 0
    for entry in annotations:
        # if entry["name"] in primary_geo_renames: # RTK
        if entry["name"] in rename_list:
            # if not primary_geo_renamed: # RTK
            if rename_count < len(rename_list):
                rename_count += 1
                for new_name in new_names:
                    # Don't add again, although duplicates are removed below.
                    if new_name in added:
                        continue
                    e = entry.copy()
                    e["name"] = new_name
                    e["display_name"] = new_name
                    e["type"] = new_name
                    new_list.append(e)
                    added.append(e["name"])
        else:
            if entry["name"] not in added:
                new_list.append(entry)
                added.append(entry["name"])
    return new_list


def build_mapper(uuid, annotations):
    """
    Description
    -----------
    Performs two functions:
    (1) Build and return the mixmasta mapper.json from annotations.json.
    (2) Return geo_select if "Geo_Select_Form" is annotated.

    Returns
    -------
        ret: dictionary
            geo, date, and feature keys for mixmasta process.
        geo_select: string, default None
            admin_level if set during annotation: country, admin1, admin2, admin3

    """

    import pprint
    logging.warn("+++" * 30)
    logging.warn(pprint.pformat(annotations))
    logging.warn("+++" * 30)

    # Set default return value (None) for geo_select.
    geo_select = None

    # fp = f"data/{uuid}/annotations.json"
    # with open(fp, "r") as f:
    #     annotations = json.load(f)
    conversion_names = {
        "name": "display_name",
        "geo": "geo_type",
        "time": "date_type",
        "format": "time_format",
        "data_type": "feature_type",
        "unit_description": "units_description",
        "coord_pair_form": "is_geo_pair",
        "qualifycolumn": "qualifies",
        "string": "str",
    }
    ret = {"geo": [], "date": [], "feature": []}

    for orig_name in annotations:
        entry = {}
        entry["name"] = orig_name
        sub_ann = annotations[orig_name]
        try:
            sub_ann = sub_ann[0]
        except:
            continue
        for x in sub_ann.keys():
            if x in ["redir_col"]:
                continue

            # Set geo_select if annotated.
            if str(x).lower() == "geo_select_form":
                geo_select = sub_ann[x]
                # Mixmasta expects "admin0" not "country".
                if geo_select.lower() == "country":
                    geo_select = "admin0"

            if x.lower() in conversion_names.keys():
                new_col_name = conversion_names[x.lower()]
            else:
                new_col_name = x.lower()

            if new_col_name != "display_name":
                if new_col_name == "qualifies":
                    if type(sub_ann[x]) == str:
                        sub_ann[x] = [sub_ann[x]]
                if type(sub_ann[x]) == str and new_col_name not in [
                    "is_geo_pair",
                    "qualifies",
                    "dateformat",
                    "time_format",
                    "description",
                ]:
                    entry[new_col_name] = sub_ann[x].lower()
                else:
                    entry[new_col_name] = sub_ann[x]
            else:
                entry[new_col_name] = sub_ann[x]

        for x in ["dateassociate", "isgeopair", "qualify"]:
            if x in entry.keys():
                del entry[x]

        ret[entry["type"]].append(entry)

    for x in range(len(ret["date"])):
        if "dateformat" in ret["date"][x]:
            ret["date"][x]["time_format"] = ret["date"][x]["dateformat"]
            del ret["date"][x]["dateformat"]

        if ret["date"][x].get("primary_time", False):
            ret["date"][x]["primary_date"] = True
            del ret["date"][x]["primary_time"]

    return ret, geo_select


def valid_qualifier_target(entry):
    k = entry.keys()
    for x in ["qualify", "primary_geo", "primary_time"]:
        if x in k:
            if entry[x] == True:
                return False
    return True


def is_qualifier(entry):
    for x in ["qualify", "qualifies", "qualifyColumn"]:
        if x in entry.keys():
            return True
    return False


def clear_invalid_qualifiers(uuid, annotations):
    # fp = f"data/{uuid}/annotations.json"
    # with open(fp, "r") as f:
    #     annotations = json.load(f)
    to_del = {}
    for x in annotations.keys():
        sub_ann = annotations[x]
        try:
            logging.info(
                f"Annotation: {annotations} | Annotation Keys: {annotations.keys()} | X: {x} | Annotation x: {sub_ann} | Typeof: {type(sub_ann)} | SUBANN: {sub_ann[0]}"
            )
            sub_ann = sub_ann[0]
            if "qualify" in sub_ann:
                if sub_ann["qualify"] == True:
                    to_del[x] = []
                    if type(sub_ann["qualifyColumn"]) == str:
                        sub_ann["qualifyColumn"] = [sub_ann["qualifyColumn"]]

                    for y in sub_ann["qualifyColumn"]:
                        if y in annotations.keys():
                            if not valid_qualifier_target(annotations[y]):
                                to_del[x].append(y)
                        else:
                            to_del[x].append(y)
        except Exception as e:
            logging.warning(f"Annotation field couldn't be processed: {x}")
    to_drop = []
    for x in to_del.keys():
        for y in to_del[x]:
            annotations[x][0]["qualifyColumn"].remove(y)
        if annotations[x][0]["qualifyColumn"] == []:
            to_drop.append(x)
    for x in to_drop:
        if x in annotations.keys():
            del annotations[x]

    # with open(fp, "w") as f:
    #     json.dump(annotations, f)
    return annotations

def build_mixmasta_meta_from_context(context, filename=None):
    import pprint
    logging.warn(pprint.pformat(context))
    metadata = context["annotations"]["metadata"]
    mapping  = {
        'band': 'geotiff_band_count',
        'band_name': 'geotiff_value',
        'bands': 'geotiff_bands',
        'band_type': 'geotiff_band_type',
        'date': 'geotiff_date',
        'feature_name': 'geotiff_band',
        'null_val': 'geotiff_null_value',
        'sheet': 'excel_sheet_name',
    }
    mixmasta_meta = {
        "ftype": metadata.get("ftype", "csv"),
    }
    for key, value in mapping.items():
        if value in metadata:
            mixmasta_meta[key] = metadata[value]
    logging.warn(context)
    return mixmasta_meta

def build_meta(uuid, d, geo_select, context):
    logging.warn('------------------------')
    logging.warn(uuid)
    logging.warn(d)
    logging.warn(geo_select)
    logging.warn(context)
    annotations = context["annotations"]["annotations"]

    ft = annotations["meta"].get("ftype", "csv")
    fp = context.get("uploaded_file_fp", f"/datasets/{uuid}/raw_data.csv")
    meta = {}
    meta["ftype"] = ft

    if ft == "geotiff":
        with open(f"data/{uuid}/geotiff_info.json", "r") as f:
            tif = json.load(f)
        {
            "geotiff_Feature_Name": "feat",
            "geotiff_Band": "1",
            "geotiff_Null_Val": "-9999",
            "geotiff_Date": "",
        }
        if "bands" in context:
            meta["ftype"] = context.get("ft", "csv")
            meta["bands"] = context.get("bands", "1")
            meta["null_val"] = context.get("null_val", "-9999")
            meta["date"] = context.get("date", "")
            meta["date"] = context.get("date", "01/01/2001")
            meta["feature_name"] = context.get(
                "Feature_name", tif.get("geotiff_Feature_Name", "feature")
            )
            meta["band_name"] = context.get(
                "Feature_name", tif.get("geotiff_Feature_Name", "feature")
            )
            meta["band"] = 0
            meta["null_val"] = -9999
            meta["bands"] = context.get("bands", {})
            meta["band_type"] = context.get("band_type", "category")

        else:
            meta["feature_name"] = tif["geotiff_Feature_Name"]
            meta["band_name"] = tif["geotiff_Feature_Name"]
            meta["null_val"] = tif["geotiff_Null_Val"]
            meta["date"] = tif["geotiff_Date"]

    if ft == "excel":
        xl = json.load(open(f"/datasets/{uuid}/excel_info.json", "r"))
        meta["sheet"] = xl["excel_Sheet"]

    # Update meta with geocode_level if set as geo_select above.
    # If present Mimaxta will override admin param with this value.
    # Meant for use with DMC model runs.
    if geo_select != None:
        meta["geocode_level"] = geo_select
    return meta, fp.split("/")[-1], fp


def generate_mixmasta_files(context, filename=None):
    uuid = context["uuid"]
    annotations = context["annotations"]["annotations"]
    annotations = clear_invalid_qualifiers(uuid, annotations)

    # Build the mapper.json annotations, and get geo_select for geo_coding
    # admin level if set annotating lat/lng pairs.
    mixmasta_ready_annotations, geo_select = build_mapper(uuid, annotations)

    logging_preface = "Mixmasta  log start: "
    d = f"/datasets/{uuid}"
    fp = ""
    meta = {}
    fn = None

    mixmasta_ready_annotations["meta"] = build_mixmasta_meta_from_context(context, filename=filename)
    # mixmasta_ready_annotations["meta"], fn, fp = build_meta(
    #     uuid, d, geo_select, context
    # )

    logging.info(f"{logging_preface} - Began mixmasta process")

    # BYOM handling
    if context.get("mode") == "byom":
        # Default to admin2 if geo_select is not set or too precise.
        if geo_select in (None, "admin3"):
            admin_level = "admin2"
        else:
            admin_level = geo_select
            logging.info(f"{logging_preface} - set admin_level to {admin_level}")

        byom_annotations = copy.deepcopy(mixmasta_ready_annotations)
        fn = f"{d}/raw_data.csv"
        fp = fn
        byom_annotations["meta"] = {"ftype": "csv"}

        with open(f"data/{uuid}/byom_annotations.json", "w") as f:
            json.dump(
                byom_annotations,
                f,
            )
        mapper = "byom_annotations"

    # BYOD handling
    else:
        # Default to admin3 if geo_select is not set.
        if geo_select == None:
            admin_level = "admin3"
        else:
            admin_level = geo_select
            logging.info(f"{logging_preface} - set admin_level to {admin_level}")

        mapper = "mixmasta_ready_annotations"

    # Set gadm level based on geocoding level; still using gadm2 for gadm0/1.
    gadm_level = None

    context["gadm_level"] = gadm_level
    context["output_directory"] = d
    context["mapper_fp"] = f"data/{uuid}/{mapper}.json"
    context["raw_data_fp"] = fp
    context["admin_level"] = admin_level

    return mixmasta_ready_annotations


def post_mixmasta_annotation_processing(rename, context):
    """change annotations to reflect mixmasta's output"""
    uuid = context["uuid"]
    # with open(context["mapper_fp"], "r") as f:
    #     mixmasta_ready_annotations = json.load(f)
    mixmasta_ready_annotations = context["annotations"]["annotations"]
    to_rename = {}
    for k, x in rename.items():
        for y in x:
            to_rename[y] = k

    mixmasta_ready_annotations = rename_function(mixmasta_ready_annotations, to_rename)

    primary_date_renames = [
        x["name"]
        for x in mixmasta_ready_annotations["date"]
        if x.get("primary_geo", False)
    ]
    primary_geo_renames = [
        x["name"]
        for x in mixmasta_ready_annotations["geo"]
        if x.get("primary_geo", False)
    ]

    primary_geo_rename_count = 0  # RTK
    mixmasta_ready_annotations["geo"] = dupe(
        mixmasta_ready_annotations["geo"],
        primary_geo_renames,
        ["admin1", "admin2", "admin3", "country", "lat", "lng"],
    )
    mixmasta_ready_annotations["date"] = dupe(
        mixmasta_ready_annotations["date"], primary_date_renames, ["timestamp"]
    )

    json.dump(
        mixmasta_ready_annotations,
        open(f"/datasets/{uuid}/mixmasta_ready_annotations.json", "w"),
    )


def anomaly_detection(context):
    from matplotlib import pyplot as plt
    from io import BytesIO

    uuid = context["uuid"]
    file_stream = get_rawfile(uuid, "raw_data.csv")

    if not os.path.exists(f"./data/{uuid}"):
        os.makedirs(f"./data/{uuid}")

    with open(f"./data/{uuid}/ad_file.csv", "wb") as f:
        f.write(file_stream.read())

    tensor = detector.csv_to_img(f"./data/{uuid}/ad_file.csv")

    result = detector.classify(
        tensor, low_threshold=0.33, high_threshold=0.66, entropy_threshold=0.15
    )
    img = sheet_tensor_to_img(tensor)
    buffer = BytesIO()
    plt.imshow(img)
    plt.savefig(buffer, format="png")
    buffer.seek(0)

    return {
        "anomalyConfidence": result,
        "img": base64.encodebytes(buffer.read()),
    }


def test_job(context, fail=False, sleep=10, *args, **kwargs):
    logging.info(f"test_job preparing to sleep for {sleep} seconds")
    # Test RQ job
    time.sleep(sleep)
    logging.info("test_job sleep completed")
    if fail:
        logging.info("Flag set to force fail, raising exception")
        raise RuntimeError("Forced failure of test job")

    logging.info("test_job task completed successfully")


def model_output_analysis(context, model_id, fileurl, filepath):

    file_key = f"{model_id}:{filepath}"
    file_uuid = str(uuid.UUID(bytes=hashlib.md5(file_key.encode()).digest(), version=4))
    url = f"{os.environ['CLOUSEAU_ENDPOINT']}{fileurl}"
    req = requests.get(url, stream=True)
    stream = req.raw
    if filepath.endswith('.xlsx') or filepath.endswith('.xls'):
        excel_file = pd.ExcelFile(stream.read())
        return {
            'file_uuid': file_uuid,
            'filetype': 'excel', 
            'excel_sheets': excel_file.sheet_names, 
            'excel_sheet': excel_file.sheet_names[0]
        }
    elif filepath.endswith('.tiff') or filepath.endswith('.tif'):
        raster = rasterio.open(rasterio.io.MemoryFile(stream))
        return {
            'file_uuid': file_uuid,
            'filetype': 'geotiff', 
            'geotiff_band_count': raster.profile['count'], 
            'geotiff_band_type': "category", 
            'geotiff_bands': {}
        }
    else: 
        return {
            'file_uuid': file_uuid
        }


