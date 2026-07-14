terraform {
  required_providers {
    coder = {
      source  = "coder/coder"
      version = ">= 2.5.3"
    }
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

provider "docker" {
  host = var.docker_socket != "" ? var.docker_socket : null
}
