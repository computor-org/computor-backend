# VS Code (code-server) workspace. See README.md for the template contract.
# This directory is split across several .tf files (Terraform loads them all):
#   versions.tf   - required_providers + docker provider
#   variables.tf  - input variables
#   agent.tf      - coder_agent (+ startup.sh.tftpl) and IDE modules
#   container.tf  - docker image + workspace container + Traefik labels
#   main.tf       - data sources, locals, coder_parameter (this file)

###########################
# DATA SOURCES & LOCALS
###########################

data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

locals {
  username = data.coder_workspace_owner.me.name

  # Shared per-USER home volume: every workspace of a user mounts the same
  # /home/coder, so files and user-space installs (pip --user, venvs, npm, ...)
  # follow the user across workspaces. The volume is deliberately NOT a
  # Terraform resource — the docker engine auto-creates it on first mount, and
  # because Terraform never owns it, deleting a workspace can never destroy the
  # user's home. System (apt) packages live in the image/container rootfs and
  # are NOT shared or persisted.
  home_volume_name = "coder-home-${data.coder_workspace_owner.me.id}"
}

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
