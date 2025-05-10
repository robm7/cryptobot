variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment (dev/stage/prod)"
  type        = string
  default     = "prod"
}

variable "kafka_version" {
  description = "Kafka version"
  type        = string
  default     = "3.5.0"
}

variable "broker_instance_type" {
  description = "EC2 instance type for Kafka brokers"
  type        = string
  default     = "kafka.m5.2xlarge"
}

variable "storage_size_gb" {
  description = "EBS volume size per broker (GB)"
  type        = number
  default     = 1000
}