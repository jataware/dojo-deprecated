from datetime import timedelta
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.utils.dates import days_ago
from airflow.configuration import conf

############################
####### Generate DAG #######
############################

default_args = {
    'owner': 'Brandon',
    'depends_on_past': False,
    'start_date': days_ago(0),
    'catchup': False,
    'email': ['brandon@jataware.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'fsc',
    default_args=default_args,
    schedule_interval=None,
    max_active_runs=1,
    concurrency=10
)

###########################
###### Create Tasks #######
###########################


def s3copy():
    s3 = S3Hook(aws_conn_id="s3_connection")

    result_node = s3.load_file(
        filename='/outputs/Production_TimeSeries.csv',
        key='Production_TimeSeries.csv',
        replace=True,
        bucket_name='jataware-world-modelers'
    )
    return

result_node = PythonOperator(task_id='python_task', 
                             python_callable=s3copy,
                             dag=dag)

fsc_node = DockerOperator(
    image="jataware/fsc_model:0.1",
    volumes=["//var/run/docker.sock://var/run/docker.sock", "/home/ubuntu/dojo/dmc/outputs:/outputs"],
    docker_url="unix:///var/run/docker.sock",
    network_mode="bridge",
    # cmds=["python", "-c"],
    command=["0", "1", "0.5"],
    task_id='fsc-task',
    dag=dag
)

fsc_node.set_downstream(result_node)