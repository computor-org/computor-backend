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

resource "docker_container" "workspace" {
  count      = data.coder_workspace.me.start_count
  depends_on = [docker_volume.scratch_home]
  image      = docker_image.workspace_image.name
  name       = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  hostname   = data.coder_workspace.me.name

  memory     = var.memory_mb
  cpu_shares = var.cpu_shares
  shm_size   = var.shm_size

  # Root policy (see allow_root). no-new-privileges makes the kernel refuse the
  # setuid transition in sudo/su, so the same image serves both modes and there
  # is no root-less image variant to maintain. Fixed for the container's life —
  # changing the policy replaces the container.
  security_opts = local.root_enabled ? [] : ["no-new-privileges:true"]

  entrypoint = [
    "sh", "-c",
    replace(
      replace(coder_agent.main.init_script, "localhost", "coder"),
      "http://coder/", "http://${var.coder_internal_url}/"
    )
  ]

  env = concat(
    ["CODER_AGENT_TOKEN=${coder_agent.main.token}"],
    var.matlab_license_file != "" ? ["MLM_LICENSE_FILE=${var.matlab_license_file}"] : []
  )

  dynamic "host" {
    for_each = length(regexall("host.docker.internal", var.computor_backend_internal)) > 0 ? [1] : []
    content {
      host = "host.docker.internal"
      ip   = "host-gateway"
    }
  }

  networks_advanced {
    name = local.ws_net
  }

  volumes {
    container_path = "/home/coder"
    volume_name    = local.home_volume_name
    read_only      = false
  }

  # Routed by workspace-ingress, not the main Traefik: this label is what each
  # proxy's docker-provider constraint selects on (see docker-compose.coder.yaml).
  labels {
    label = "computor.ingress"
    value = "workspace"
  }

  labels {
    label = "coder.owner"
    value = data.coder_workspace_owner.me.name
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
  labels {
    label = "traefik.enable"
    value = "true"
  }
  labels {
    label = "traefik.docker.network"
    value = local.ws_net
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
    value = var.matlab_proxy_port
  }
  # Injects the per-user app credential (matlab-proxy takes its token in the mwi-auth-token header), so a request reaching the app
  # WITHOUT passing through this proxy — another workspace dialling the
  # container directly — carries no credential and is refused. An empty value
  # removes the header: the unauthenticated fallback when no secret was issued.
  labels {
    label = "traefik.http.middlewares.appauth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.headers.customrequestheaders.mwi-auth-token"
    value = local.app_secret
  }

  labels {
    label = "traefik.http.middlewares.auth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.forwardauth.address"
    value = "${var.computor_backend_internal}/auth/verify-coder-access"
  }
  labels {
    label = "traefik.http.middlewares.auth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.forwardauth.authResponseHeaders"
    value = "X-Auth-User"
  }
  labels {
    label = "traefik.http.routers.coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.middlewares"
    value = "auth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)},appauth-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  }
}
