import argparse
import glob
import json
import os
from datetime import datetime

import requests


def run_exit(model_id, run_id, dojo_url, causemos_base_url, bucket_dir):
    run = requests.get(f"{dojo_url}/runs/{run_id}").json()
    # TODO: this should be conditional; if the other tasks fail
    # this should reflect the failure; job should always finish
    if "attributes" not in run:
        run["attributes"] = {"status": "success"}
    else:
        run["attributes"]["status"] = "success"

    # get pth array
    print("Processing results:")
    pth = []
    for fpath in glob.glob(f"/results/{run_id}/*.parquet.gzip"):
        print(f"fpath:{fpath}")
        fn = fpath.split("/")[-1]
        print(f"fn:{fn}")
        pth.append(f"https://jataware-world-modelers.s3.amazonaws.com/{bucket_dir}/{run_id}/{fn}")

    print("pth array", pth)
    run["data_paths"] = pth

    print("Processing accessories:")
    # Prepare accessory lookup
    req = requests.get(f"{dojo_url}/dojo/accessories/{model_id}")
    accessories = json.loads(req.content)
    caption_lookup = {}
    for accessory in accessories:
        caption_lookup[accessory["id"]] = accessory.get("caption", "")

    print(f"Accessories: {accessories}")
    print(f"Caption Lookup: {caption_lookup}")
    accessories_paths = set([i.get("path").split("/")[-1] for i in accessories])

    # Get any accessories and append their S3 URLS to run['pre_gen_output_paths']
    accessories_array = []
    for fpath in glob.glob(f"/results/{run_id}/accessories/*"):
        accessory_dict = {}
        print(f"fpath:{fpath}")
        fn = fpath.split("/")[-1]
        print(f"fn:{fn}")
        if "__dojo__" in fn:
            if fn.split("__dojo__")[1] in accessories_paths:
                print("Found accessory, processing...")
                accessory_id = fn.split("__dojo__")[0]
                fn_aws_key = fn.split("__dojo__")[1]
                accessory_dict[
                    "file"
                ] = f"https://jataware-world-modelers.s3.amazonaws.com/{bucket_dir}/{run_id}/{fn_aws_key}"
                accessory_dict["caption"] = caption_lookup[accessory_id]
                accessories_array.append(accessory_dict)
        else:
            print("Not tagged as accessory, skipping.")

    print("accessories_array", accessories_array)

    run["pre_gen_output_paths"] = accessories_array

    # Update attributes.executed_at.
    run["attributes"]["executed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create the response, which is the response from the dojo api/runs PUT.
    response = requests.put(f"{dojo_url}/runs", json=run)
    print(response.text)

    # Notify Uncharted
    if os.getenv("DMC_DEBUG") == "true":
        print(f"{run=}")
        print("testing Debug mode: no need to notify Uncharted")
    else:
        print("Notifying Uncharted...")
        causemos_user = os.getenv("CAUSEMOS_USER")
        causemos_pwd = os.getenv("CAUSEMOS_PWD")
        response = requests.post(
            f"{causemos_base_url}/{run_id}/post-process",
            headers={"Content-Type": "application/json"},
            json=run,
            auth=(causemos_user, causemos_pwd),
        )
        print(f"Response from Uncharted: {response.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="run_exit")
    parser.add_argument("model_id", help="model_id")
    parser.add_argument("run_id", help="run_id")
    parser.add_argument("dojo_url", help="dojo_url")
    parser.add_argument("causemos_base_url", help="causemos_base_url")
    parser.add_argument("s3_bucket_dir", help="s3 bucket dir")
    args = parser.parse_args()
    run_exit(args.model_id, args.run_id, args.dojo_url, args.causemos_base_url, args.s3_bucket_dir)
