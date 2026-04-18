resource "google_container_node_pool" "pro6000_pool" {
  name       = "pro600-pool"
  location   = "us-central1-a"
  cluster    = google_container_cluster.primary.name
  
  node_locations = [
    "us-central1-b" ,
    "us-central1-f"
  ]

  initial_node_count = 0
  autoscaling {
    min_node_count = 0
    max_node_count = 1
  }

  node_config {
    # pro6000 gpu requires a g4-standard-48 machine type
    machine_type = "g4-standard-48"

    guest_accelerator {
      type  = "nvidia-rtx-pro-6000"
      count = 1
      
      gpu_driver_installation_config {
        gpu_driver_version = "LATEST"
      }
    }

    # SPOT is the modern equivalent of Preemptible
    spot = false 

    # Specific labels to help the Autoscaler find this pool
    labels = {
      "accelerator"                 = "pro6000-gpu"
    }

    # Taint to keep other pods off this expensive node
    taint {
      key    = "nvidia.com/gpu-nvidia-rtx-pro-6000"
      value  = "present"
      effect = "NO_SCHEDULE"
    }

    disk_size_gb = 100 
    disk_type    = "hyperdisk-balanced"
    
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
