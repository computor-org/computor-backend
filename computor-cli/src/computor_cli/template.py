import click
import yaml

@click.command()
def create_template_course():

    from computor_types.deployments import COURSE_DEFAULT_DEPLOYMENT

    with open("template.yaml", "w") as file:
        file.write(yaml.safe_dump(COURSE_DEFAULT_DEPLOYMENT.model_dump(exclude_none=True)))

@click.group()
def template():
    pass

template.add_command(create_template_course,"course")