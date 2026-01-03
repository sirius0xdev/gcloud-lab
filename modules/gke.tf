
resource "google_container_cluster" "default" {
  name               = "devops-lab-cluster"
  location           = "us-central1-a"
  initial_node_count = 1

  datapath_provider = "ADVANCED_DATAPATH"

  enable_cilium_clusterwide_network_policy = true
  remove_default_node_pool                 = true
  network                                  = google_compute_network.default.id
  subnetwork                               = google_compute_subnetwork.default.id

  node_config {
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
