resource "helm_release" "cilium" {
  name       = "cilium"
  repository = "https://helm.cilium.io"
  chart      = "cilium"
  namespace  = "kube-system"
  version    = "1.18.5"
  values = [
    yamlencode({
      ingressController = {
        enabled = true
        default = true
      }
      hubble = {
        enabled = true
        relay   = { enabled = true }
        ui      = { enabled = true }
      }
    })
  ]
}

