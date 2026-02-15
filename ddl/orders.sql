ALTER TABLE employees_master
SET TBLPROPERTIES ('delta.columnMapping.mode' = 'name');

ALTER TABLE employees_master RENAME COLUMN emp_name TO full_name;


