terraform {
  required_providers {
    coder = {
      source  = "coder/coder"
      version = "2.18.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "4.6.0"
    }
    # Only so Terraform can plan the removal of the resources the retired
    # registry.coder.com jetbrains module left in existing workspaces' state
    # (it used hashicorp/http). Nothing in this template uses it.
    http = {
      source  = "hashicorp/http"
      version = "3.6.2"
    }
  }
}

provider "docker" {
  host = var.docker_socket != "" ? var.docker_socket : null
}
