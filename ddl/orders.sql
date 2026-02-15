ALTER TABLE employee_master
SET TBLPROPERTIES ('delta.columnMapping.mode' = 'name');

ALTER TABLE employee_master RENAME COLUMN emp_name TO full_name;


