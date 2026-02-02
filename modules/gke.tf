
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
  
  lifecycle {
    ignore_changes = [
      enable_autopilot,
      enable_tpu,
      enable_intranode_visibility,
      resource_labels,

      addons_config,
      anonymous_authentication_config,
      binary_authorization,
      cluster_autoscaling,
      database_encryption,
      default_snat_status,
      gateway_api_config,
      logging_config,
      control_plane_endpoints_config,
      cost_management_config,
      enterprise_config,
      gke_auto_upgrade_config,
      identity_service_config,
      node_config,
      node_config[0].spot,               # or node_config.spot if not indexed
      node_config[0].preemptible,        # sometimes shown as this
      node_config[0].disk_size_gb,
      node_config[0].disk_type,
      node_config[0].metadata,
      node_config[0].resource_labels,
      node_config[0].boot_disk,
      # IP policy sub-drift
      ip_allocation_policy,

      # Auth/cert drift
      master_auth,

      # Computed/read-only (removes warnings too)
      endpoint,
      self_link,
      label_fingerprint,
      operation,
      cluster_ipv4_cidr,
      services_ipv4_cidr,
      node_locations,
      default_max_pods_per_node,
      networking_mode,
      private_ipv6_google_access,
      tpu_ipv4_cidr_block,

      master_version,
      node_version,
      logging_service,
      monitoring_service,  
  ]
  }
}
  
