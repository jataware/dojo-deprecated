from airflow.operators.docker_operator import DockerOperator

class DojoDockerOperator(DockerOperator):
    template_fields = ('image', 'command', 'environment', 'container_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)