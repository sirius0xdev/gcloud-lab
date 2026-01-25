
resource "google_container_cluster" "primary" {
  name               = "devops-lab-cluster"
  location           = "us-central1-a"
  remove_default_node_pool = true 
  initial_node_count = 1

  datapath_provider = "ADVANCED_DATAPATH"

  enable_cilium_clusterwide_network_policy = true
  network                                  = google_compute_network.default.id
  subnetwork                               = google_compute_subnetwork.default.id

  node_config {
    machine_type = "e2-standard-2"
    disk_size_gb = 25
    disk_type    = "pd-ssd"
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    taint {
      key    = "node.cilium.io/agent-not-ready"
      value  = "true"
      effect = "NO_EXECUTE"
    }
  }
  ip_allocation_policy {
    stack_type                    = "IPV4_IPV6"
    services_secondary_range_name = google_compute_subnetwork.default.secondary_ip_range[0].range_name
    cluster_secondary_range_name  = google_compute_subnetwork.default.secondary_ip_range[1].range_name
  }

  enable_l4_ilb_subsetting = true
  deletion_protection      = false
}
