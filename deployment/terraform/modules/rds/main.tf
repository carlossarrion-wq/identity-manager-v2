# =====================================================
# RDS PostgreSQL Module for Identity Manager
# =====================================================

# Security Group for RDS
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  description = "Security group for Identity Manager RDS instance"
  vpc_id      = var.vpc_id

  # PostgreSQL access from VPC and Internet (for Lambda without VPC)
  ingress {
    description = "PostgreSQL from VPC and Internet"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = concat(var.allowed_cidr_blocks, ["0.0.0.0/0"])  # Allow from internet for Lambda without VPC
  }

  # Self-referencing rule for PostgreSQL (Lambda to RDS)
  ingress {
    description     = "PostgreSQL self-referencing"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    self            = true
  }

  # Self-referencing rule for HTTPS (Lambda to VPC Endpoints - Secrets Manager)
  ingress {
    description     = "HTTPS for VPC Endpoints"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    self            = true
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-rds-sg"
    }
  )
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name_prefix = "${var.project_name}-${var.environment}-"
  description = "Subnet group for Identity Manager RDS"
  subnet_ids  = var.subnet_ids

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-db-subnet-group"
    }
  )
}

# Random password for RDS master user
resource "random_password" "master" {
  length  = 32
  special = true
}

# Store RDS credentials in Secrets Manager
# Nomenclatura: <aplicacion>-<entorno>-<tipo>-<detalle>
resource "aws_secretsmanager_secret" "rds_credentials" {
  name                    = "identity-mgmt-${var.environment}-db-admin"
  description             = "RDS admin credentials for Identity Manager ${var.environment}"
  recovery_window_in_days = var.environment == "pro" ? 30 : 7

  tags = merge(
    var.tags,
    {
      Name        = "identity-mgmt-${var.environment}-db-admin"
      Environment = var.environment
      Application = "identity-mgmt"
      SecretType  = "db"
      AccessLevel = "admin"
    }
  )
}

resource "aws_secretsmanager_secret_version" "rds_credentials" {
  secret_id = aws_secretsmanager_secret.rds_credentials.id
  secret_string = jsonencode({
    username = var.master_username
    password = random_password.master.result
    engine   = "postgres"
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = var.database_name
  })
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-${var.environment}-rds"
  engine         = "postgres"
  engine_version = var.postgres_version

  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage
  storage_type      = var.storage_type
  storage_encrypted = true
  kms_key_id        = var.kms_key_id

  db_name  = var.database_name
  username = var.master_username
  password = random_password.master.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = var.publicly_accessible

  backup_retention_period = var.backup_retention_period
  backup_window           = var.backup_window
  maintenance_window      = var.maintenance_window

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = var.monitoring_interval
  monitoring_role_arn             = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null

  deletion_protection = var.deletion_protection
  skip_final_snapshot = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  apply_immediately          = var.apply_immediately

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-rds"
      Environment = var.environment
    }
  )
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0

  name_prefix = "${var.project_name}-${var.environment}-rds-monitoring-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0

  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# NOTE: Database initialization must be done from EC2 instance in same VPC
# Null resource disabled - run scripts manually from EC2
# resource "null_resource" "init_database" {
#   depends_on = [aws_db_instance.main, aws_secretsmanager_secret_version.rds_credentials]
#   
#   triggers = {
#     db_instance_id = aws_db_instance.main.id
#   }
# }
