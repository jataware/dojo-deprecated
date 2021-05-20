#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import boto3
import requests
import glob
import os

'''
MUST EXPORT YOUR S3 CREDENTIALS IN THE ENV
export AWS_ACCESS_KEY=KEY_HERE
export AWS_SECRET_KEY=SECRET_HERE

'''

def to_s3(file, bucket_name, s3_key, s3_accessKey, s3_secretKey):
    #isCM flag to upload causemosified files...differnt file structure tan tar.gz

    session = boto3.Session(aws_access_key_id=s3_accessKey,aws_secret_access_key=s3_secretKey)
    s3 = session.resource("s3")
    s3_client = session.client("s3")
    bucket = s3.Bucket(bucket_name)

    s3_client.upload_file(file, 
                          bucket_name, 
                          s3_key,
                          ExtraArgs={'ACL':'public-read'})  
