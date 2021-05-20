import pandas as pd
import numpy as np
from datetime import datetime
import glob
import json
from requests import get
import os
import time
import random


### FUNCTIONS ###
# Get feature data type
def get_type(df_data, variable_id):
    istype = str(df_data.loc[df_data["variable_id"] == variable_id, "value"].dtype)
    if "float" in istype:
        TYPE = "float"
    if "int" in istype:
        TYPE = "int"
    if "str" in istype:
        TYPE = "str"
    return TYPE


# Get list of all admins in the admin-level
def get_admins(admin, df):
    raw_adm_list = list(df[admin].unique())

    adm_list = []
    for x in raw_adm_list:
        if type(x) == str:
            adm_list.append(x)

    if len(adm_list) == 0:
        return []
    else:
        return adm_list


def get_temporal_res(df_data):
    res = df_data.get("time_precision", " ")[0]

    if type(res) == str:
        return res
    else:
        return "not provided"


#Main Function
def to_json(filename,isi_user, isi_pwd, i, end):
    # Get metadata for ALL datasets in the DM
    datamart_api_url = (f"https://{isi_user}:{isi_pwd}@dsbox02.isi.edu:8888/datamart-api-wm")
    response = get(f"{datamart_api_url}/metadata/datasets")
    df_dataset_meta = pd.DataFrame(response.json())
    dataset_meta = df_dataset_meta.set_index("dataset_id").T.to_dict()

    del dataset_meta["ACLED2"]  # not in bulk download
    del dataset_meta["FAOSTAT4"]  # empty dataset

    #### Build dataset.json ####

    """
    Need three data sources to best fill out the indicator json
    1. Dataset metadata :: dataset_meta dictionary from "metadata/datasets" endpoint (built outside loop)
    2. Dataset df :: df_data (dataframe_datamart) read from bulk downloaded file
    3. Variable metadata :: var_meta from "metadata/datasets/{dataset_id}/variables" endpoint
    """

    # Progress Report and Delay for API hits
    print(f"{100*round(float(i/end),2)}%  filename: {filename}")
    i += 1
    time.sleep(random.uniform(0, 1))

    # Read in dataset as dataframe
    dataset_id = filename.split("/")[1].split(".")[0]
    df_data = pd.read_csv(filename)

    # Get Variable metadata
    response = get(f"{datamart_api_url}/metadata/datasets/{dataset_id}/variables")
    df_var_meta = pd.DataFrame(response.json())
    variable_ids = list(df_var_meta.variable_id)  # list of all vars in dataset to loop thru
    print(variable_ids[0])
    var_meta = df_var_meta.set_index("variable_id").T.to_dict()

    TEMPORAL_RES = get_temporal_res(df_data)

    # For each variable in the dataset, get the variable's metadata and dump list to header dict
    OUTPUTS = []
    for variable_id in variable_ids:
        
        VARIABLE_ID = variable_id
        NAME = var_meta[variable_id]["name"]
        DESCRIPTION = var_meta[variable_id]["description"]
        TYPE = get_type(df_data, variable_id)

        try:
            UNITS = f"{df_data.loc[df_data['variable_id']==variable_id, 'value_unit'].iloc[0]}"
        except Exception as e:
            UNITS = "not provided"

        TAGS = []
        for qual in var_meta[variable_id]["qualifier"]:
            TAGS.append(qual["name"])

        temp_outputs = {
            "id": VARIABLE_ID,
            "name": NAME,
            "display_name": NAME,
            "description": DESCRIPTION,
            "type": TYPE,
            "units": UNITS,
            "units_description": "not provided",
            "concepts": [{"name": "TBD", "score": 0}],
            "additional_options": {},
            "tags": TAGS,
            "data_resolution": {
                "temporal_resolution": TEMPORAL_RES,
                "spatial_resolution": [0, 0]
            }
        }

        OUTPUTS.append(temp_outputs)

    # FROM dataset_meta
    ID = dataset_id
    NAME = dataset_meta[dataset_id]["name"]
    DESCRIPTION = dataset_meta[dataset_id]["description"]
    DATA_PATHS = f"https://jataware-world-modelers.s3.amazonaws.com/indicators/causemosified/{ID}.parquet.gzip/"
    CREATED = dataset_meta[dataset_id]["last_update"]
    URL = dataset_meta[dataset_id]["url"]

    # DEFAULTS FOR OPTIONAL METADATA
    MAINTAINER_NAME = "not provided"
    EMAIL = "not provided"
    ORG = "not provided"
    CATEGORY = []

    # Most datasets do not have this info, below captures the few that do
    df_cols = list(df_data.columns)
    if "Contact" in df_cols:
        MAINTAINER_NAME = df_data["Contact"].iloc[0]
    if "Email" in df_cols:
        EMAIL = df_data["Email"].iloc[0]
    if "Topic" in df_cols:
        CATEGORY = [df_data["Topic"].iloc[0]]

    COUNTRIES = get_admins("country", df_data)
    ADMIN1 = get_admins("admin1", df_data)
    ADMIN2 = get_admins("admin2", df_data)
    ADMIN3 = get_admins("admin3", df_data)

    # Main Dictionary to be written to with all variables set above
    main_dict = {
        "id": ID,
        "name": NAME,
        "description": DESCRIPTION,
        "data_paths": [DATA_PATHS],
        "created": CREATED,
        "version": "",
        "category": CATEGORY,
        "maintainer": {
            "name": MAINTAINER_NAME,
            "email": EMAIL,
            "organization": ORG,
            "website": URL,
        },
        "outputs": OUTPUTS,
        "tags": [],
        "geography": {
            "country": COUNTRIES,
            "admin1": ADMIN1,
            "admin2": ADMIN2,
            "admin3": ADMIN3,
        }
    }

    with open(f"jsons/{ID}.json", "w") as fp:
        json.dump(main_dict, fp, ensure_ascii=True, indent=1)


# Verify all json files written
dump = []
jsawn = []
for filename in sorted(glob.glob("datamart-dump/*.csv")):
    dump.append(filename.split("/")[1].split(".")[0])
for filename in sorted(glob.glob("jsons/*.json")):
    jsawn.append(filename.split("/")[1].split(".")[0])
one_not_two = set(dump) - set(jsawn)

if len(one_not_two) != 0:
    print(f"{one_not_two} json files not written")
else:
    print("COMPLETE: all json files written to /jsons")
