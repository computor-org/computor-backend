data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

locals {
  home_volume_name = "coder-home-${data.coder_workspace_owner.me.id}"
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

data "coder_parameter" "matlab_license_file" {
  name         = "matlab_license_file"
  type         = "string"
  description  = "Optional MATLAB license manager (port@host) or an in-container license file path. Leave empty to sign in with a MathWorks account."
  mutable      = true
  default      = ""
  display_name = "MATLAB License"
  form_type    = "input"
  order        = 110
  styling = jsonencode({
    mask_input  = true
    placeholder = "27000@license-server"
  })
}
