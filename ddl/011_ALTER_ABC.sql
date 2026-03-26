USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_ABC ADD COLUMNS (email STRING);

ALTER TABLE employee_ABC RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_ABC DROP COLUMN department;

ALTER TABLE employee_ABC ALTER COLUMN salary TYPE INT;
