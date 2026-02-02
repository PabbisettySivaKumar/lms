-- Rename audit_logs columns: resource_type → target_type, resource_id → target_id
-- Run once after deploying the code change. Use -p with no space before password if needed.
--   mysql -u root -pYOUR_PASSWORD leave_management_db < scripts/rename_audit_log_to_target.sql

-- Drop indexes that use the old column names first (MySQL does not support IF EXISTS for DROP INDEX)
DROP INDEX idx_resource ON audit_logs;
DROP INDEX idx_resource_type ON audit_logs;

ALTER TABLE audit_logs
  CHANGE COLUMN resource_type target_type VARCHAR(50) NOT NULL COMMENT 'Type of affected record: USER, LEAVE, POLICY, HOLIDAY, COMP_OFF, JOB, BALANCE',
  CHANGE COLUMN resource_id   target_id   INT NULL COMMENT 'ID of the affected record (e.g. leave id, user id)';

CREATE INDEX idx_target ON audit_logs (target_type, target_id);
CREATE INDEX idx_target_type ON audit_logs (target_type);
