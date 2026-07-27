# Bash (ttyd) terminal workspace. See README.md for the template contract.
# This directory is split across several .tf files (Terraform loads them all):
#   versions.tf   - required_providers + docker provider
#   variables.tf  - input variables
#   agent.tf      - coder_agent (+ startup.sh.tftpl)
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
  # /home/coder, so files and user-space installs follow the user across
  # workspaces. The volume is deliberately NOT a Terraform resource — the docker
  # engine auto-creates it on first mount, and because Terraform never owns it,
  # deleting a workspace can never destroy the user's home.
  # A "scratch" workspace instead mounts a throwaway per-WORKSPACE volume that
  # Terraform DOES own (see container.tf): it survives stop/start but is
  # destroyed together with the workspace.
  home_volume_name = (
    data.coder_parameter.home_mode.value == "scratch"
    ? "coder-scratch-${data.coder_workspace.me.id}"
    : "coder-home-${data.coder_workspace_owner.me.id}"
  )
}

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


# Home volume mode. "shared" mounts the per-user home volume (the default);
# "scratch" mounts a throwaway per-workspace volume that Terraform owns (see
# container.tf). Immutable: a workspace cannot switch homes after creation.
data "coder_parameter" "home_mode" {
  name         = "home_mode"
  type         = "string"
  description  = "Home volume: 'shared' = per-user home; 'scratch' = throwaway per-workspace volume deleted with the workspace"
  mutable      = false
  default      = "shared"
  display_name = "Home Mode"
  order        = 101
  option {
    name  = "Shared home"
    value = "shared"
  }
  option {
    name  = "Throwaway (scratch)"
    value = "scratch"
  }
}

# Course-level narrowing of the template's root/internet policy, delivered as
# rich parameters at provision time. The default "true" means "no course-level
# restriction" — the effective value is ANDed with the template variable in the
# locals below, so a parameter can only ever take access away, never grant it.
# Immutable: a running workspace's policy cannot be flipped by a rebuild.
data "coder_parameter" "allow_root" {
  name         = "allow_root"
  type         = "bool"
  description  = "Course-level root policy; ANDed with the template's allow_root variable"
  mutable      = false
  default      = "true"
  display_name = "Root Access"
  order        = 102
}

data "coder_parameter" "allow_internet" {
  name         = "allow_internet"
  type         = "bool"
  description  = "Course-level internet policy; ANDed with the template's allow_internet variable"
  mutable      = false
  default      = "true"
  display_name = "Internet Access"
  order        = 103
}

locals {
  # Template variable is the ceiling, course parameter narrows it. Resolved here
  # rather than in the backend so that a rich parameter — which is per workspace
  # and therefore the weaker of the two inputs — can never widen access beyond
  # what the template allows. coder_parameter.value is always a string.
  root_enabled     = var.allow_root && tobool(data.coder_parameter.allow_root.value)
  internet_enabled = var.allow_internet && tobool(data.coder_parameter.allow_internet.value)

  # Exactly ONE network: attaching both would restore egress through the
  # non-internal one (see docker-compose.coder.yaml).
  ws_net = local.internet_enabled ? var.docker_network : var.docker_network_offline
}

# Per-USER credential the workspace app requires and the ingress injects, so a
# workspace cannot be driven directly by another workspace on the shared bridge
# (the apps bind 0.0.0.0 and container names are predictable). Per user rather
# than per workspace because /home/coder is shared across a user's workspaces —
# a per-workspace value would make two running desktops fight over
# ~/.kasmpasswd. Empty leaves the app unauthenticated.
data "coder_parameter" "workspace_app_secret" {
  name         = "workspace_app_secret"
  type         = "string"
  description  = "Per-user credential required by this workspace's app"
  mutable      = true
  default      = ""
  display_name = "Workspace App Secret"
  order        = 104
}

# Argon2id hash of the same secret, for the code-server templates: code-server
# compares its session cookie against HASHED_PASSWORD, so handing it the hash
# lets the ingress inject a ready-made session and skip the login page.
data "coder_parameter" "workspace_app_hash" {
  name         = "workspace_app_hash"
  type         = "string"
  description  = "Argon2id hash of the app secret (code-server session cookie)"
  mutable      = true
  default      = ""
  display_name = "Workspace App Secret Hash"
  order        = 105
}

locals {
  app_secret = data.coder_parameter.workspace_app_secret.value
  app_hash   = data.coder_parameter.workspace_app_hash.value
}

# Which course this workspace was provisioned FOR, empty when a user
# provisioned it for themselves. Nothing in Terraform reads it — it is a label
# the backend queries back, because otherwise "is this workspace part of course
# X" can only be inferred from (owner is a member) x (template is allowed),
# which also matches a member's personal workspace on a course template. The
# course views scope listing and deletion on this.
data "coder_parameter" "course_id" {
  name         = "course_id"
  type         = "string"
  description  = "Course this workspace was provisioned for (empty = personal)"
  mutable      = false
  default      = ""
  display_name = "Course"
  order        = 106
}
