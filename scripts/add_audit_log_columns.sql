-- Add detailed columns to audit_logs (run this if you get "Unknown column 'actor_email'").
-- Usage (no space between -p and password):
--   mysql -u root -pYOUR_PASSWORD leave_management_db < scripts/add_audit_log_columns.sql
-- Or: mysql -u root -p -D leave_management_db < scripts/add_audit_log_columns.sql  (then enter password when prompted)
-- Or run in MySQL client / your DB tool. Run once.

ALTER TABLE audit_logs
  ADD COLUMN actor_email VARCHAR(255) NULL,
  ADD COLUMN actor_employee_id VARCHAR(50) NULL,
  ADD COLUMN actor_full_name VARCHAR(255) NULL,
  ADD COLUMN actor_role VARCHAR(50) NULL,
  ADD COLUMN summary TEXT NULL,
  ADD COLUMN request_method VARCHAR(10) NULL,
  ADD COLUMN request_path VARCHAR(500) NULL;

CREATE INDEX idx_actor_email ON audit_logs (actor_email);
CREATE INDEX idx_created_at_action ON audit_logs (created_at, action);
