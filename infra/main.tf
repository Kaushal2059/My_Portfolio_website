terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>5.0"
    }
  }
}
provider "aws" {
  region = "us-east-1"
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "portfolio-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "portfolio-igw"
  }
}

resource "aws_subnet" "portfolio-public-a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.0.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "portfolio-public-a"
  }
}

resource "aws_subnet" "portfolio-public-b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true

  tags = {
    Name = "portfolio-public-b"
  }
}

resource "aws_subnet" "portfolio-private-a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = {
    Name = "portfolio-private-a"
  }
}

resource "aws_subnet" "portfolio-private-b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "portfolio-private-b"
  }
}

resource "aws_eip" "elastic-ip" {
  domain = "vpc"
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.elastic-ip.id
  subnet_id     = aws_subnet.portfolio-public-a.id
  depends_on    = [aws_internet_gateway.main]

  tags = {
    Name = "portfolio-nat"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "portfolio-public-rt"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }

  tags = {
    Name = "portfolio-private-rt"
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.portfolio-public-a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.portfolio-public-b.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.portfolio-private-a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.portfolio-private-b.id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "alb" {
  name        = "portfolio-alb-sg"
  description = "Allow inbound HTTP from the internet to the ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "portfolio-alb-sg"
  }
}

resource "aws_security_group" "ec2" {
  name        = "portfolio-ec2-sg"
  description = "portfolio ec2 security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "portfolio-ec2-sg"
  }
}

resource "aws_security_group" "rds" {
  name        = "portfolio-rds-sg"
  description = "portfolio rds security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "portfolio-rds-sg"
  }
}

# Already imported — kept as a reference 
#import {
#  to = aws_ecr_repository.web
#  id = "portfolio-web"
#}

resource "aws_ecr_repository" "web" {
  force_delete         = null
  image_tag_mutability = "MUTABLE"
  name                 = "portfolio-web"
  tags                 = {}
  encryption_configuration {
    encryption_type = "AES256"
  }
  image_scanning_configuration {
    scan_on_push = false
  }
  lifecycle {
    prevent_destroy = true
  }
}

# Already imported — kept as a reference for the same pattern.
# import {
#   to = aws_iam_role.ec2
#   id = "portfolio-ec2-role"
# }

# import {
#   to = aws_iam_role_policy_attachment.ssm
#   id = "portfolio-ec2-role/arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
# }

# import {
#   to = aws_iam_role_policy_attachment.ecr_readonly
#   id = "portfolio-ec2-role/arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
# }

# import {
#   to = aws_iam_role_policy.s3_media
#   id = "portfolio-ec2-role:porfolio-se-media-access"
# }

# import {
#   to = aws_iam_instance_profile.ec2
#   id = "portfolio-ec2-role"
# }

# __generated__ by Terraform from "portfolio-ec2-role/arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
resource "aws_iam_role_policy_attachment" "ssm" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.ec2.name
  lifecycle {
    prevent_destroy = true
  }
}

# __generated__ by Terraform from "portfolio-ec2-role:porfolio-se-media-access"
resource "aws_iam_role_policy" "s3_media" {
  name = "porfolio-se-media-access"
  policy = jsonencode({
    Statement = [{
      Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
      Effect   = "Allow"
      Resource = "arn:aws:s3:::portfolio-media-897021975353/*"
      }, {
      Action   = "s3:ListBucket"
      Effect   = "Allow"
      Resource = "arn:aws:s3:::portfolio-media-897021975353"
    }]
    Version = "2012-10-17"
  })
  lifecycle {
    prevent_destroy = true
  }
  role = aws_iam_role.ec2.name
}

# __generated__ by Terraform from "portfolio-ec2-role/arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.ec2.name
  lifecycle {
    prevent_destroy = true
  }
}

# __generated__ by Terraform from "portfolio-ec2-role"
resource "aws_iam_instance_profile" "ec2" {
  name = "portfolio-ec2-role"
  path = "/"
  role = aws_iam_role.ec2.name
  tags = {}
  lifecycle {
    prevent_destroy = true
  }
}

# __generated__ by Terraform from "portfolio-ec2-role"
resource "aws_iam_role" "ec2" {
  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })
  description           = "Allows EC2 instances to call AWS services on your behalf."
  force_detach_policies = false
  max_session_duration  = 3600
  name                  = "portfolio-ec2-role"
  path                  = "/"
  permissions_boundary  = null
  tags                  = {}
  lifecycle {
    prevent_destroy = true
  }
}

# Already imported — kept as a reference for the same pattern.
# import {
#   to = aws_s3_bucket.media
#   id = "portfolio-media-897021975353"
# }

# import {
#   to = aws_s3_bucket_public_access_block.media
#   id = "portfolio-media-897021975353"
# }

# import {
#   to = aws_s3_bucket_policy.media
#   id = "portfolio-media-897021975353"
# }

# import {
#   to = aws_s3_bucket_server_side_encryption_configuration.media
#   id = "portfolio-media-897021975353"
# }

# import {
#   to = aws_s3_bucket_ownership_controls.media
#   id = "portfolio-media-897021975353"
# }

resource "aws_s3_bucket_public_access_block" "media" {
  block_public_acls       = true
  block_public_policy     = false
  bucket                  = aws_s3_bucket.media.id
  ignore_public_acls      = true
  restrict_public_buckets = false
  lifecycle {
    prevent_destroy = true
  }
}

# __generated__ by Terraform from "portfolio-media-897021975353"
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket                = aws_s3_bucket.media.id
  expected_bucket_owner = null
  lifecycle {
    prevent_destroy = true
  }
  rule {
    bucket_key_enabled = true
    apply_server_side_encryption_by_default {
      kms_master_key_id = null
      sse_algorithm     = "AES256"
    }
  }
}

# __generated__ by Terraform from "portfolio-media-897021975353"
resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id
  lifecycle {
    prevent_destroy = true
  }
  policy = jsonencode({
    Statement = [{
      Action    = "s3:GetObject"
      Effect    = "Allow"
      Principal = "*"
      Resource  = "arn:aws:s3:::portfolio-media-897021975353/*"
      Sid       = "PublicReadGetObject"
    }]
    Version = "2012-10-17"
  })
}

# __generated__ by Terraform from "portfolio-media-897021975353"
resource "aws_s3_bucket_ownership_controls" "media" {
  bucket = aws_s3_bucket.media.id
  lifecycle {
    prevent_destroy = true
  }
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# __generated__ by Terraform from "portfolio-media-897021975353"
resource "aws_s3_bucket" "media" {
  bucket              = "portfolio-media-897021975353"
  force_destroy       = null
  object_lock_enabled = false
  tags                = {}
  lifecycle {
    prevent_destroy = true
  }
}


resource "aws_db_subnet_group" "main" {
  name       = "portfolio-db-subnet-group"
  subnet_ids = [aws_subnet.portfolio-private-a.id, aws_subnet.portfolio-private-b.id]

  tags = {
    Name = "portfolio-db-subnet-group"
  }
}

resource "aws_db_instance" "portfolio-db" {
  identifier                  = "portfolio-db"
  engine                      = "postgres"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  db_name                     = "portfolio_website"
  username                    = "kaushal20"
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.main.name
  vpc_security_group_ids      = [aws_security_group.rds.id]
  multi_az                    = false
  publicly_accessible         = false
  backup_retention_period     = 7
  skip_final_snapshot         = true
  deletion_protection         = false
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical's official AWS account ID
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd*/ubuntu-noble-24.04-amd64-server-*"]
  }
}

resource "aws_instance" "main" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.portfolio-private-a.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name
  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }
  tags = {
    Name = "portfolio-web-server"
  }
}

resource "aws_lb" "main" {
  name               = "portfolio-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.portfolio-public-a.id, aws_subnet.portfolio-public-b.id]
}

resource "aws_lb_target_group" "main" {
  name     = "portfolio-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  health_check {
    path = "/portfolio_pages/"
  }
}

resource "aws_lb_listener" "main" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

resource "aws_lb_target_group_attachment" "main" {
  target_group_arn = aws_lb_target_group.main.arn
  target_id        = aws_instance.main.id
  port             = 80
}

# Private relay bucket for Ansible's aws_ssm connection plugin (Phase 11).
# Not for public content — kept separate from portfolio-media-* on purpose.
resource "aws_s3_bucket" "ansible_relay" {
  bucket = "portfolio-ansible-relay-897021975353"

  tags = {
    Name = "portfolio-ansible-relay"
  }
}

resource "aws_s3_bucket_public_access_block" "ansible_relay" {
  bucket                  = aws_s3_bucket.ansible_relay.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role_policy" "ansible_relay" {
  name = "portfolio-ansible-relay-access"
  policy = jsonencode({
    Statement = [{
      Action   = ["s3:GetObject", "s3:PutObject"]
      Effect   = "Allow"
      Resource = "${aws_s3_bucket.ansible_relay.arn}/*"
      }, {
      Action   = "s3:ListBucket"
      Effect   = "Allow"
      Resource = aws_s3_bucket.ansible_relay.arn
    }]
    Version = "2012-10-17"
  })
  role = aws_iam_role.ec2.name
}

