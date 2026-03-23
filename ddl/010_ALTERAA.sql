USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_proAA ADD COLUMNS (email STRING);

ALTER TABLE employee_proAA RENAME COLUMN emp_name TO full_name;

this is the junk file

ALTER TABLE employee_proAA DROP COLUMN department;

ALTER TABLE employee_proAA ALTER COLUMN salary TYPE INT;