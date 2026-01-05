
provider "google" {
  credentials = file("~/.config/gcloud/application_default_credentials.json")
  project     = "devops-lab-cluster"
  region      = "us-central1" # Or your desired region/location
}

data "google_client_config" "default" {}

provider "helm" {
  kubernetes = {
    host                   = "https://${google_container_cluster.primary.endpoint}"
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = base64decode(google_container_cluster.primary.master_auth[0].cluster_ca_certificate)
  }
}

provider "flux" {
  kubernetes = {

    host                   = "https://${google_container_cluster.primary.endpoint}"
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = base64decode(google_container_cluster.primary.master_auth[0].cluster_ca_certificate)
  }

  git = {

    url = "ssh://git@github.com/${var.github_org}/${var.github_repository}.git"

    branch = "master"
    ssh = {
      username    = "git"
      private_key = (file("~/.ssh/gcloud-lab"))
    }
  }
}
