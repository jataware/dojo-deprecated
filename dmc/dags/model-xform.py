from datetime import timedelta
import requests
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

import glob

############################
####### Generate DAG #######
############################

default_args = {
    'owner': 'Jataware',
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
    'model_xform',
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

    results_path = f"/results/{kwargs['dag_run'].conf.get('run_id')}"
    print(f'results_path:{results_path}')

    for fpath in glob.glob(f'{results_path}/*[norm]*.csv'):
        print(f'fpath:{fpath}')
        fn = fpath.split("/")[-1]
        print(f'fn:{fn}')
        key=f"dmc_results/{kwargs['dag_run'].conf.get('run_id')}/{fn}"
        
        s3.load_file(
            filename=fpath,
            key=key,
            replace=True,
            bucket_name='jataware-world-modelers'
        )
    
    return

def getMapper(**kwargs):
    dojo_url = kwargs['dag_run'].conf.get('dojo_url')
    model_id = kwargs['dag_run'].conf.get('model_id')
    of = requests.get(f"{dojo_url}/dojo/outputfile/{model_id}").json()
    mapper = of[0]['transform']
    with open(f'/home/ubuntu/dojo/dmc/mappers/mapper_{model_id}.json','w') as f:
        f.write(json.dumps(mapper))

###########################
###### Create Tasks #######
###########################

s3_node = PythonOperator(task_id='s3push-task', 
                             python_callable=s3copy,
                             provide_context=True,
                             dag=dag)

mapper_node = PythonOperator(task_id='mapper-task', 
                             python_callable=getMapper,
                             provide_context=True,
                             dag=dag)                   

model_node = DojoDockerOperator(
    task_id='model-task',    
    image="{{ dag_run.conf['model_image'] }}",
    container_name="run_{{ dag_run.conf['run_id'] }}",
    volumes=["//var/run/docker.sock://var/run/docker.sock", "/home/ubuntu/dojo/dmc/results/{{ dag_run.conf['run_id'] }}:{{ dag_run.conf['model_output_directory'] }}"],
    docker_url="unix:///var/run/docker.sock",
    network_mode="bridge",
    command="{{ dag_run.conf['model_command'] }}",
    auto_remove=True,
    dag=dag
)

transform_node = DojoDockerOperator(
    task_id='mixmasta-task',    
    image="jataware/mixmasta:latest",
    container_name="run_{{ dag_run.conf['run_id'] }}",
    volumes=["//var/run/docker.sock://var/run/docker.sock", 
             "/home/ubuntu/dojo/dmc/results/{{ dag_run.conf['run_id'] }}:/tmp",
             "/home/ubuntu/dojo/dmc/mappers:/mappers"],
    docker_url="unix:///var/run/docker.sock",
    network_mode="bridge",
    command="{{ dag_run.conf['mixmasta_cmd'] }}",
    auto_remove=True,
    dag=dag
)

model_node >> mapper_node >> transform_node >> s3_node