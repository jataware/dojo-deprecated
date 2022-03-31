import json
from typing import Optional
import os
from docker.errors import APIError
import tarfile
import io
import pickle
import yaml

from airflow.operators.docker_operator import DockerOperator

from airflow.utils.helpers import parse_template_string


class DojoDockerOperator(DockerOperator):
    template_fields = ('image', 'command', 'environment', 'container_name', 'volumes', 'docker_url')

    def __init__(self, *args, do_login=False, additional_volumes=None, **kwargs):
        super().__init__(*args, **kwargs)
        print(self.volumes)
        self.do_login = do_login
        print(f"{self.do_login=}")
        self.additional_volumes = additional_volumes if additional_volumes else []

    def pre_execute(self, context):
        self.log.info(f"pre_exc {self.command=}")
        self.log.info(f"pre_exc {self.docker_url=}")
        self.log.info(f"pre_exc {self.image=}")
        self.log.info(f"pre_exc {self.user}")

    def post_execute(self, context, result=None):
        self.log.debug("post_exec %s", result)
        super().post_execute(context, result)

    def execute(self, context) -> Optional[str]:
        # Handle volume mount
        if isinstance(self.volumes, str):
            self.volumes = json.loads(self.volumes)

        for v in self.additional_volumes:
            self.volumes.append(v)

        print(f"{self.volumes=}")

        self.cli = self._get_cli()
        if not self.cli:
            raise Exception("The 'cli' should be initialized before!")

        self.log.info('Do Docker Login %s', self.do_login)
        if self.do_login:
            docker_user = os.environ.get("DOCKERHUB_USER")
            docker_pass = os.environ.get("DOCKERHUB_PASS")

            self.log.info('log in to dockerhub for user: %s', docker_user)
            self.cli.login(docker_user, docker_pass, registry="https://index.docker.io/v1")

        # Pull the docker image if `force_pull` is set or image does not exist locally
        # pylint: disable=too-many-nested-blocks
        if self.force_pull or not self.cli.images(name=self.image):
            self.log.info('Pulling docker image %s', self.image)
            latest_status = {}
            for output in self.cli.pull(self.image, stream=True, decode=True):
                if isinstance(output, str):
                    self.log.info("%s", output)
                    continue
                if isinstance(output, dict) and 'status' in output:
                    output_status = output["status"]
                    if 'id' not in output:
                        self.log.info("%s", output_status)
                        continue

                    output_id = output["id"]
                    if latest_status.get(output_id) != output_status:
                        self.log.info("%s: %s", output_id, output_status)
                        latest_status[output_id] = output_status

        self.environment['AIRFLOW_TMP_DIR'] = self.tmp_dir
        return self._run_image()


class HammerheadDockerOperator(DockerOperator):
    template_fields = ('image', 'command', 'environment', 'container_name', 'volumes', 'docker_url', 'volume_size',
                       'instance_type')

    def __init__(self, instance_type="t3.micro", version="latest", volume_size=8, *args, **kwargs):

        image = f"jataware/hammerhead:{version}"
        super().__init__(**{"image": image, **kwargs})
        self.force_pull = False
        self.volume_size = volume_size
        self.instance_type = instance_type

    def _attempt_to_retrieve_result(self):
        """
        Attempts to pull the result of the function from the expected file using docker's
        get_archive function.
        If the file is not yet ready, returns None
        :return:
        """

        def copy_from_docker(container_id, src):
            archived_result, stat = self.cli.get_archive(container_id, src)
            self.log.info("** stat %s", stat)
            if stat['size'] == 0:
                # 0 byte file, it can't be anything else than None
                return None
            # no need to port to a file since we intend to deserialize
            file_standin = io.BytesIO(b"".join(archived_result))
            tar = tarfile.open(fileobj=file_standin)
            file = tar.extractfile(stat['name'])
            return file.read()

        try:
            self.log.info("** Container Id %s", self.container['Id'])
            return copy_from_docker(self.container['Id'], "/tmp/results.out")
        except APIError as aie:
            self.log.info("** PULL archive API Error %s", aie)
            return None

    def pre_execute(self, context):
        self.log.info("pre_exc %s", self.docker_url)
        self.log.info("pre_exc %s", self.volume_size)
        self.log.info("pre_exc %s", self.instance_type)
        #_, tmpl = parse_template_string(self.docker_url)
        #self.docker_url = tmpl.render(**context)
        #self.log.info("pre_exc docker_url %s", self.docker_url)


    def post_execute(self, context, result=None):

        if self.cli is not None:
            try:
                results = self._attempt_to_retrieve_result()
                dct = yaml.safe_load(results)
            finally:
                self.cli.remove_container(self.container['Id'])
                context['ti'].xcom_push(key='instance_info', value=dct)

        super().post_execute(context, results)

    def execute(self, context) -> Optional[str]:

        self.log.info("ctx: %s", context)
        # Handle volume mount
        if isinstance(self.volumes, str):
            self.volumes = json.loads(self.volumes)

        self.cli = self._get_cli()
        if not self.cli:
            raise Exception("The 'cli' should be initialized before!")


        self.environment = {**self.environment,
                            "ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED": "y",
                            "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
                            "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
                            "AWS_DEFAULT_REGION": "us-east-1",
                            "DEPLOY_ID_RSA": os.environ.get("ID_RSA")}

        self.command = [
            "ansible-playbook",
            "launch-airflow-worker.yaml",
            "-e",
            f"instance_type={self.instance_type}",
            "-e",
            f"volume_size={self.volume_size}",
            "-e",
            "dockerhub_registry_user=${DOCKERHUB_USER:?}",
            "-e",
            "dockerhub_registry_pass=${DOCKERHUB_PASS:?}",
        ]

        docker_user = os.environ.get("DOCKERHUB_USER")
        docker_pass = os.environ.get("DOCKERHUB_PASS")

        self.log.info('log in to dockerhub for user: %s', docker_user)
        self.cli.login(docker_user, docker_pass, registry="https://index.docker.io/v1")


        # Pull the docker image if `force_pull` is set or image does not exist locally
        # pylint: disable=too-many-nested-blocks
        if self.force_pull or not self.cli.images(name=self.image):
            self.log.info('Pulling docker image %s', self.image)
            latest_status = {}
            for output in self.cli.pull(self.image, stream=True, decode=True):
                if isinstance(output, str):
                    self.log.info("%s", output)
                    continue
                if isinstance(output, dict) and 'status' in output:
                    output_status = output["status"]
                    if 'id' not in output:
                        self.log.info("%s", output_status)
                        continue

                    output_id = output["id"]
                    if latest_status.get(output_id) != output_status:
                        self.log.info("%s: %s", output_id, output_status)
                        latest_status[output_id] = output_status

        #self.environment['AIRFLOW_TMP_DIR'] = self.tmp_dir
        return self._run_image()


class HammerheadTeardownDockerOperator(DockerOperator):
    template_fields = ('image', 'command', 'environment', 'container_name', 'volumes', 'docker_url')

    def __init__(self, version="latest", *args, **kwargs):

        image = f"jataware/hammerhead:{version}"
        super().__init__(**{"image": image, **kwargs})
        self.dns_name = None

    def pre_execute(self, context):
        self.log.info("pre_exc %s", self.docker_url)
        ii = context["ti"].xcom_pull(key="instance_info")
        self.log.info("pre_exc %s", ii)
        self.dns_name = ii["DNS_NAME"]
        assert self.dns_name, "DNS name is not none"
        self.log.info("pre_exc %s", self.dns_name)
        #_, tmpl = parse_template_string(self.docker_url)
        #self.docker_url = tmpl.render(**context)
        #self.log.info("pre_exc docker_url %s", self.docker_url)

    def execute(self, context) -> Optional[str]:

        self.log.info("ctx: %s", context)
        # Handle volume mount
        if isinstance(self.volumes, str):
            self.volumes = json.loads(self.volumes)

        self.cli = self._get_cli()
        if not self.cli:
            raise Exception("The 'cli' should be initialized before!")

        self.environment = {**self.environment,
                            "ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED": "y",
                            "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
                            "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
                            "AWS_DEFAULT_REGION": "us-east-1",
                            "DEPLOY_ID_RSA": os.environ.get("ID_RSA")}

        self.command = [
            "ansible-playbook",
            "-i",
            "./hosts.py",
            "terminate-instance.yaml",
            "--limit",
            f"{self.dns_name}",
        ]

        docker_user = os.environ.get("DOCKERHUB_USER")
        docker_pass = os.environ.get("DOCKERHUB_PASS")

        self.log.info('log in to dockerhub for user: %s', docker_user)
        self.cli.login(docker_user, docker_pass, registry="https://index.docker.io/v1")


        # Pull the docker image if `force_pull` is set or image does not exist locally
        # pylint: disable=too-many-nested-blocks
        if self.force_pull or not self.cli.images(name=self.image):
            self.log.info('Pulling docker image %s', self.image)
            latest_status = {}
            for output in self.cli.pull(self.image, stream=True, decode=True):
                if isinstance(output, str):
                    self.log.info("%s", output)
                    continue
                if isinstance(output, dict) and 'status' in output:
                    output_status = output["status"]
                    if 'id' not in output:
                        self.log.info("%s", output_status)
                        continue

                    output_id = output["id"]
                    if latest_status.get(output_id) != output_status:
                        self.log.info("%s: %s", output_id, output_status)
                        latest_status[output_id] = output_status

        #self.environment['AIRFLOW_TMP_DIR'] = self.tmp_dir
        return self._run_image()
