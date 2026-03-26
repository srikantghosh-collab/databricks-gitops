USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_HH ADD COLUMNS (email STRING);

ALTER TABLE employee_HH RENAME COLUMN emp_name TO full_name;

this is a junk file

ALTER TABLE employee_HH DROP COLUMN department;

ALTER TABLE employee_HH ALTER COLUMN salary TYPE INT;
