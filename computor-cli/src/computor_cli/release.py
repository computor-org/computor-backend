import time
import click
from computor_backend.api.system import ReleaseCourseCreate
from computor_cli.auth import authenticate
from computor_cli.config import CLIAuthConfig
from computor_backend.client.crud_client import CustomClient
from computor_types.deployments import DeploymentFactory
from computor_types.deployments import ComputorDeploymentConfig
from alive_progress import alive_bar

def handle_flow_runs(flow_run_id: str, custom_client: CustomClient, title: str = "Flow run"):

    # click.echo(f"Flow run with id [{click.style(flow_run_id,fg='green')}] started")

    with alive_bar(title=title,monitor=None, stats=None,spinner='twirls') as bar:

      bar.text(f"[scheduled]")

      start_time = time.time()

      status = "SCHEDULED"
      for i in range(30000):
        time.sleep(0.1)
        
        elapsed_time = time.time() - start_time

        if elapsed_time > 4:

          start_time = time.time()
          elapsed_time = 0

          try:
            response = custom_client.get(f"system/status/{flow_run_id}")
          except Exception as e:
              click.echo(e)
              return
          
          status = response["status"]

          bar.text(f"[{status}]")

          if status == "FAILED" or status == "COMPLETED" or status == "CRASHED" or status == "CANCELLED":
             break
        
        bar()
      
      if status == "COMPLETED":
        click.echo(f"[{click.style('COMPLETED',fg='green')}]")

      elif status == "FAILED" or status == "CRASHED":
        click.echo(f"[{click.style('FAILED',fg='red')}]")

      click.echo(response.get("message"))
      return True

        # if response["status"] == "SCHEDULED":
        #   bar.text("[SCHEDULED]")
        #   #click.echo(f"[{click.style('scheduled',fg='yellow')}]",nl=False)
        #   # time.sleep(4)
        # elif response["status"] == "PENDING":
        #   bar.text("[PENDING]")
        #   #click.echo(f"[{click.style('pending',fg='white')}]",nl=False)
        #   # time.sleep(4)
        # elif response["status"] == "RUNNING":
        #   bar.text("[RUNNING]")
        #   #click.echo(f"[{click.style('running',fg='blue')}]",nl=False)
        #   # time.sleep(2)
        # elif response["status"] == "FAILED":
        #   bar.text("[FAILED]")
        #   click.echo(f"[{click.style('FAILED',fg='red')}]",nl=False)
        #   click.echo(response.get("message"))
        #   return False
        # elif response["status"] == "COMPLETED":
        #   bar.text("[COMPLETED]")
        #   click.echo(f"[{click.style('COMPLETED',fg='green')}]",nl=False)
        #   click.echo(response.get("message"))
        #   return True


# @click.command()
# @click.option("--course-id", "-c", prompt="Course Id")
# @click.option("--descendants", "-d", prompt="Descendants", prompt_required=False, default=False)
# @authenticate
# def release_course(course_id, descendants, auth: CLIAuthConfig):

#     from computor_backend.api.system import ReleaseCourseCreate

#     if auth.basic != None:
#       custom_client = CustomClient(url_base=auth.api_url,auth=(auth.basic.username,auth.basic.password))
#     elif auth.gitlab != None:
#       custom_client = CustomClient(url_base=auth.api_url,glp_auth_header=auth.gitlab.model_dump())
#     else:
#       raise Exception("Not implemented yet")
    
#     try:
#       resp = custom_client.create("/system/release/courses", ReleaseCourseCreate(descendants=descendants,course_id=course_id).model_dump())
#     except Exception as e:
#       click.echo(e)
#       return

#     flow_run_id = resp["flow_run_id"]

#     handle_flow_runs(flow_run_id, custom_client)

# @click.command()
# @click.option("--course-id", "-c", prompt="Course Id")
# @click.option("--descendants", "-d", prompt="Descendants", prompt_required=False, default=False)
# @click.option("--ascendants", "-a", prompt="Ascendants", prompt_required=False, default=False)
# @click.option("--directory", "-r", prompt="Release directory", prompt_required=False, default=None)
# @authenticate
# def release_course_content(course_id, descendants, ascendants, directory, auth: CLIAuthConfig):

#     from computor_backend.api.system import ReleaseCourseContentCreate

#     if auth.basic != None:
#       custom_client = CustomClient(url_base=auth.api_url,auth=(auth.basic.username,auth.basic.password))
#     elif auth.gitlab != None:
#       custom_client = CustomClient(url_base=auth.api_url,glp_auth_header=auth.gitlab.model_dump())
#     else:
#       raise Exception("Not implemented yet")

#     try:
#       resp = custom_client.create("/system/release/course-contents", ReleaseCourseContentCreate(release_dir=directory,ascendants=ascendants,descendants=descendants,course_id=course_id).model_dump())
#     except Exception as e:
#       click.echo(e)
#       return

#     flow_run_id = resp["flow_run_id"]

#     handle_flow_runs(flow_run_id, custom_client)

# @click.command()
# @click.option("--user-id", "-u", prompt="User Id")
# @click.option("--course-id", "-c", prompt="Course Id")
# @click.option("--course-group-title", "-g", prompt="Course group Title")
# @authenticate
# def release_student(user_id, course_id, course_group_title, auth: CLIAuthConfig):

#     from computor_backend.api.system import StudentCreate

#     if auth.basic != None:
#       custom_client = CustomClient(url_base=auth.api_url,auth=(auth.basic.username,auth.basic.password))
#     elif auth.gitlab != None:
#       custom_client = CustomClient(url_base=auth.api_url,glp_auth_header=auth.gitlab.model_dump())
#     else:
#       raise Exception("Not implemented yet")

#     try:
#       resp = custom_client.create("/system/release/students", StudentCreate(user_id=user_id,course_id=course_id,course_group_title=course_group_title).model_dump())
#     except Exception as e:
#       click.echo(e)
#       return

#     flow_run_id = resp["flow_run_id"]
    
#     handle_flow_runs(flow_run_id, custom_client)

# @click.command()
# @click.option("--file", "-f", prompt="Directory")
# @click.option("--descendants", "-d", prompt="Descendants", prompt_required=False, default=False)
# @authenticate
# def release_deployment(file, descendants, auth: CLIAuthConfig):

#     deployment: ComputorDeploymentConfig = DeploymentFactory.read_deployment_from_file(ComputorDeploymentConfig,file)

#     if auth.basic != None:
#       custom_client = CustomClient(url_base=auth.api_url,auth=(auth.basic.username,auth.basic.password))
#     elif auth.gitlab != None:
#       custom_client = CustomClient(url_base=auth.api_url,glp_auth_header=auth.gitlab.model_dump())
#     else:
#       raise Exception("Not implemented yet")

#     try:
#       resp = custom_client.create("/system/release/courses", ReleaseCourseCreate(descendants=descendants,deployment=deployment).model_dump())
#     except Exception as e:
#       click.echo(e)
#       return

#     flow_run_id = resp["flow_run_id"]

#     handle_flow_runs(flow_run_id, custom_client, f"Applied deployment, flow run started [{flow_run_id}]")

# @click.group()
# def release():
#     pass

# release.add_command(release_course,"course")
# release.add_command(release_course_content,"content")
# release.add_command(release_student,"student")
# release.add_command(release_deployment,"apply")