from requests import get
import os
import tarfile
import glob

isi_user = "datamart"
isi_pwd = "datamart-api-789"
datamart_api_url = f"https://{isi_user}:{isi_pwd}@dsbox02.isi.edu:8888/datamart-api-wm"

try:
    # DOWNLOAD
    bulk_url = f"{datamart_api_url}/datasets/bulk"

    print("Downloading Bulk Datasets from ISI Datamart")
    response = get(bulk_url, stream=True)
    with open("datamart_datasets_dump.tar.gz", "wb") as f:
        for chunk in response.raw.stream(1024, decode_content=False):
            if chunk:
                f.write(chunk)
    print("Download Complete")

    #  DECOMPRESS
    print("Decompressing Bulk Download")
    tar = tarfile.open(
        "/Users/travishartman/Desktop/Datamart_13May/bulk-data/datamart_datasets_dump.tar.gz"
    )
    tar.extractall()
    tar.close()
    print("Decompression Complete")

    ## DELETE EXTRA FILES
    print("Cleaning up the directory")
    for file in glob.glob("datamart-dump/*.*"):
        if file == "datamart-dump/FAOSTAT4.csv":
            os.remove("datamart-dump/FAOSTAT4.csv")  # empty file
        if file == "datamart-dump/unittestdatasetannotated.csv":
            os.remove("datamart-dump/unittestdatasetannotated.csv")  # junk
        if file == "datamart-dump/tutorial_dataset.csv":
            os.remove("datamart-dump/tutorial_dataset.csv")  # junk
        ender = file.split(".")[-1]
        if ender != "csv":
            os.remove(f"{file}")
    print(
        "Process complete: unzipped datamart dataset files are in the /datamart-dump folder"
    )

except Exception as e:
    print(e)
