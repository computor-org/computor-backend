data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

locals {
  # A "scratch" workspace instead mounts a throwaway per-WORKSPACE volume that
  # Terraform DOES own (see container.tf): it survives stop/start but is
  # destroyed together with the workspace.
  home_volume_name = (
    data.coder_parameter.home_mode.value == "scratch"
    ? "coder-scratch-${data.coder_workspace.me.id}"
    : "coder-home-${data.coder_workspace_owner.me.id}"
  )
}

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
