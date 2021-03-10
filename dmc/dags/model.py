from datetime import timedelta
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from operators.dojo_operators import DojoDockerOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.utils.dates import days_ago
from airflow.configuration import conf
from airflow.models import Variable

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
    'model',
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

s3_node = PythonOperator(task_id='s3push-task', 
                             python_callable=s3copy,
                             dag=dag)

model_node = DojoDockerOperator(
    task_id='model-task',    
    image="{{ dag_run.conf['image'] }}",
    volumes=["//var/run/docker.sock://var/run/docker.sock", "/home/ubuntu/dojo/dmc/outputs:/outputs"],
    docker_url="unix:///var/run/docker.sock",
    network_mode="bridge",
    command=["{{ dag_run.conf['param1'] }}", "{{ dag_run.conf['param2'] }}", "{{ dag_run.conf['param3'] }}"],
    dag=dag
)

model_node >> s3_node