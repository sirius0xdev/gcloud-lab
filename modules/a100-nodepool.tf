resource "google_container_node_pool" "a100_80gb_pool" {
  name       = "a100-80gb-analyst-pool"
  location   = "us-central1-a"
  cluster    = google_container_cluster.primary.name
  
  initial_node_count = 0
  autoscaling {
    min_node_count = 0
    max_node_count = 1
  }

  node_config {
    # A100 80GB requires the a2-ultragpu family
    machine_type = "a2-ultragpu-1g"

    guest_accelerator {
      type  = "nvidia-a100-80gb"
      count = 1
      
      gpu_driver_installation_config {
        gpu_driver_version = "LATEST"
      }
    }

    # SPOT is the modern equivalent of Preemptible
    spot = true

    # Specific labels to help the Autoscaler find this pool
    labels = {
      "cloud.google.com/gke-accelerator" = "nvidia-tesla-a100-80gb"
      "accelerator"                      = "a100-80gb"
    }

    # Taint to keep other pods off this expensive node
    taint {
      key    = "nvidia.com/gpu-a100-80gb"
      value  = "present"
      effect = "NO_SCHEDULE"
    }

    disk_size_gb = 200
    disk_type    = "pd-ssd"
    
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
