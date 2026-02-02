-- Drop and recreate audit_logs with the new schema (affected_entity_*, actor columns; no ip_address/user_agent).
-- All existing audit data will be lost. Run once.
--   mysql -u root -pYOUR_PASSWORD leave_management_db < scripts/recreate_audit_logs.sql

DROP TABLE IF EXISTS audit_logs;

CREATE TABLE audit_logs (
  id INT NOT NULL AUTO_INCREMENT,
  user_id INT NULL,
  actor_employee_id VARCHAR(50) NULL,
  actor_full_name VARCHAR(255) NULL,
  actor_role VARCHAR(50) NULL,
  actor_email VARCHAR(255) NULL,
  affected_entity_id INT NULL,
  affected_entity_type VARCHAR(50) NOT NULL,
  action VARCHAR(100) NOT NULL,
  summary TEXT NULL,
  request_method VARCHAR(10) NULL,
  request_path VARCHAR(500) NULL,
  old_values JSON NULL,
  new_values JSON NULL,
  created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_audit_logs_user_id FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_user_id ON audit_logs (user_id);
CREATE INDEX idx_action ON audit_logs (action);
CREATE INDEX idx_affected_entity ON audit_logs (affected_entity_type, affected_entity_id);
CREATE INDEX idx_created_at ON audit_logs (created_at);
CREATE INDEX idx_affected_entity_type ON audit_logs (affected_entity_type);
CREATE INDEX idx_actor_email ON audit_logs (actor_email);
CREATE INDEX idx_created_at_action ON audit_logs (created_at, action);
