from datetime import timedelta
from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator

from kubernetes.client import models as k8s
from kubernetes.client.models import V1Volume as Volume
from kubernetes.client.models import V1VolumeMount as VolumeMount

from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.providers.amazon.aws.operators import s3_copy_object

from airflow.utils.dates import days_ago

###########################
###### Set up volume ######
###########################
volume_mount = VolumeMount(name='results-volume',
                           mount_path='/outputs',
                           sub_path=None,
                           read_only=False)


volume = Volume(name='results-volume', persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name='results-claim'))


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
    schedule_interval=timedelta(minutes=30),
    max_active_runs=1,
    concurrency=10
)

###########################
###### Create Tasks #######
###########################

result_node = KubernetesPodOperator(
    namespace='default',
    name='result-run',    
    task_id="result-task",
    image='ubuntu:latest',
    cmds=["ls", "/outputs"],
    volumes=[volume],
    volume_mounts=[volume_mount],
    wait_for_downstream=False,
    is_delete_operator_pod=False,
    get_logs=True,    
    dag=dag
)


fsc_node = KubernetesPodOperator(
    namespace='default',
    image="jataware/fsc_model:0.1",
    # cmds=["python", "-c"],
    arguments=["0", "1", "0.5"],
    labels={"model": "fsc"},
    image_pull_policy="Always",
    volumes=[volume],
    volume_mounts=[volume_mount], 
    name='fsc-run',
    task_id='fsc-task',
    is_delete_operator_pod=False,
    get_logs=True,
    dag=dag
)

fsc_node.set_downstream(result_node)
