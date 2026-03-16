USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro26 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro26  DROP COLUMN department;

ALTER TABLE employee_pro26 ALTER COLUMN salary TYPE INT;