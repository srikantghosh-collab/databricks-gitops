USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_DS ADD COLUMNS (email STRING);

ALTER TABLE employee_DS RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_DS DROP COLUMN department;

ALTER TABLE employee_DS ALTER COLUMN salary TYPE INT;