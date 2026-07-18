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
