import requests
import click
import time

@click.group()
@click.option('--dojo_url', default='localhost:8000', help='The Dojo URL')
@click.option('--dojo_user', default='', help='The Dojo username.')
@click.option('--dojo_pwd', default='', help='The Dojo password.')
@click.pass_context
def cli(ctx, dojo_url, dojo_user, dojo_pwd):
    ctx.ensure_object(dict)
    if dojo_user == '':
        ctx.obj['dojo_auth_url'] = f"http://{dojo_url}"
    else:
        ctx.obj['dojo_auth_url'] = f"https://{dojo_user}:{dojo_pwd}@{dojo_url}"

@cli.command(name='test')
@click.pass_context
def test(ctx):
    """Obtain list of published models and submit them to Dojo for testing."""
    dojo_auth_url = ctx.obj['dojo_auth_url']
    models = requests.get(f"{dojo_auth_url}/models/latest?size=100").json()
    for model in models.get('results', []):
        if model.get("is_published",False):
            click.echo(f"Submitting model {model['id']} to Dojo for testing.")
            response = requests.get(f"{dojo_auth_url}/models/{model['id']}/test")
            with open("test_models.log", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{model['id']}\t{response.text}\n")

@cli.command(name='validate')
@click.pass_context
def validate(ctx):
    """Validate submitted tests for success/failure."""
    dojo_auth_url = ctx.obj['dojo_auth_url']
    with open('test_models.log', 'r') as f:
        for line in f:
            time, model_id, run_id = line.replace('\n','').split('\t')
            click.echo(f"Submitting run_id {run_id} to Dojo for validation.")
            response = requests.get(f"{dojo_auth_url}/runs/{run_id}/test")
            click.echo(response.text)

if __name__ == '__main__':
    cli(obj={})