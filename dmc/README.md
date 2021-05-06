# Domain Model Controller

The Domain Model Controller (DMC), is an implementation of Airflow designed to support black box model execution, normalization, and storage.

Please see `Known Issues` before running.

## Setup

First you will need to determine your local machine IPv4

For OSX
```
ipconfig getifaddr en0
```
For Linux
```
hostname -i
```

Either `export` this to your environment or update `docker-compose.yaml` and change `DOCKER_URL` to
```
      DOCKER_URL: http://<local ip>:8375
```

You can validate docker api is working after `docker-compose` has started with
```
curl localhost:8375/containers/json
```

The DMC can be run via `docker-compose` with:

```
docker-compose up -d
```

You'll need to make the following permissions change:

```
sudo chmod -R +777 logs mappers results
```

to enable Airflow to control Docker containers.

If using Docker Desktop (e.g. on Mac) you may need to open the `Preferences` and **disable** `Use gRPC FUSE for file sharing`.

To change the authentification username and password adjust the following in the `docker-compose.yaml`:

```
_AIRFLOW_WWW_USER_USERNAME: jataware
_AIRFLOW_WWW_USER_PASSWORD: wileyhippo
```

> Note: these should be changed for production; the above credentials are the default.

You must also set environment variables for the AWS access and secret keys in order to be able to push results to S3:

```
export AWS_ACCESS_KEY=youraccesskey
export AWS_SECRET_KEY=yoursecretkey
```

> **Note**: you must **URL encode** your access and secret keys before setting the environment variables

Set the `DMC_DEBUG` environment variable in the `docker-compose.yaml` to `'false'` if you are running in production, otherwise leave it as `'true'`. If `'false'`, a notification is sent to Uncharted to let them know the model run as completed. We **don't** want to do this when developing the application.

This should run the Airflow UI at `http://localhost:8080/home`.

## Run Airflow DAG

- Launch Airflow:

  Go to: `http://34.204.189.38:8080/home`
  Contact a repo contributor for login credentials.

- After logging in, choose your desired DAG (currently `model_xform`)
- Trigger the DAG with the "play button"
- Copy in your configuration json (see below)
- Click `Trigger`
- Click `Graph View` to monitor progress. For each node you can view the logs by double-clicking the node and then choosing `logs`

### Example Model-to-S3 DAG

The config json below will trigger the `model_xform.py` DAG to:

1. Run the maxhop model

2. Via mixmasta, transform the maxhop geotiff output file to a geocoded .csv

3. Upload the csv file to S3:world-modelers-jataware/{run_id}/ bucket

To trigger the DAG, add the following configuration json:

```
{
   "run_id":"maxhop_test1",
   "model_image":"marshhawk4/maxhop",
   "model_command":"--country=Ethiopia --annualPrecipIncrease=.4 --meanTempIncrease=-.3 --format=GTiff",
   "model_output_directory":"/usr/local/src/myscripts/output",
   "xfrm_command":"-xform geotiff -input_file /tmp/maxent_Ethiopia_precipChange=0.4tempChange=-0.3.tif -geo admin2 -x longitude -y latitude -output_file /tmp/maxhop_transformed.csv -feature_name probability -band 1"
}
```

For the model run: the `model_output_directory` references the directory **within the Docker container**.
For mixmasta: the DAG looks for the file to be transferred in the mounted `/tmp` folder and will write the transformed csv to the mounted `/tmp` folder.

### Multiple S3 File upload.

See the DAG `mulitpleFiles.py` for an example of uploading several csv files to the S3 bucket.


### Airflow REST API

This is enabled on line 52 of `docker-compose.yaml`. The API reference can be found [here](http://apache-airflow-docs.s3-website.eu-central-1.amazonaws.com/docs/apache-airflow/latest/stable-rest-api-ref.html#operation/get_config). You can run commands like:


```
curl 'localhost:8080/api/v1/dags' \
-H 'Content-Type: application/json' \
--user "jataware:wileyhippo"
```


### Known Issues

There seems to be a problem with permissions on Mac with the `/var/run/docker.sock` file which prohibits Airflow from kicking off Docker runs. Therefore this should be run on Ubuntu only for the time being.
