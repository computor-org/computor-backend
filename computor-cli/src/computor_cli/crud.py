import click
from httpx import ConnectError, HTTPStatusError
from computor_client.exceptions import ComputorClientError
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
    """Map an endpoint name to its ComputorClient attribute.

    Endpoint constants are the hyphenated URL names (e.g. ``course-families``);
    the client exposes the underscored attribute (``client.course_families``)
    via ``ComputorClient.__getattr__``, so a single dynamic lookup replaces the
    per-endpoint branch table.
    """
    if table not in AVAILABLE_DTO_DEFINITIONS:
        raise Exception("Not found")
    return getattr(client, table.replace('-', '_'))


_QUERY_CLASSES = {
    endpoints.ORGANIZATIONS_ENDPOINT: OrganizationQuery,
    endpoints.COURSE_FAMILIES_ENDPOINT: CourseFamilyQuery,
    endpoints.COURSES_ENDPOINT: CourseQuery,
    endpoints.COURSE_CONTENTS_ENDPOINT: CourseContentQuery,
    endpoints.COURSE_CONTENT_TYPES_ENDPOINT: CourseContentTypeQuery,
    endpoints.COURSE_GROUPS_ENDPOINT: CourseGroupQuery,
    endpoints.COURSE_MEMBERS_ENDPOINT: CourseMemberQuery,
    endpoints.COURSE_ROLES_ENDPOINT: CourseRoleQuery,
    endpoints.USERS_ENDPOINT: UserQuery,
    endpoints.RESULTS_ENDPOINT: ResultQuery,
}


def GET_QUERY_CLASS(table: str):
    """Map an endpoint name to its Query class."""
    try:
        return _QUERY_CLASSES[table]
    except KeyError:
        raise Exception("Not found")


def handle_api_exceptions(func):
  def wrapper(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except ConnectError as e:
      click.echo(f"Connection to [{click.style(kwargs['auth'].api_url,fg='red')}] could not be established.")
    except HTTPStatusError as e:
      # httpx HTTPStatusError has response.status_code and response.json()
      try:
        error_detail = e.response.json()
        message = error_detail.get("detail", str(error_detail))
      except:
        message = e.response.text or str(e)
      click.echo(f"[{click.style(str(e.response.status_code),fg='red')}] {message}")
    except ComputorClientError as e:
      # Typed errors raised by the sync facade / async endpoint clients carry
      # the status code + server detail directly.
      status = e.status_code or 500
      message = e.args[0] if e.args else str(e)
      click.echo(f"[{click.style(str(status),fg='red')}] {message}")
    except Exception as e:
      click.echo(f"[{click.style('500',fg='red')}] {e.args if e.args != () else 'Internal Server Error'}")

  return wrapper

@click.command()
@click.argument("table", type=click.Choice(AVAILABLE_DTO_DEFINITIONS))
@click.option("--query", "-q", "query", type=(str, str), multiple=True)
@authenticate
@handle_api_exceptions
def list_entities(table, query, auth: CLIAuthConfig):

  client = run_async(get_computor_client(auth))

  params = None
  query = dict(query)
  if dict(query) != {}:
    params = GET_QUERY_CLASS(table)(**query)

  resp = run_async(GET_CLIENT_ATTRIBUTE(client, table).list(params))

  for entity in resp:
    # Handle both dict and Pydantic model responses
    if hasattr(entity, 'model_dump_json'):
      click.echo(f"{entity.model_dump_json(indent=4)}")
    else:
      import json
      click.echo(json.dumps(entity, indent=4))

@click.command()
@click.argument("table", type=click.Choice(AVAILABLE_DTO_DEFINITIONS))
def show_entities_query(table):

  query_class = GET_QUERY_CLASS(table)

  query_fields = query_class.model_fields

  click.echo(f"Query parameters for endpoint [{click.style(table,fg='green')}]:\n")
  for field, info in query_fields.items():
    click.echo(f"{click.style(field,fg='green')} - {info.annotation}")

@click.command()
@click.argument("table", type=click.Choice(AVAILABLE_DTO_DEFINITIONS))
@click.argument("id")
@authenticate
@handle_api_exceptions
def get_entity(table, id, auth: CLIAuthConfig):

  client = run_async(get_computor_client(auth))

  entity = run_async(GET_CLIENT_ATTRIBUTE(client, table).get(id))

  # Handle both dict and Pydantic model responses
  if hasattr(entity, 'model_dump_json'):
    click.echo(f"{entity.model_dump_json(indent=4)}")
  else:
    import json
    click.echo(json.dumps(entity, indent=4))

@click.group()
def rest():
    """List, get, and query API entities."""
    pass

rest.add_command(list_entities,"list")
rest.add_command(show_entities_query,"query")
rest.add_command(get_entity,"get")