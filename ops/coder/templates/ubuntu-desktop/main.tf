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

variable "kasmvnc_port" {
  default     = 6901
  description = "Port for the KasmVNC web desktop"
  type        = number
}

variable "workspace_image" {
  default     = "localhost:5000/computor-workspace-ubuntu-desktop:latest"
  description = "Pre-built workspace image from local registry"
  type        = string
}

variable "coder_internal_url" {
  default     = "coder:7080"
  description = "Internal URL for Coder server (Docker network)"
  type        = string
}

variable "docker_network" {
  default     = "computor-network"
  description = "Docker network for workspace containers (must match Traefik network)"
  type        = string
}

variable "coder_base_path" {
  default     = "/coder"
  description = "Base path prefix for workspace access via Traefik"
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

variable "dev_forward_ports" {
  default     = ""
  description = "Comma-separated localhost ports to forward to host.docker.internal (dev only, empty = disabled)"
  type        = string
}

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
  description  = "Pre-minted API token for automatic Computor authentication"
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

    # User personalization hook: with the shared per-user home, apt-installed
    # software is per-workspace and lost on rebuild — users can re-apply such
    # setup in an executable ~/personalize script.
    if [ -x "$HOME/personalize" ]; then
      "$HOME/personalize" >/tmp/personalize.log 2>&1 || true
    fi

    # Configure KasmVNC: plain HTTP websocket transport on all interfaces —
    # TLS and authentication are Traefik's job (ForwardAuth in front of the
    # workspace, same as every other workspace type).
    mkdir -p "$HOME/.vnc"
    cat > "$HOME/.vnc/kasmvnc.yaml" << KASM_EOF
network:
  protocol: http
  interface: 0.0.0.0
  websocket_port: ${var.kasmvnc_port}
  ssl:
    require_ssl: false
    pem_certificate:
    pem_key:
  udp:
    public_ip: 127.0.0.1
KASM_EOF

    # Start the XFCE desktop served by KasmVNC's built-in web server.
    # Traefik strips the /coder/{user}/{workspace} prefix; the KasmVNC web
    # client uses relative asset/websocket URLs, which resolve correctly as
    # long as the workspace URL ends with a trailing slash.
    vncserver -kill :1 >/dev/null 2>&1 || true
    vncserver :1 \
      -select-de xfce \
      -disableBasicAuth \
      >/tmp/kasmvnc.log 2>&1
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
# DOCKER RESOURCES
###########################

# Shared per-USER home volume: every workspace of a user mounts the same
# /home/coder, so files and user-space installs follow the user across
# workspaces. The volume is deliberately NOT a Terraform resource — the docker
# engine auto-creates it on first mount, and because Terraform never owns it,
# deleting a workspace can never destroy the user's home.
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

  # Fix for agent connection: replace localhost URLs with internal Coder URL
  entrypoint = [
    "sh", "-c",
    replace(
      replace(coder_agent.main.init_script, "localhost", "coder"),
      "http://coder/", "http://${var.coder_internal_url}/"
    )
  ]

  env = ["CODER_AGENT_TOKEN=${coder_agent.main.token}"]

  # Allow container to reach host machine (for development)
  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
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

  # Traefik labels for terminal access at /coder/{username}/{workspace}
  labels {
    label = "traefik.enable"
    value = "true"
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
    value = "${var.kasmvnc_port}"
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
