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
  default     = "localhost:5000/computor-workspace-vscode:latest"
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
  description = "Isolated Docker network for workspace containers. Kept off computor-network so untrusted workspaces (the user has sudo) cannot reach platform services; Traefik and Coder are dual-homed onto it. Must match the traefik.docker.network label below."
  type        = string
}

variable "coder_base_path" {
  default     = "/coder"
  description = "Base path prefix for code-server access via Traefik"
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

variable "code_server_password" {
  default     = ""
  description = "Password for code-server access (empty = no password required)"
  type        = string
  sensitive   = true
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
