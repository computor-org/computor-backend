###########################
# DOCKER RESOURCES
###########################

# Use pre-built image from local registry (no build required)
resource "docker_image" "workspace_image" {
  name         = var.workspace_image
  keep_locally = true
}

# Throwaway home volume for scratch-mode workspaces. Unlike the shared home
# (never a Terraform resource, so a workspace delete can't touch it), the
# scratch volume IS Terraform-owned: it survives stop/start (not gated on
# start_count) and is destroyed together with the workspace. Created before
# the container mounts it by name, so docker's auto-create can't race it.
resource "docker_volume" "scratch_home" {
  count = data.coder_parameter.home_mode.value == "scratch" ? 1 : 0
  name  = "coder-scratch-${data.coder_workspace.me.id}"
}

# Workspace container
resource "docker_container" "workspace" {
  count      = data.coder_workspace.me.start_count
  depends_on = [docker_volume.scratch_home]
  image      = docker_image.workspace_image.name
  name       = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  hostname   = data.coder_workspace.me.name

  # Resource limits so one workspace cannot exhaust the host. Opt-in caps
  # (0 = unlimited/default) — set per host capacity. NOTE: the docker provider
  # exposes no per-container pids_limit; use dockerd --default-pids-limit for a
  # host-wide fork-bomb guard.
  memory     = var.memory_mb
  cpu_shares = var.cpu_shares

  # Fix for agent connection: replace localhost URLs with internal Coder URL
  entrypoint = [
    "sh", "-c",
    replace(
      replace(coder_agent.main.init_script, "localhost", "coder"),
      "http://coder/", "http://${var.coder_internal_url}/"
    )
  ]

  env = ["CODER_AGENT_TOKEN=${coder_agent.main.token}"]

  # Host-gateway route to the host machine. Only needed in DEV, where the
  # backend runs on the host (host.docker.internal) and dev port-forwarding
  # targets it. In PROD the backend is the `uvicorn` container, so this route
  # would only needlessly expose the host (SSH, host-run services) to the
  # workspace — omit it. `computor_backend_internal` is host.docker.internal in
  # dev and uvicorn in prod: a reliable signal.
  dynamic "host" {
    for_each = length(regexall("host.docker.internal", var.computor_backend_internal)) > 0 ? [1] : []
    content {
      host = "host.docker.internal"
      ip   = "host-gateway"
    }
  }

  # Connect to the isolated workspace network (see variables.tf docker_network)
  networks_advanced {
    name = var.docker_network
  }

  volumes {
    container_path = "/home/coder"
    volume_name    = local.home_volume_name
    read_only      = false
  }

  labels {
    label = "coder.owner"
    value = data.coder_workspace_owner.me.name
  }

  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }

  # Traefik labels for JupyterLab access at /coder/{username}/{workspace}
  labels {
    label = "traefik.enable"
    value = "true"
  }

  # Route to this container on the isolated workspace network, overriding
  # Traefik's global --providers.docker.network pin (computor-network).
  labels {
    label = "traefik.docker.network"
    value = var.docker_network
  }

  labels {
    label = "traefik.http.routers.coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.rule"
    value = "PathPrefix(`${var.coder_base_path}/${data.coder_workspace_owner.me.name}/${data.coder_workspace.me.name}`)"
  }

  labels {
    label = "traefik.http.routers.coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.entrypoints"
    value = "web"
  }

  labels {
    label = "traefik.http.services.coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.loadbalancer.server.port"
    value = var.jupyter_port
  }

  # NOTE: no stripprefix middleware. JupyterLab is started with
  # --ServerApp.base_url set to the full /coder/{owner}/{workspace} path and
  # serves all of its assets, REST API and kernel websockets under it, so the
  # prefix must reach the container intact (unlike ttyd/KasmVNC/code-server).

  # ForwardAuth middleware - verify user authentication before allowing access
  labels {
    label = "traefik.http.middlewares.auth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.forwardauth.address"
    value = "${var.computor_backend_internal}/auth/verify-coder-access"
  }

  labels {
    label = "traefik.http.middlewares.auth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.forwardauth.authResponseHeaders"
    value = "X-Auth-User"
  }

  # Authentication middleware only (no strip-prefix — see note above)
  labels {
    label = "traefik.http.routers.coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.middlewares"
    value = "auth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  }
}
