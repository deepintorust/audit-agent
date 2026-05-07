CREATE DATABASE IF NOT EXISTS audit_agent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE audit_agent;

CREATE TABLE IF NOT EXISTS files (
  file_id VARCHAR(32) PRIMARY KEY,
  file_hash_full CHAR(64) NOT NULL UNIQUE,
  filename LONGTEXT NOT NULL,
  content_type VARCHAR(255) NOT NULL DEFAULT '',
  meta_frontend JSON NOT NULL,
  meta_merged JSON NOT NULL,
  storage_backend VARCHAR(32) NOT NULL DEFAULT 's3',
  storage_bucket VARCHAR(255) NOT NULL DEFAULT '',
  storage_key VARCHAR(1024) NOT NULL DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT 'UPLOADED',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_files_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id CHAR(36) PRIMARY KEY,
  file_id VARCHAR(32) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'RUNNING',
  current_step VARCHAR(16) NOT NULL DEFAULT 'STORE',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_runs_file (file_id),
  INDEX idx_runs_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS process_steps (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  file_id VARCHAR(32) NOT NULL,
  step VARCHAR(16) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
  attempt INT NOT NULL DEFAULT 0,
  error_code VARCHAR(64) NOT NULL DEFAULT '',
  error_msg LONGTEXT NOT NULL,
  started_at TIMESTAMP NULL,
  ended_at TIMESTAMP NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_run_step (run_id, step),
  INDEX idx_steps_run (run_id),
  INDEX idx_steps_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS projects (
  project_id VARCHAR(32) PRIMARY KEY,
  project_hash_full CHAR(64) NOT NULL UNIQUE,
  project_name LONGTEXT NOT NULL,
  project_year VARCHAR(32) NOT NULL DEFAULT '',
  construction_unit LONGTEXT NOT NULL,
  approval_info LONGTEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS companies (
  company_id VARCHAR(32) PRIMARY KEY,
  company_hash_full CHAR(64) NOT NULL UNIQUE,
  project_id VARCHAR(32) NOT NULL,
  company_name LONGTEXT NOT NULL,
  uscc VARCHAR(64) NOT NULL DEFAULT '',
  address LONGTEXT NOT NULL,
  contact LONGTEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_company_project (project_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS chunks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  chunk_id VARCHAR(32) NOT NULL,
  file_id VARCHAR(32) NOT NULL,
  run_id CHAR(36) NOT NULL,
  chunk_index INT NOT NULL,
  content LONGTEXT NOT NULL,
  payload_snapshot JSON NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'CHUNKED',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_file_chunk_index (file_id, chunk_index),
  INDEX idx_chunks_file (file_id),
  INDEX idx_chunks_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS llm_call_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  call_id CHAR(36) NOT NULL,
  run_id CHAR(36) NOT NULL,
  file_id VARCHAR(32) NOT NULL,
  step VARCHAR(16) NOT NULL,
  provider VARCHAR(64) NOT NULL DEFAULT '',
  model VARCHAR(128) NOT NULL DEFAULT '',
  request_json JSON NOT NULL,
  response_json JSON NOT NULL,
  error_msg LONGTEXT NOT NULL,
  success TINYINT NOT NULL DEFAULT 0,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ended_at TIMESTAMP NULL,
  INDEX idx_llm_run (run_id),
  INDEX idx_llm_file (file_id)
) ENGINE=InnoDB;

