# Provider AWS + génération d'un suffixe aléatoire pour des noms de bucket uniques.
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "random_id" "suffix" {
  byte_length = 4
}

data "aws_caller_identity" "current" {}

locals {
  bucket_name = "${var.project_prefix}-${random_id.suffix.hex}"
  athena_output = "s3://${local.bucket_name}/athena-results/"
}
