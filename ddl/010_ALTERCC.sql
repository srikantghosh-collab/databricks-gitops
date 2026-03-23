USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_proCC ADD COLUMNS (email STRING);

ALTER TABLE employee_proCC RENAME COLUMN emp_name TO full_name;

this is the junk file

ALTER TABLE employee_proCC DROP COLUMN department;

ALTER TABLE employee_proCC ALTER COLUMN salary TYPE INT;