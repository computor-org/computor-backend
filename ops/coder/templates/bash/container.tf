###########################
# DOCKER RESOURCES
###########################

# Use pre-built image from local registry (no build required)
resource "docker_image" "workspace_image" {
  name         = var.workspace_image
  keep_locally = true
}

# Workspace container
resource "docker_container" "workspace" {
  count    = data.coder_workspace.me.start_count
  image    = docker_image.workspace_image.name
  name     = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  hostname = data.coder_workspace.me.name

  # Resource limits so one workspace (whose user has sudo) cannot exhaust the
  # host. Opt-in caps (0 = unlimited/default) — set per host capacity. NOTE: the
  # docker provider exposes no per-container pids_limit; use dockerd
  # --default-pids-limit for a host-wide fork-bomb guard.
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
  # would only needlessly expose the host (SSH, host-run services) to an
  # untrusted workspace that has sudo — omit it. `computor_backend_internal`
  # is host.docker.internal in dev and uvicorn in prod: a reliable signal.
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

  # Traefik labels for terminal access at /coder/{username}/{workspace}
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
    value = var.ttyd_port
  }

  # Middleware to strip the /coder/{username}/{workspace} prefix before forwarding
  labels {
    label = "traefik.http.middlewares.strip-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.stripprefix.prefixes"
    value = "${var.coder_base_path}/${data.coder_workspace_owner.me.name}/${data.coder_workspace.me.name}"
  }

  # ForwardAuth middleware - verify user authentication before allowing access
  labels {
    label = "traefik.http.middlewares.auth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.forwardauth.address"
    value = "${var.computor_backend_internal}/auth/verify-coder-access"
  }

  labels {
    label = "traefik.http.middlewares.auth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.forwardauth.authResponseHeaders"
    value = "X-Auth-User"
  }

  # Chain both authentication and strip-prefix middlewares
  labels {
    label = "traefik.http.routers.coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.middlewares"
    value = "auth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)},strip-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  }
}
