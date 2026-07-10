###########################
# CODER AGENT
###########################

resource "coder_agent" "main" {
  arch = data.coder_provisioner.me.arch
  os   = "linux"

  # The startup script lives in startup.sh.tftpl; values it needs are passed
  # here as the templatefile vars map (Terraform interpolation, ${...}). Bash
  # variables in the script use the single-$ form ($HOME, $port) so they pass
  # through untouched.
  startup_script = templatefile("${path.module}/startup.sh.tftpl", {
    dev_forward_ports    = var.dev_forward_ports
    full_name            = coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)
    email                = data.coder_workspace_owner.me.email
    computor_backend_url = var.computor_backend_url
    code_server_password = var.code_server_password
    code_server_port     = var.code_server_port
    coder_base_path      = var.coder_base_path
    owner_name           = data.coder_workspace_owner.me.name
    workspace_name       = data.coder_workspace.me.name
    workspace_name_lower = lower(data.coder_workspace.me.name)
  })

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

# NOTE: code-server is started manually in the startup script (templatefile
# above) to support --abs-proxy-base-path for Traefik routing at
# /coder/{user}/{workspace}. Do NOT add the code-server module here — it will
# conflict (EADDRINUSE).

# JetBrains Gateway
module "jetbrains" {
  count      = data.coder_workspace.me.start_count
  source     = "registry.coder.com/coder/jetbrains/coder"
  version    = "~> 1.1"
  agent_id   = coder_agent.main.id
  agent_name = "main"
  folder     = "/home/coder"
}
