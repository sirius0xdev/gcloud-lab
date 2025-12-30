# Configure the Google Cloud provider
provider "google" {
  credentials = file("~/.config/gcloud/application_default_credentials.json")
  project     = "devops-lab-cluster"
  region      = "us-central1" # Or your desired region/location
}

resource "google_compute_network" "default" {
  name = "devops-lab-network"

  auto_create_subnetworks  = false
  enable_ula_internal_ipv6 = true
}

resource "google_compute_subnetwork" "default" {
  name = "devops-lab-subnetwork"

  ip_cidr_range = "10.0.0.0/16"
  region        = "us-central1"

  stack_type       = "IPV4_IPV6"
  ipv6_access_type = "INTERNAL" # Change to "EXTERNAL" if creating an external loadbalancer

  network = google_compute_network.default.id
  secondary_ip_range {
    range_name    = "services-range"
    ip_cidr_range = "192.168.0.0/24"
  }

  secondary_ip_range {
    range_name    = "pod-ranges"
    ip_cidr_range = "192.168.1.0/24"
  }
}

resource "google_container_cluster" "default" {
  name     = "devops-lab-cluster"
  location = "us-central1-a"

  # 1. Enable Cilium via Dataplane V2
  datapath_provider = "ADVANCED_DATAPATH"
  initial_node_count = 1 
  # 2. REQUIRED: Remove the network_policy block. 
  # Dataplane V2 handles policies natively.

  # 3. Optional: Enable Cilium-specific cluster-wide policies (GKE 1.28+)
  enable_cilium_clusterwide_network_policy = true

  network    = google_compute_network.default.id
  subnetwork = google_compute_subnetwork.default.id

  ip_allocation_policy {
    stack_type                    = "IPV4_IPV6"
    services_secondary_range_name = google_compute_subnetwork.default.secondary_ip_range[0].range_name
    cluster_secondary_range_name  = google_compute_subnetwork.default.secondary_ip_range[1].range_name
  }

  enable_l4_ilb_subsetting = true
  deletion_protection      = false
}
