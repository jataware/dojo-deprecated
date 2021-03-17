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


'''

scp -v /Users/travishartman/ssh/id_rsa /Users/travishartman/Desktop/dags/* ubuntu@34.204.189.38:/home/ubuntu/dojo/dmc/dags/

'''

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
    'maxhop',
    default_args=default_args,
    schedule_interval=None,
    max_active_runs=1,
    concurrency=10
)


#########################
###### Functions ########
#########################

def s3copy(**kwargs):
    s3 = S3Hook(aws_conn_id="s3_connection")
    outputs = kwargs['dag_run'].conf.get('x_outputs')
    results_path = f"/results/{kwargs['dag_run'].conf.get('run_id')}"
    for f in outputs:
        s3.load_file(
            filename=f'{results_path}/{f}',
            key=f"{kwargs['dag_run'].conf.get('run_id')}/{f}",
            replace=True,
            bucket_name='jataware-world-modelers'
        )
    return

###########################
###### Create Tasks #######
###########################

s3_node = PythonOperator(task_id='s3push-task', 
                             python_callable=s3copy,
                             provide_context=True,
                             dag=dag)

model_node = DojoDockerOperator(
    task_id='model-task',    
    image="{{ dag_run.conf['image'] }}",
    container_name="run_{{ dag_run.conf['run_id'] }}",
    volumes=["//var/run/docker.sock://var/run/docker.sock", "/home/ubuntu/dojo/dmc/results/{{ dag_run.conf['run_id'] }}:{{ dag_run.conf['output_directory'] }}"],
    docker_url="unix:///var/run/docker.sock",
    network_mode="bridge",
    command="{{ dag_run.conf['command'] }}",
    auto_remove=True,
    dag=dag
)

transform_node = DojoDockerOperator(
    task_id='transform-task',    
    image="{{ dag_run.conf['x_image'] }}",
    container_name="run_{{ dag_run.conf['run_id'] }}",
    volumes=["//var/run/docker.sock://var/run/docker.sock", 
             "/home/ubuntu/dojo/dmc/results/{{ dag_run.conf['run_id'] }}:{{ dag_run.conf['x_input_directory'] }}",
             "/home/ubuntu/dojo/dmc/results/{{ dag_run.conf['run_id'] }}:{{ dag_run.conf['x_output_directory'] }}"],

    docker_url="unix:///var/run/docker.sock",
    network_mode="bridge",
    command="{{ dag_run.conf['x_command'] }}",
    auto_remove=True,
    dag=dag
)

model_node >> transform_node >> s3_node