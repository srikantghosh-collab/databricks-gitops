USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_proDD ADD COLUMNS (email STRING);

ALTER TABLE employee_proDD RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_proDD DROP COLUMN department;

ALTER TABLE employee_proDD ALTER COLUMN salary TYPE INT;