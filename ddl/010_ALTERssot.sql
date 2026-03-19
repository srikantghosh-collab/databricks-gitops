USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_ssot ADD COLUMNS (email STRING);

ALTER TABLE employee_ssot RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_ssot DROP COLUMN department;

ALTER TABLE employee_ssot ALTER COLUMN salary TYPE INT;