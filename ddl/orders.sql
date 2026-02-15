ALTER TABLE employees ADD COLUMN email STRING;

ALTER TABLE employees RENAME COLUMN emp_name TO full_name;

ALTER TABLE employees ALTER COLUMN salary COMMENT 'Monthly salary in INR';

ALTER TABLE employees SET TBLPROPERTIES (
  'quality' = 'silver',
  'modified_by' = 'devops_pipeline'
);

ALTER TABLE employees RENAME TO employee_master;
