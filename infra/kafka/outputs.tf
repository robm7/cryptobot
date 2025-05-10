output "cluster_arn" {
  description = "MSK Cluster ARN"
  value       = aws_msk_cluster.data_bus.arn
}

output "bootstrap_brokers" {
  description = "Plaintext connection endpoints"
  value       = aws_msk_cluster.data_bus.bootstrap_brokers
  sensitive   = true
}

output "bootstrap_brokers_tls" {
  description = "TLS connection endpoints"
  value       = aws_msk_cluster.data_bus.bootstrap_brokers_tls
  sensitive   = true
}

output "zookeeper_connect_string" {
  description = "Zookeeper connection string"
  value       = aws_msk_cluster.data_bus.zookeeper_connect_string
  sensitive   = true
}

output "current_version" {
  description = "Current Kafka version"
  value       = aws_msk_cluster.data_bus.current_version
}