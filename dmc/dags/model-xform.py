from datetime import timedelta, datetime
import requests
import json
import os
from airflow import DAG
# from airflow.providers.docker.operators.docker import DockerOperator
from operators.dojo_operators import DojoDockerOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.utils.dates import days_ago
from airflow.configuration import conf
from airflow.models import Variable
from jinja2 import Template

import glob

import logging
from logging import Logger
logger: Logger = logging.getLogger(__name__)

# Get latest version of mixmasta
mixmasta_version = os.getenv('MIXMASTA_VERSION')
print(f'mixmasta_version: {mixmasta_version}')

### Get ENV variables for Causemos API
causemos_user = os.getenv('CAUSEMOS_USER')
causemos_pwd = os.getenv('CAUSEMOS_PWD')
causemos_base_url = os.getenv('CAUSEMOS_BASE_URL')
active_runs = int(os.getenv('DAG_MAX_ACTIVE_RUNS'))
concurrency = int(os.getenv('DAG_CONCURRENCY'))

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
    max_active_runs=active_runs,
    concurrency=concurrency
)


#########################
###### Functions ########
#########################

def rehydrate(ti, **kwargs):
    # get default dict
    defaultDict = {}
    dojo_url = kwargs['dag_run'].conf.get('dojo_url')
    model_id = kwargs['dag_run'].conf.get('model_id')
    run_id = kwargs['dag_run'].conf.get('run_id')
    saveFolder =  f"/model_configs/{run_id}/"
    output_dir =kwargs['dag_run'].conf.get('model_output_directory')

    # get the model
    req = requests.get(f"{dojo_url}/models/{model_id}")
    respData = json.loads(req.content)
    params = respData["parameters"]
    print(f'params: {params}')

    print(f'kwargs: {kwargs}')

    #build "type" dict:
    type_dict = {}
    for param in params:
        
        type_dict[param["name"]] = param["type"]

    print(f'type_dict: {type_dict}')  
        
    try:

        for configFile in kwargs['dag_run'].conf.get('s3_config_files'):

            fileName = configFile.get('fileName')
            model_config_s3 = configFile.get('s3_url')
            mountPath = configFile.get('path')

            respTemplate = requests.get(model_config_s3)
            dehydrated_config = respTemplate.content.decode('utf-8')
            for p in params:
                defaultDict[p['name']] = p['default']

            # parameters the user sent in
            hydrateData = kwargs['dag_run'].conf.get('params')

            # need to loop over defaultDict and update with hydrateData values
            for key in hydrateData:
                if key in defaultDict.keys():
                    defaultDict[key] = hydrateData[key]

            finalDict = {}
            for key in defaultDict:
                 print(f'DEFAULT: key: {key} value: {defaultDict[key]}   type: {type(defaultDict[key])}')
            for key in hydrateData:
                 print(f'hydrateData: key: {key} value: {hydrateData[key]}   type: {type(hydrateData[key])}')
            
            # Hydrate the config
            if os.path.exists(saveFolder):
                print('here')
                pass

            else:
                os.mkdir(saveFolder, mode=0o777)

            os.chmod(saveFolder, mode=0o777)

            # Template(dehydrated_config).stream(finalDict).dump(savePath)
            dataToSave = Template(dehydrated_config).render(defaultDict)

            print(f'dataToSave: {dataToSave}')
            # savePath needs to be hard coded for ubuntu path with run id and model name or something.
            saveFileName=saveFolder+fileName
            with open(saveFileName, "w+") as fh:
                fh.write(dataToSave)
            os.chmod(saveFileName, mode=0o777)

    except Exception as e:
        print(e)
    print('done')


def accessoryNodeTask(**kwargs):
    """
        If anything is in /results/{run.id}/accessories, push it to S3.
    """
    s3 = S3Hook(aws_conn_id="aws_default")
    accessories_path = f"/results/{kwargs['dag_run'].conf.get('run_id')}/accessories"
    logger.info(f'accessories_path: {accessories_path}')

    # get the model accessories
    dojo_url = kwargs['dag_run'].conf.get('dojo_url')
    model_id = kwargs['dag_run'].conf.get('model_id')
    req = requests.get(f"{dojo_url}/dojo/accessories/{model_id}")
    accessories = json.loads(req.content)

    for accessory in accessories:
        fp_ = accessory.get('path','').split('/')[-1]
        logger.info(f'fpath raw:{accessories_path}/{fp_}')
        matches = glob.glob(f"{accessories_path}/{fp_}")

        # if no accessory files are found, just return nothing
        # I don't believe this should cause the task to fail, since the model outputs may
        # have successfuly been transformed and might still have utility, even if the accessories
        # were dropped
        if len(matches) == 0:
            logger.error(f'No accessory files were found matching: {accessories_path}/{fp_}')
            continue

        fpath = matches[0]
        logger.info(f'fpath ready:{fpath}')

        fn = fpath.split("/")[-1]
        logger.info(f'fn:{fn}')

        # move accessory and inject id into filepath
        fpath_new = f"{accessories_path}/{accessory['id']}__dojo__{fn}"
        os.rename(fpath, fpath_new)

        # NOTE: objects stored to dmc_results are automatically made public
        # per the S3 bucket's policy
        # TODO: may need to address this with more fine grained controls in the future
        bucket_dir = os.getenv('BUCKET_DIR')
        key=f"{bucket_dir}/{kwargs['dag_run'].conf.get('run_id')}/{fn}"

        logger.info('key:' + key)

        s3.load_file(
            filename=fpath_new,
            key=key,
            replace=True,
            bucket_name=os.getenv('BUCKET')
        )
                  

def s3copy(**kwargs):
    s3 = S3Hook(aws_conn_id="aws_default")
    results_path = f"/results/{kwargs['dag_run'].conf.get('run_id')}"

    for fpath in glob.glob(f'{results_path}/*.parquet.gzip'):
        print(f'fpath:{fpath}')
        fn = fpath.split("/")[-1]
        print(f'fn:{fn}')

        # NOTE: objects stored to dmc_results are automatically made public
        # per the S3 bucket's policy
        # TODO: may need to address this with more fine grained controls in the future
        bucket_dir = os.getenv('BUCKET_DIR')
        key=f"{bucket_dir}/{kwargs['dag_run'].conf.get('run_id')}/{fn}"

        s3.load_file(
            filename=fpath,
            key=key,
            replace=True,
            bucket_name=os.getenv('BUCKET')
        )

    return


def getMapper(**kwargs):
    dojo_url = kwargs['dag_run'].conf.get('dojo_url')
    model_id = kwargs['dag_run'].conf.get('model_id')
    ofs = requests.get(f"{dojo_url}/dojo/outputfile/{model_id}").json()
    for of in ofs:
        mapper = of['transform']
        with open(f'/mappers/mapper_{of["id"]}.json','w') as f:
            f.write(json.dumps(mapper))


def RunExit(**kwargs):
    dojo_url = kwargs['dag_run'].conf.get('dojo_url')
    run_id = kwargs['dag_run'].conf.get('run_id')
    model_id = kwargs['dag_run'].conf.get('model_id')
    run = requests.get(f"{dojo_url}/runs/{run_id}").json()

    # TODO: this should be conditional; if the other tasks fail
    # this should reflect the failure; job should always finish
    if 'attributes' not in run:
        run['attributes'] = {'status': 'success'}
    else:
        run['attributes']['status'] = 'success'

    # get pth array
    print("Processing results:")
    pth=[]
    for fpath in glob.glob(f'/results/{run_id}/*.parquet.gzip'):
        print(f'fpath:{fpath}')
        fn = fpath.split("/")[-1]
        print(f'fn:{fn}')
        bucket_dir = os.getenv('BUCKET_DIR')
        pth.append(f"https://jataware-world-modelers.s3.amazonaws.com/{bucket_dir}/{run_id}/{fn}")

    print('pth array' ,pth)
    run['data_paths'] = pth

    print("Processing accessories:")
    # Prepare accessory lookup
    req = requests.get(f"{dojo_url}/dojo/accessories/{model_id}")
    accessories = json.loads(req.content)
    caption_lookup = {}
    for accessory in accessories:
        caption_lookup[accessory['id']] = accessory.get('caption','')
    
    print(f"Accessories: {accessories}")
    print(f"Caption Lookup: {caption_lookup}")
    accessories_paths = set([i.get('path').split('/')[-1] for i in accessories])
        
    # Get any accessories and append their S3 URLS to run['pre_gen_output_paths']
    accessories_array = []
    for fpath in glob.glob(f'/results/{run_id}/accessories/*'):
        accessory_dict = {}
        print(f'fpath:{fpath}')
        fn = fpath.split("/")[-1]
        print(f'fn:{fn}')
        if '__dojo__' in fn:
            if fn.split('__dojo__')[1] in accessories_paths:
                print("Found accessory, processing...")
                accessory_id = fn.split('__dojo__')[0]
                fn_aws_key = fn.split('__dojo__')[1]
                bucket_dir = os.getenv('BUCKET_DIR')
                accessory_dict['file'] = f"https://jataware-world-modelers.s3.amazonaws.com/{bucket_dir}/{run_id}/{fn_aws_key}"
                accessory_dict['caption'] = caption_lookup[accessory_id]
                accessories_array.append(accessory_dict)
        else:
            print("Not tagged as accessory, skipping.")

    print('accessories_array', accessories_array)

    run['pre_gen_output_paths'] = accessories_array

    # Update attributes.executed_at.
    run['attributes']['executed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Create the response, which is the response from the dojo api/runs PUT.
    response = requests.put(f"{dojo_url}/runs", json=run)
    print(response.text)

    # Notify Uncharted
    if os.getenv('DMC_DEBUG') == 'true':
        print("testing Debug mode: no need to notify Uncharted")
        return
    else:
        print('Notifying Uncharted...')
        response = requests.post(f'{causemos_base_url}/{run_id}/post-process',
                                headers={'Content-Type': 'application/json'}, 
                                json=run, 
                                auth=(causemos_user, causemos_pwd))
        print(f"Response from Uncharted: {response.text}")
        return
    

def post_failed_to_dojo(**kwargs):

    dojo_url = kwargs['dag_run'].conf.get('dojo_url')
    run_id = kwargs['dag_run'].conf.get('run_id')
    model_id = kwargs['dag_run'].conf.get('model_id')
    run = requests.get(f"{dojo_url}/runs/{run_id}").json()

    # TODO: this should be conditional; if the other tasks fail
    # this should reflect the failure; job should always finish
    if 'attributes' not in run:
        run['attributes'] = {'status': 'failed'}
    else:
        run['attributes']['status'] = 'failed'

    response = requests.put(f"{dojo_url}/runs", json=run)
    print(response.text)

    # Notify Uncharted
    if os.getenv('DMC_DEBUG') == 'true':
        print("Debug mode: no need to notify Uncharted")
        return
    else:
        print('Notifying Uncharted...')
        response = requests.post(f'{causemos_base_url}/{run_id}/run-failed',
                                 headers={'Content-Type': 'application/json'},
                                 json=run,
                                 auth=(causemos_user, causemos_pwd))
        print(f"Response from Uncharted: {response.text}")
        return


###########################
###### Create Tasks #######
###########################

dmc_local_dir = os.environ.get("DMC_LOCAL_DIR")


rehydrate_node = PythonOperator(task_id='rehydrate-task',
                             python_callable=rehydrate,
                             provide_context=True,
                             dag=dag)

acccessory_node = PythonOperator(task_id='accessory-task',
                             trigger_rule='all_success',
                             python_callable=accessoryNodeTask,
                             provide_context=True,
                             dag=dag)                             

s3_node = PythonOperator(task_id='s3push-task',
                             trigger_rule='all_success',
                             python_callable=s3copy,
                             provide_context=True,
                             dag=dag)

mapper_node = PythonOperator(task_id='mapper-task',
                             trigger_rule='all_success',
                             python_callable=getMapper,
                             provide_context=True,
                             dag=dag)

exit_node = PythonOperator(task_id='exit-task',
                             trigger_rule='all_success',
                             python_callable=RunExit,
                             provide_context=True,
                             dag=dag)

model_node = DojoDockerOperator(
    task_id='model-task',
    trigger_rule='all_success',
    image="{{ dag_run.conf['model_image'] }}",
    container_name="run_{{ dag_run.conf['run_id'] }}",
    volumes="{{ dag_run.conf['volumes'] }}",
    docker_url=os.environ.get("DOCKER_URL", "unix:///var/run/docker.sock"),
    network_mode="bridge",
    command="{{ dag_run.conf['model_command'] }}",
    auto_remove=True,
    dag=dag
)

transform_node = DojoDockerOperator(
    task_id='mixmasta-task',
    trigger_rule='all_success',
    image=f"jataware/mixmasta:{mixmasta_version}",
    container_name="run_{{ dag_run.conf['run_id'] }}",
    volumes=[dmc_local_dir + "/results/{{ dag_run.conf['run_id'] }}:/tmp",
             dmc_local_dir + "/mappers:/mappers"],
    docker_url=os.environ.get("DOCKER_URL", "unix:///var/run/docker.sock"),
    network_mode="bridge",
    command="{{ dag_run.conf['mixmasta_cmd'] }}",
    auto_remove=True,
    dag=dag
)

notify_failed_node = PythonOperator(task_id='failed-task',
                             python_callable=post_failed_to_dojo,
                             trigger_rule='one_failed',
                             provide_context=True,
                             dag=dag)

rehydrate_node >> model_node >>  mapper_node >> transform_node >> acccessory_node >> s3_node
s3_node >> notify_failed_node
s3_node >> exit_node