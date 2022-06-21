

## Jataware Dag Tasks Container


The `dag-tasks` container is a set of scripts that were converted from Airflows `PythonOperators`.
The purpose of these scripts is to run some task over a shared volume from a previous _task_.


An example usage would be to upload files to s3 you would use the `s3_copy.py` with the appropriate parameters
required for that script.


An example usage would be locally would be

```
docker run --rm -v ${PwD}/results:/results jataware/dag-tasks:dev s3_copy.py
```


And an example usage in Airflow looks like this

```
s3_node = DojoDockerOperator(
    task_id="s3-task",
    image=f"jataware/dag-tasks:{dag_tasks_version}",
    volumes=[dmc_local_dir + "/results/{{ dag_run.conf['run_id'] }}:/results"],
    docker_url="""{{ "http://" ~ ti.xcom_pull(key="instance_info").PUBLIC_IP ~ ":8375" }}""",
    network_mode="bridge",
    environment={{
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),

        "AWS_DEFAULT_REGION": "us-east-1",
    },
    command=(
        "s3_copy.py " "{{ dag_run.conf['model_id']}} {{ dag_run.conf['run_id']}} " f"{s3_bucket} {s3_bucket_dir}"
    ),
    auto_remove=True,
    xcom_all=False,
    dag=dag,
)
```



### Build

```
make docker_build
```

This will build the docker container locally


### Publish

```
make docker_push
```

This will push the current version to docker-hub

