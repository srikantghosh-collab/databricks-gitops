USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_BBC ADD COLUMNS (email STRING);

ALTER TABLE employee_BBC RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_BBC DROP COLUMN department;

ALTER TABLE employee_BBC ALTER COLUMN salary TYPE INT;
