
resource "google_container_node_pool" "cluster" {
  name     = "devops-lab-nodepool"
  location = "us-central1-a"
  cluster  = google_container_cluster.primary.name
  initial_node_count = 1 
  network_config {
    pod_range = "pod-ranges"
  }

  autoscaling {
    min_node_count = 1
    max_node_count = 5
  }

  node_config {
    machine_type = "e2-standard-2"
    spot = true 
    disk_size_gb = 20
    disk_type    = "pd-standard" 
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
  depends_on = [google_container_cluster.primary]

}
