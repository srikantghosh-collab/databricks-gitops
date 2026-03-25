USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_dataops ADD COLUMNS (email STRING);

ALTER TABLE employee_dataops RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_dataops DROP COLUMN department;

ALTER TABLE employee_dataops ALTER COLUMN salary TYPE INT;