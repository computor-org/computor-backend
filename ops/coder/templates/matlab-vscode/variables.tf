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

variable "matlab_license_file" {
  default     = ""
  description = "MATLAB license (port@host or in-container license path), pushed from the deployment's MATLAB_MLM_LICENSE_FILE env var. Empty falls back to in-browser MathWorks sign-in."
  type        = string
  sensitive   = true
}

variable "workspace_image" {
  default     = "localhost:5000/computor-workspace-matlab-vscode:latest"
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
  description = "Isolated Docker network for workspace containers"
  type        = string
}

variable "coder_base_path" {
  default     = "/coder"
  description = "Base path prefix for code-server access via Traefik"
  type        = string
}

variable "computor_backend_url" {
  description = "External backend URL for Computor extension"
  type        = string
}

variable "computor_backend_internal" {
  description = "Internal backend service URL for ForwardAuth"
  type        = string
}

variable "dev_forward_ports" {
  default     = ""
  description = "Comma-separated localhost ports to forward in development"
  type        = string
}


variable "memory_mb" {
  default     = 0
  description = "Workspace memory cap in MiB; 0 is unlimited"
  type        = number
}

variable "cpu_shares" {
  default     = 0
  description = "Relative CPU weight; 0 uses the Docker default"
  type        = number
}

variable "shm_size" {
  default     = 512
  description = "Size of /dev/shm in MiB (MATLAB needs a larger-than-default shared memory segment)"
  type        = number
}

variable "allow_root" {
  default     = false
  description = "Grant the workspace user root via sudo. When false the container runs with no-new-privileges, so the kernel refuses the setuid transition in sudo/su and ONE image serves both modes. Set per template in the workspace template settings; a course can narrow this further, never widen it."
  type        = bool
}

variable "allow_internet" {
  default     = true
  description = "Allow egress to the internet. When false the workspace is attached to docker_network_offline instead: an internal network with no NAT and no default route, so platform ingress and the Coder agent keep working while external connects fail immediately. Set per template in the workspace template settings; a course can narrow this further, never widen it."
  type        = bool
}

variable "docker_network_offline" {
  default     = "computor-coder-workspaces-offline"
  description = "Isolated Docker network WITHOUT egress, used when allow_internet is false. Declared `internal: true` in docker-compose.coder.yaml and carries the same ingress/agent services as docker_network."
  type        = string
}
