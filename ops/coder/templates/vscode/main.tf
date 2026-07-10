terraform {
  required_providers {
    coder = {
      source = "coder/coder"
    }
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

###########################
# VARIABLES
###########################

variable "docker_socket" {
  default     = ""
  description = "(Optional) Docker socket URI"
  type        = string
}

variable "code_server_port" {
  default     = 13337
  description = "Port for code-server"
  type        = number
}

variable "workspace_image" {
  default     = "localhost:5000/computor-workspace-vscode:latest"
  description = "Pre-built workspace image from local registry"
  type        = string
}

variable "coder_internal_url" {
  default     = "coder:7080"
  description = "Internal URL for Coder server (Docker network)"
  type        = string
}

variable "docker_network" {
  default     = "computor-coder-workspaces"
  description = "Isolated Docker network for workspace containers. Kept off computor-network so untrusted workspaces (the user has sudo) cannot reach platform services; Traefik and Coder are dual-homed onto it. Must match the traefik.docker.network label below."
  type        = string
}

variable "coder_base_path" {
  default     = "/coder"
  description = "Base path prefix for code-server access via Traefik"
  type        = string
}

variable "computor_backend_url" {
  description = "External backend URL for Computor extension (set via template deployment based on DEBUG_MODE)"
  type        = string
}

variable "computor_backend_internal" {
  description = "Internal backend service URL for ForwardAuth (Docker network). Set via template deployment based on DEBUG_MODE: 'http://host.docker.internal:8000' in dev, 'http://uvicorn:8000' in prod."
  type        = string
}

variable "code_server_password" {
  default     = ""
  description = "Password for code-server access (empty = no password required)"
  type        = string
  sensitive   = true
}

variable "dev_forward_ports" {
  default     = ""
  description = "Comma-separated localhost ports to forward to host.docker.internal (dev only, empty = disabled)"
  type        = string
}

variable "memory_mb" {
  default     = 0
  description = "Workspace memory cap in MiB. 0 = unlimited; set per host capacity to bound RAM use."
  type        = number
}

variable "cpu_shares" {
  default     = 0
  description = "Relative CPU weight under contention (Docker default 1024). 0 = Docker default."
  type        = number
}

# NOTE: computor_auth_token is now defined as a coder_parameter below
# to allow per-workspace values via rich_parameter_values API

###########################
# DATA SOURCES
###########################

locals {
  username = data.coder_workspace_owner.me.name
}

data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

# Per-workspace parameter for Computor API token (set via rich_parameter_values)
data "coder_parameter" "computor_auth_token" {
  name         = "computor_auth_token"
  type         = "string"
  description  = "Pre-minted API token for automatic VSCode extension authentication"
  mutable      = true
  default      = ""
  display_name = "Computor Auth Token"
  order        = 100
}

###########################
# PROVIDERS
###########################

provider "docker" {
  host = var.docker_socket != "" ? var.docker_socket : null
}

###########################
# CODER AGENT
###########################

resource "coder_agent" "main" {
  arch = data.coder_provisioner.me.arch
  os   = "linux"

  startup_script = <<-EOT
    set -e

    # Dev mode: forward localhost ports to host machine via socat
    %{ if var.dev_forward_ports != "" }
    for port in $(echo "${var.dev_forward_ports}" | tr ',' ' '); do
      echo "Forwarding localhost:$port -> host.docker.internal:$port"
      socat TCP-LISTEN:$port,fork,reuseaddr TCP:host.docker.internal:$port &
    done
    %{ endif }

    # Initialize home directory from skeleton if first run
    if [ ! -f ~/.init_done ]; then
      cp -rT /etc/skel ~
      touch ~/.init_done
    fi

    # Configure git with user info
    git config --global user.name "${coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)}"
    git config --global user.email "${data.coder_workspace_owner.me.email}"

    # Create default workspace folder
    mkdir -p ~/workspace

    # Create Computor extension config directory and file
    mkdir -p ~/.computor
    cat > ~/.computor/config.json << COMPUTOR_EOF
{
  "version": "1.0.0",
  "authentication": {
    "baseUrl": "${var.computor_backend_url}",
    "autoLogin": true
  }
}
COMPUTOR_EOF

    # Create workspace marker file (triggers extension activation)
    touch ~/workspace/.computor

    # User personalization hook: with the shared per-user home, apt-installed
    # software is per-workspace and lost on rebuild — users can re-apply such
    # setup in an executable ~/personalize script.
    if [ -x "$HOME/personalize" ]; then
      "$HOME/personalize" >/tmp/personalize.log 2>&1 || true
    fi

    # Start code-server in background
    # Configure abs-proxy-base-path for Traefik routing at /coder prefix
    # Bind to 0.0.0.0 so Traefik can reach it from outside the container
    # Use password auth if password is provided, otherwise no auth
    # The home is shared across the user's workspaces, so code-server state
    # (open editors, machine settings) is scoped per workspace via user-data-dir
    %{ if var.code_server_password != "" }
    export PASSWORD="${var.code_server_password}"
    code-server \
      --auth password \
      --bind-addr 0.0.0.0:${var.code_server_port} \
      --abs-proxy-base-path "${var.coder_base_path}/${data.coder_workspace_owner.me.name}/${data.coder_workspace.me.name}" \
      --extensions-dir /opt/code-server/extensions \
      --user-data-dir "/home/coder/.local/share/code-server-${lower(data.coder_workspace.me.name)}" \
      /home/coder/workspace \
      >/tmp/code-server.log 2>&1 &
    %{ else }
    code-server \
      --auth none \
      --bind-addr 0.0.0.0:${var.code_server_port} \
      --abs-proxy-base-path "${var.coder_base_path}/${data.coder_workspace_owner.me.name}/${data.coder_workspace.me.name}" \
      --extensions-dir /opt/code-server/extensions \
      --user-data-dir "/home/coder/.local/share/code-server-${lower(data.coder_workspace.me.name)}" \
      /home/coder/workspace \
      >/tmp/code-server.log 2>&1 &
    %{ endif }
  EOT

  env = {
    GIT_AUTHOR_NAME     = coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)
    GIT_AUTHOR_EMAIL    = data.coder_workspace_owner.me.email
    GIT_COMMITTER_NAME  = coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)
    GIT_COMMITTER_EMAIL = data.coder_workspace_owner.me.email
    COMPUTOR_AUTH_TOKEN = data.coder_parameter.computor_auth_token.value
  }

  # Metadata blocks for workspace monitoring
  metadata {
    display_name = "CPU Usage"
    key          = "0_cpu_usage"
    script       = "coder stat cpu"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "RAM Usage"
    key          = "1_ram_usage"
    script       = "coder stat mem"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "Disk Usage"
    key          = "2_disk_usage"
    script       = "coder stat disk --path /home/coder"
    interval     = 60
    timeout      = 1
  }
}

###########################
# MODULES
###########################

# NOTE: code-server is started manually in the startup_script above
# to support --abs-proxy-base-path for Traefik routing at /coder/{user}/{workspace}
# Do NOT add the code-server module here as it will conflict (EADDRINUSE)

# JetBrains Gateway
module "jetbrains" {
  count      = data.coder_workspace.me.start_count
  source     = "registry.coder.com/coder/jetbrains/coder"
  version    = "~> 1.1"
  agent_id   = coder_agent.main.id
  agent_name = "main"
  folder     = "/home/coder"
}

###########################
# DOCKER RESOURCES
###########################

# Shared per-USER home volume: every workspace of a user mounts the same
# /home/coder, so files and user-space installs (pip --user, venvs, npm, ...)
# follow the user across workspaces. The volume is deliberately NOT a
# Terraform resource — the docker engine auto-creates it on first mount, and
# because Terraform never owns it, deleting a workspace can never destroy the
# user's home. System (apt) packages live in the image/container rootfs and
# are NOT shared or persisted.
locals {
  home_volume_name = "coder-home-${data.coder_workspace_owner.me.id}"
}

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
  # The init script contains URLs like http://localhost/bin/...
  # We need to replace with http://coder:7080/bin/...
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

  # Connect to the same network as Coder services
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

  # Traefik labels for direct code-server access at /coder/{username}/{workspace}
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
    value = "${var.code_server_port}"
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
