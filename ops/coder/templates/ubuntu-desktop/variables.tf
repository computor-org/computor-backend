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
  default     = "computor-coder-workspaces"
  description = "Isolated Docker network for workspace containers. Kept off computor-network so untrusted workspaces cannot reach platform services; Traefik and Coder are dual-homed onto it. Must match the traefik.docker.network label below."
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
