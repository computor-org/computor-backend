import click
from fastapi import HTTPException
from httpx import ConnectError
from computor_cli.auth import authenticate, get_crud_client
from computor_cli.config import CLIAuthConfig
from computor_types import endpoints
from computor_types.results import ResultInterface
from computor_types.users import UserInterface
from computor_types.courses import CourseInterface
from computor_types.organizations import OrganizationInterface
from computor_types.course_families import CourseFamilyInterface
from computor_types.course_groups import CourseGroupInterface
from computor_types.course_members import CourseMemberInterface
from computor_types.course_roles import CourseRoleInterface
from computor_types.course_content_types import CourseContentTypeInterface
from computor_types.course_contents import CourseContentInterface

AVAILABLE_DTO_DEFINITIONS = [
    endpoints.ORGANIZATIONS_ENDPOINT,
    endpoints.COURSE_FAMILIES_ENDPOINT,
    endpoints.COURSES_ENDPOINT,
    endpoints.COURSE_CONTENTS_ENDPOINT,
    endpoints.COURSE_CONTENT_TYPES_ENDPOINT,
    endpoints.COURSE_GROUPS_ENDPOINT,
    endpoints.COURSE_MEMBERS_ENDPOINT,
    endpoints.COURSE_ROLES_ENDPOINT,
    endpoints.USERS_ENDPOINT,
    endpoints.RESULTS_ENDPOINT,
]

def DTO_DEFINITIONS(table: str):
    """Map endpoint name to interface class."""
    if endpoints.ORGANIZATIONS_ENDPOINT == table:
        return OrganizationInterface
    elif endpoints.COURSE_FAMILIES_ENDPOINT == table:
        return CourseFamilyInterface
    elif endpoints.COURSES_ENDPOINT == table:
        return CourseInterface
    elif endpoints.COURSE_CONTENTS_ENDPOINT == table:
        return CourseContentInterface
    elif endpoints.COURSE_CONTENT_TYPES_ENDPOINT == table:
        return CourseContentTypeInterface
    elif endpoints.COURSE_GROUPS_ENDPOINT == table:
        return CourseGroupInterface
    elif endpoints.COURSE_MEMBERS_ENDPOINT == table:
        return CourseMemberInterface
    elif endpoints.COURSE_ROLES_ENDPOINT == table:
        return CourseRoleInterface
    elif endpoints.USERS_ENDPOINT == table:
        return UserInterface
    elif endpoints.RESULTS_ENDPOINT == table:
        return ResultInterface
    else:
        raise Exception("Not found")


def handle_api_exceptions(func):
  def wrapper(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except ConnectError as e:
      click.echo(f"Connection to [{click.style(kwargs['auth'].api_url,fg='red')}] could not be established.")
    except HTTPException as e:
      message = e.detail.get("detail")
      message = message if message != None else e.detail
      click.echo(f"[{click.style(e.status_code,fg='red')}] {message}")
    except Exception as e:
      click.echo(f"[{click.style('500',fg='red')}] {e.args if e.args != () else 'Internal Server Error'}")

  return wrapper

@click.command()
@click.option("--table", "-t", type=click.Choice(AVAILABLE_DTO_DEFINITIONS), prompt="Type")
@click.option("--query", "-q", "query", type=(str, str), multiple=True)
@authenticate
@handle_api_exceptions
def list_entities(table, query, auth: CLIAuthConfig):

  params = None
  query = dict(query)
  if dict(query) != {}:
    params = DTO_DEFINITIONS(table).query(**query)

  resp = get_crud_client(auth,DTO_DEFINITIONS(table)).list(params)

  for entity in resp:
    click.echo(f"{entity.model_dump_json(indent=4)}")

@click.command()
@click.option("--table", "-t", type=click.Choice(AVAILABLE_DTO_DEFINITIONS), prompt="Type")
def show_entities_query(table):

  dto = DTO_DEFINITIONS(table)

  query_fields = dto.query.model_fields

  click.echo(f"Query parameters for endpoint [{click.style(dto.endpoint,fg='green')}]:\n")
  for field, info in query_fields.items():
    click.echo(f"{click.style(field,fg='green')} - {info.annotation}")

@click.command()
@click.option("--table", "-t", type=click.Choice(AVAILABLE_DTO_DEFINITIONS), prompt="Type")
@click.option("--id", "-i", prompt=True)
@authenticate
@handle_api_exceptions
def get_entity(table, id, auth: CLIAuthConfig):

  entity = get_crud_client(auth,DTO_DEFINITIONS(table)).get(id)

  click.echo(f"{entity.model_dump_json(indent=4)}")

@click.group()
def rest():
    pass

rest.add_command(list_entities,"list")
rest.add_command(show_entities_query,"query")
rest.add_command(get_entity,"get")