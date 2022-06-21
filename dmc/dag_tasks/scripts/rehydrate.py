import argparse
import json
import os

import requests
from jinja2 import Template


def rehydrate(**kwargs):

    print(f"kwargs: {kwargs}")

    # get default dict
    defaultDict = {}
    dojo_url = kwargs.get("dojo_url")
    model_id = kwargs.get("model_id")
    run_id = kwargs.get("run_id")
    saveFolder = f"/model_configs/{run_id}/"
    # kwargs["dag_run"].conf.get("model_output_directory")

    # get the model
    resp = requests.get(f"{dojo_url}/models/{model_id}")
    resp.raise_for_status()

    respData = json.loads(resp.content)
    params = respData["parameters"]
    print(f"params: {params}")

    # build "type" dict:
    type_dict = {}
    for param in params:
        type_dict[param["name"]] = param["type"]

    print(f"type_dict: {type_dict}")

    try:

        for configFile in kwargs.get("s3_config_files"):

            fileName = configFile.get("fileName")
            model_config_s3 = configFile.get("s3_url")
            configFile.get("path")

            respTemplate = requests.get(model_config_s3)
            dehydrated_config = respTemplate.content.decode("utf-8")
            for p in params:
                defaultDict[p["name"]] = p["default"]

            # parameters the user sent in
            hydrateData = kwargs.get("params")

            # need to loop over defaultDict and update with hydrateData values
            for key in hydrateData:
                if key in defaultDict.keys():
                    defaultDict[key] = hydrateData[key]

            for key in defaultDict:
                print(f"DEFAULT: key: {key} value: {defaultDict[key]} type: {type(defaultDict[key])}")
            for key in hydrateData:
                print(f"hydrateData: key: {key} value: {hydrateData[key]} type: {type(hydrateData[key])}")

            # Hydrate the config
            if os.path.exists(saveFolder):
                print("here")

            else:
                os.mkdir(saveFolder, mode=0o777)

            os.chmod(saveFolder, mode=0o777)

            # Template(dehydrated_config).stream(finalDict).dump(savePath)
            dataToSave = Template(dehydrated_config).render(defaultDict)

            print(f"dataToSave: {dataToSave}")
            # savePath needs to be hard coded for ubuntu path with run id and model name or something.
            saveFileName = saveFolder + fileName
            with open(saveFileName, "w+") as fh:
                fh.write(dataToSave)
            os.chmod(saveFileName, mode=0o777)

    except Exception as e:
        print(e)
        raise
    print("done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="rehydrate")
    parser.add_argument("kwargs", help="json string of arguments")
    args = parser.parse_args()
    rehydrate(**json.loads(args.kwargs))
