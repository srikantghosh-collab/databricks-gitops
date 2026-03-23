USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_proBB ADD COLUMNS (email STRING);

ALTER TABLE employee_proBB RENAME COLUMN emp_name TO full_name;

this is the junk file

ALTER TABLE employee_proBB DROP COLUMN department;

ALTER TABLE employee_proBB ALTER COLUMN salary TYPE INT;