terraform {
  backend "s3" {
    bucket         = "cryptobot-tfstate"
    key            = "data-service/kafka/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}