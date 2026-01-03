
provider "google" {
  credentials = file("~/.config/gcloud/application_default_credentials.json")
  project     = "devops-lab-cluster"
  region      = "us-central1" # Or your desired region/location
}

data "google_client_config" "default" {}

provider "helm" {
  kubernetes = {
    host                   = "https://${google_container_cluster.default.endpoint}"
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = base64decode(google_container_cluster.default.master_auth[0].cluster_ca_certificate)
  }
}
