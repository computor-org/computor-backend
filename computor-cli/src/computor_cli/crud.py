import click
from fastapi import HTTPException
from httpx import ConnectError
from computor_cli.auth import authenticate, get_computor_client
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async
from computor_types import endpoints
from computor_types.results import ResultQuery
from computor_types.users import UserQuery
from computor_types.courses import CourseQuery
from computor_types.organizations import OrganizationQuery
from computor_types.course_families import CourseFamilyQuery
from computor_types.course_groups import CourseGroupQuery
from computor_types.course_members import CourseMemberQuery
from computor_types.course_roles import CourseRoleQuery
from computor_types.course_content_types import CourseContentTypeQuery
from computor_types.course_contents import CourseContentQuery

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

def GET_CLIENT_ATTRIBUTE(client, table: str):
    """Map endpoint name to ComputorClient attribute."""
    if endpoints.ORGANIZATIONS_ENDPOINT == table:
        return client.organizations
    elif endpoints.COURSE_FAMILIES_ENDPOINT == table:
        return client.course_families
    elif endpoints.COURSES_ENDPOINT == table:
        return client.courses
    elif endpoints.COURSE_CONTENTS_ENDPOINT == table:
        return client.course_contents
    elif endpoints.COURSE_CONTENT_TYPES_ENDPOINT == table:
        return client.course_content_types
    elif endpoints.COURSE_GROUPS_ENDPOINT == table:
        return client.course_groups
    elif endpoints.COURSE_MEMBERS_ENDPOINT == table:
        return client.course_members
    elif endpoints.COURSE_ROLES_ENDPOINT == table:
        return client.course_roles
    elif endpoints.USERS_ENDPOINT == table:
        return client.users
    elif endpoints.RESULTS_ENDPOINT == table:
        return client.results
    else:
        raise Exception("Not found")

def GET_QUERY_CLASS(table: str):
    """Map endpoint name to Query class."""
    if endpoints.ORGANIZATIONS_ENDPOINT == table:
        return OrganizationQuery
    elif endpoints.COURSE_FAMILIES_ENDPOINT == table:
        return CourseFamilyQuery
    elif endpoints.COURSES_ENDPOINT == table:
        return CourseQuery
    elif endpoints.COURSE_CONTENTS_ENDPOINT == table:
        return CourseContentQuery
    elif endpoints.COURSE_CONTENT_TYPES_ENDPOINT == table:
        return CourseContentTypeQuery
    elif endpoints.COURSE_GROUPS_ENDPOINT == table:
        return CourseGroupQuery
    elif endpoints.COURSE_MEMBERS_ENDPOINT == table:
        return CourseMemberQuery
    elif endpoints.COURSE_ROLES_ENDPOINT == table:
        return CourseRoleQuery
    elif endpoints.USERS_ENDPOINT == table:
        return UserQuery
    elif endpoints.RESULTS_ENDPOINT == table:
        return ResultQuery
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

  client = run_async(get_computor_client(auth))

  params = None
  query = dict(query)
  if dict(query) != {}:
    params = GET_QUERY_CLASS(table)(**query)

  resp = GET_CLIENT_ATTRIBUTE(client, table).list(params)

  for entity in resp:
    click.echo(f"{entity.model_dump_json(indent=4)}")

@click.command()
@click.option("--table", "-t", type=click.Choice(AVAILABLE_DTO_DEFINITIONS), prompt="Type")
def show_entities_query(table):

  query_class = GET_QUERY_CLASS(table)

  query_fields = query_class.model_fields

  click.echo(f"Query parameters for endpoint [{click.style(table,fg='green')}]:\n")
  for field, info in query_fields.items():
    click.echo(f"{click.style(field,fg='green')} - {info.annotation}")

@click.command()
@click.option("--table", "-t", type=click.Choice(AVAILABLE_DTO_DEFINITIONS), prompt="Type")
@click.option("--id", "-i", prompt=True)
@authenticate
@handle_api_exceptions
def get_entity(table, id, auth: CLIAuthConfig):

  client = run_async(get_computor_client(auth))

  entity = GET_CLIENT_ATTRIBUTE(client, table).get(id)

  click.echo(f"{entity.model_dump_json(indent=4)}")

@click.group()
def rest():
    pass

rest.add_command(list_entities,"list")
rest.add_command(show_entities_query,"query")
rest.add_command(get_entity,"get")