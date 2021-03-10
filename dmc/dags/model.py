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

def s3copy(**kwargs):
    s3 = S3Hook(aws_conn_id="s3_connection")
    outputs = kwargs['dag_run'].conf.get('outputs')
    results_path = f"/results/{kwargs['dag_run'].conf.get('run_id')}"
    for f in outputs:
        s3.load_file(
            filename=f'{results_path}/{f}',
            key=f"{kwargs['dag_run'].conf.get('run_id')}/{f}",
            replace=True,
            bucket_name='jataware-world-modelers'
        )
    return

s3_node = PythonOperator(task_id='s3push-task', 
                             python_callable=s3copy,
                             provide_context=True,
                             dag=dag)

model_node = DojoDockerOperator(
    task_id='model-task',    
    image="{{ dag_run.conf['image'] }}",
    container_name="run_{{ dag_run.conf['run_id'] }}",
    volumes=["//var/run/docker.sock://var/run/docker.sock", "/home/ubuntu/dojo/dmc/results/{{ dag_run.conf['run_id'] }}:/outputs"],
    docker_url="unix:///var/run/docker.sock",
    network_mode="bridge",
    command=["{{ dag_run.conf['param1'] }}", "{{ dag_run.conf['param2'] }}", "{{ dag_run.conf['param3'] }}"],
    auto_remove=True,
    dag=dag
)

model_node >> s3_node