import click
import yaml

@click.command()
def create_template_course():

    from computor_types.deployments_refactored import EXAMPLE_DEPLOYMENT

    with open("template.yaml", "w") as file:
        file.write(yaml.safe_dump(EXAMPLE_DEPLOYMENT.model_dump(exclude_none=True)))

@click.group()
def template():
    pass

template.add_command(create_template_course,"course")