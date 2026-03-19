USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro90 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro90 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro90 DROP COLUMN department;

ALTER TABLE employee_pro90 ALTER COLUMN salary TYPE INT;