from datetime import timedelta
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
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

Variable.set("image", "")
Variable.set("p1", "")

def set_vars(**kwargs):
    image = Variable.set("image", kwargs['dag_run'].conf.get('image'))
    p1 = Variable.set("p1", "param1")
    print(image, p1)
    return

def del_vars(**kwargs):
    image = Variable.delete("image")
    p1 = Variable.delete("p1")
    return    

var_node = PythonOperator(task_id='var_task', 
                             python_callable=set_vars,
                             provide_context=True,
                             dag=dag)

var_del_node = PythonOperator(task_id='var_del_task', 
                             python_callable=del_vars,
                             provide_context=True,
                             dag=dag)

def s3copy():
    s3 = S3Hook(aws_conn_id="s3_connection")

    result_node = s3.load_file(
        filename='/outputs/Production_TimeSeries.csv',
        key='Production_TimeSeries.csv',
        replace=True,
        bucket_name='jataware-world-modelers'
    )
    return

s3_node = PythonOperator(task_id='python_task', 
                             python_callable=s3copy,
                             dag=dag)

image_name = Variable.get("image")

model_node = DockerOperator(
    image=image_name,
    volumes=["//var/run/docker.sock://var/run/docker.sock", "/home/ubuntu/dojo/dmc/outputs:/outputs"],
    docker_url="unix:///var/run/docker.sock",
    network_mode="bridge",
    # cmds=["python", "-c"],
    command=["{{ dag_run.conf[var.value.p1] }}", "{{ dag_run.conf['param2'] }}", "{{ dag_run.conf['param3'] }}"],
    task_id='model-task',
    dag=dag
)

var_node >> model_node >> s3_node >> var_del_node