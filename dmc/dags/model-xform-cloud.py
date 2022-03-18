import logging
import os
from datetime import timedelta
from logging import Logger

import requests
from airflow import DAG
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator

from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

# from airflow.providers.docker.operators.docker import DockerOperator
from operators.dojo_operators import DojoDockerOperator, HammerheadDockerOperator


logger: Logger = logging.getLogger(__name__)

# Get latest version of mixmasta
mixmasta_version = os.getenv("MIXMASTA_VERSION")
print(f"{mixmasta_version=}")

dag_tasks_version = os.getenv("DAG_TASKS_VERSION")
print(f"{dag_tasks_version=}")


vol_dir = os.getenv("VOLUMES_DIR")
print(f"{vol_dir=}")

# Get ENV variables for Causemos API
causemos_user = os.getenv("CAUSEMOS_USER")
causemos_pwd = os.getenv("CAUSEMOS_PWD")
causemos_base_url = os.getenv("CAUSEMOS_BASE_URL")
active_runs = int(os.getenv("DAG_MAX_ACTIVE_RUNS"))
concurrency = int(os.getenv("DAG_CONCURRENCY"))

############################
#    Generate DAG
############################

default_args = {
    "owner": "Jataware",
    "depends_on_past": False,
    "start_date": days_ago(0),
    "catchup": False,
    "email": ["brandon@jataware.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "cloud_model_xform",
    default_args=default_args,
    schedule_interval=None,
    max_active_runs=active_runs,
    concurrency=concurrency,
)


#########################
#     Functions
#########################


def seed_task(ti, **kwargs):
    ti.xcom_push(key="docker_engine", value={"IP": os.environ.get("IP_ADDRESS", "launch.wm.jata.lol")})
    is_cloud = kwargs["dag_run"].conf.get("cloud")
    print(f"{is_cloud=}")
    return "cloud-run-task" if is_cloud else "local-run-task"


def local_run_task(ti, **kwargs):
    ti.xcom_push(key="instance_info", value={"PUBLIC_IP": os.environ.get("IP_ADDRESS", "launch.wm.jata.lol")})
    print("Running on local instance")


def post_failed_to_dojo(**kwargs):
    dojo_url = kwargs["dag_run"].conf.get("dojo_url")
    run_id = kwargs["dag_run"].conf.get("run_id")
    # model_id = kwargs["dag_run"].conf.get("model_id")
    run = requests.get(f"{dojo_url}/runs/{run_id}").json()

    # TODO: this should be conditional; if the other tasks fail
    # this should reflect the failure; job should always finish
    if "attributes" not in run:
        run["attributes"] = {"status": "failed"}
    else:
        run["attributes"]["status"] = "failed"

    response = requests.put(f"{dojo_url}/runs", json=run)
    print(response.text)

    # Notify Uncharted
    if os.getenv("DMC_DEBUG") == "true":
        print("Debug mode: no need to notify Uncharted")
        return
    else:
        print("Notifying Uncharted...")
        response = requests.post(
            f"{causemos_base_url}/{run_id}/run-failed",
            headers={"Content-Type": "application/json"},
            json=run,
            auth=(causemos_user, causemos_pwd),
        )
        print(f"Response from Uncharted: {response.text}")
        return


###########################
#   Create Tasks
###########################

dmc_local_dir = os.environ.get("DMC_LOCAL_DIR")


transform_node = DojoDockerOperator(
    task_id="mixmasta-task",
    trigger_rule="all_success",
    image=f"jataware/mixmasta:{mixmasta_version}",
    container_name="run_{{ dag_run.conf['run_id'] }}",
    volumes=[dmc_local_dir + "/results/{{ dag_run.conf['run_id'] }}:/tmp", dmc_local_dir + "/mappers:/mappers"],
    docker_url="""{{ "http://" ~ ti.xcom_pull(key="instance_info", task_ids="hammerhead-task").PUBLIC_IP ~ ":8375" }}""",
    network_mode="bridge",
    command="{{ dag_run.conf['mixmasta_cmd'] }}",
    auto_remove=True,
    dag=dag,
)

notify_failed_node = PythonOperator(
    task_id="failed-task",
    python_callable=post_failed_to_dojo,
    trigger_rule="one_failed",
    provide_context=True,
    dag=dag,
)


seed_node = BranchPythonOperator(task_id="seed-task", python_callable=seed_task, provide_context=True, dag=dag)


cloud_run_node = HammerheadDockerOperator(
    task_id="cloud-run-task",
    docker_url="""{{ "http://" ~ ti.xcom_pull(key="docker_engine").IP ~ ":8375" }}""",
    force_pull=True,
    dag=dag,
)


local_run_node = PythonOperator(
    task_id="local-run-task", python_callable=local_run_task, provide_context=True, dag=dag
)


rehydrate_node = DojoDockerOperator(
    do_login=True,
    task_id="rehydrate-task",
    trigger_rule=TriggerRule.ONE_SUCCESS,
    image=f"jataware/dag-tasks:{dag_tasks_version}",
    volumes=[
        "/tmp:/tmp",
        f"{vol_dir}/model_configs:/model_configs",
    ],
    docker_url="""{{"http://" ~ ti.xcom_pull(key="instance_info").PUBLIC_IP ~ ":8375" }}""",
    command="""rehydrate.py {{ dag_run.conf | tojson | tojson }}""",
    auto_remove=True,
    xcom_all=False,
    dag=dag,
)


model_node = DojoDockerOperator(
    task_id="model-task",
    trigger_rule="all_success",
    image="{{ dag_run.conf['model_image'] }}",
    container_name="run_{{ dag_run.conf['run_id'] }}",
    volumes="{{ dag_run.conf['volumes'] }}",
    docker_url="""{{ "http://" ~ ti.xcom_pull(key="instance_info").PUBLIC_IP ~ ":8375" }}""",
    network_mode="bridge",
    command="{{ dag_run.conf['model_command'] }}",
    auto_remove=True,
    xcom_all=False,
    dag=dag,
)


def debug_task(**kwargs):
    print(f"dag {kwargs['dag_run'].conf}")


debug_node = PythonOperator(
    task_id="debug-task", trigger_rule="all_success", python_callable=debug_task, provide_context=True, dag=dag
)


seed_node >> [cloud_run_node, local_run_node] >> rehydrate_node >> debug_node >> model_node
# >> mapper_node >> transform_node >> acccessory_node >> s3_node
# s3_node >> notify_failed_node
# s3_node >> exit_node
