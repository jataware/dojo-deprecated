
## Quickstart

Run
```
python3 main.py -bulk_down=True -bulk_up=False -convert_cm=True -cm_s3=True -jsoniy=True
```

Flags are more for testing. The Bulk Upload to S3 was taking a long time.

-bulk_down: Pull datasets from ISI
-bulk_up: Upload tar.gz of all ISI data to S3
-convert_cm: Convert ISI datasets to causemos compliant and convert to gripped parquet
-cm_s3: Upload gzipped causemosifed datasets to S3
-jsonify: Build indicator json files for DOJO
