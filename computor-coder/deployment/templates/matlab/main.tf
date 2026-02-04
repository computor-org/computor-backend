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
  default     = "localhost:5000/computor-workspace-matlab:latest"
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
  description = "Base path prefix for code-server access via Traefik"
  type        = string
}

variable "computor_backend_url" {
  default     = "https://computor.itp.tugraz.at/api"
  description = "Backend URL for Computor extension"
  type        = string
}

variable "code_server_password" {
  default     = ""
  description = "Password for code-server access (empty = no password required)"
  type        = string
  sensitive   = true
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

    # Start code-server in background
    # Configure abs-proxy-base-path for Traefik routing at /coder prefix
    # Bind to 0.0.0.0 so Traefik can reach it from outside the container
    # Use password auth if password is provided, otherwise no auth
    %{ if var.code_server_password != "" }
    export PASSWORD="${var.code_server_password}"
    code-server \
      --auth password \
      --bind-addr 0.0.0.0:${var.code_server_port} \
      --abs-proxy-base-path "${var.coder_base_path}/${data.coder_workspace_owner.me.name}/${data.coder_workspace.me.name}" \
      --extensions-dir /opt/code-server/extensions \
      >/tmp/code-server.log 2>&1 &
    %{ else }
    code-server \
      --auth none \
      --bind-addr 0.0.0.0:${var.code_server_port} \
      --abs-proxy-base-path "${var.coder_base_path}/${data.coder_workspace_owner.me.name}/${data.coder_workspace.me.name}" \
      --extensions-dir /opt/code-server/extensions \
      >/tmp/code-server.log 2>&1 &
    %{ endif }
  EOT

  env = {
    GIT_AUTHOR_NAME     = coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)
    GIT_AUTHOR_EMAIL    = data.coder_workspace_owner.me.email
    GIT_COMMITTER_NAME  = coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)
    GIT_COMMITTER_EMAIL = data.coder_workspace_owner.me.email
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
    script       = "coder stat disk --path /home/matlab"
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
  folder     = "/home/matlab"
}

###########################
# DOCKER RESOURCES
###########################

# Persistent volume for home directory
resource "docker_volume" "home_volume" {
  name = "coder-${data.coder_workspace.me.id}-home"

  lifecycle {
    ignore_changes = all
  }

  labels {
    label = "coder.owner"
    value = data.coder_workspace_owner.me.name
  }

  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
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

  # Connect to the same network as Coder services
  networks_advanced {
    name = var.docker_network
  }

  volumes {
    container_path = "/home/matlab"
    volume_name    = docker_volume.home_volume.name
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

  labels {
    label = "traefik.http.routers.coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}.middlewares"
    value = "strip-coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  }
}
