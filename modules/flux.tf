terraform {
  required_version = ">= 1.7.0"

  required_providers {
    flux = {
      source  = "fluxcd/flux"
      version = ">= 1.2"
    }
  }
}
resource "flux_bootstrap_git" "this" {

  embedded_manifests = true
  path               = "clusters/gcloud-lab"
}
