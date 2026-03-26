USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_GG ADD COLUMNS (email STRING);

ALTER TABLE employee_GG RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_GG DROP COLUMN department;

ALTER TABLE employee_GG ALTER COLUMN salary TYPE INT;
