import pandas as pd
import boto3
import requests
import glob
import os
import argparse

import bulk_download as bd, to_causemos as cm, to_json as tj, to_s3 as aws


'''

python3 main.py -bulk_down=False -bulk_up=False -convert_cm=True -cm_s3=True -jsonify=True

MUST SET ENV VARIABLES

AWS:
export AWS_ACCESS_KEY=KEY_HERE
export AWS_SECRET_KEY=SECRET_HERE

ISI API:
export ISI_USER=user
export ISI_PWD=pwd

'''

# SET VARS
parser = argparse.ArgumentParser(description='Parse News for a given query')
parser.add_argument('-bulk_down', dest ='bulk_down', type=sorted, help='True=bulk download ISI DM datasets')
parser.add_argument('-bulk_up', dest ='bulk_up', type=str, help='True=bulk upload tar.gz to S3')
parser.add_argument('-convert_cm', dest ='convert_cm', type=str, help='True=bconvert to cmify')
parser.add_argument('-cm_s3', dest ='cm_s3', type=str, help='True=upload all cmified files to S3')
parser.add_argument('-jsonify', dest ='jsonify', type=str, help='True=build DOJO json of indicators')
args = parser.parse_args()

bulk_down = args.bulk_down
bulk_up = args.bulk_up
cm_s3 = args.cm_s3
convert_cm = args.convert_cm
jsonify = args.jsonify

s3_accessKey = os.getenv('AWS_ACCESS_KEY')
s3_secretKey = os.getenv('AWS_SECRET_KEY')
bucket_name = "jataware-world-modelers"
isi_user = os.getenv('ISI_USER')
isi_pwd = os.getenv('ISI_PWD')

if __name__ == "__main__":

    ### Bulk Download 
    if bulk_down == "True":
        bd.bulk_download(isi_user, isi_pwd)


    ### Write Bulk tar.gz to S3
    if bulk_up == "True":
        file = "datamart_datasets_dump.tar.gz"
        s3_key = f"indicators/datamart/{file}"
        aws.to_s3(file, bucket_name, s3_key, s3_accessKey, s3_secretKey)
    

    ### Transform datasets into causempsified gzipped parquet files
    if convert_cm == "True":
        for file in sorted(glob.glob("datamart-dump/*.csv")):
            try:
                #Datamart df to cm
                df_DM = pd.read_csv(file)

                # Convert to Friend of Causemos
                df_DM = pd.read_csv(file)
                df = cm.causemosify(df_DM)

                # Convert to gzip parquet file
                print(f"Causemosifing and gzipping {file} into parquet")
                fn_gz = file.split("/")[1].split(".")[0]
                gz_path = f'causemosified/{fn_gz}.parquet.gzip'
                df.to_parquet(gz_path, compression="gzip")

            except Exception as e:
                print(e)


    ### Upload causemosified tar.gz files to S3
    if cm_s3 == "True":
        for file in sorted(glob.glob('causemosified/*.*')):
            fn = file.split(".")[0]
            gz_file = f'{fn}.parquet.gzip'
            s3_key = f"indicators/{gz_file}"
            print(s3_key)
            aws.to_s3(gz_file, bucket_name, s3_key, s3_accessKey, s3_secretKey)


    if jsonify == "True":
        i = 0
        end = 60 #I'll update this hard code
        for filename in sorted(glob.glob("datamart-dump/*.csv")):
            tj.to_json(filename,isi_user, isi_pwd, i, end)


