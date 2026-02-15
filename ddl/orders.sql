ALTER TABLE employees
SET TBLPROPERTIES ('delta.columnMapping.mode' = 'name');

ALTER TABLE employees RENAME COLUMN emp_name TO full_name;


