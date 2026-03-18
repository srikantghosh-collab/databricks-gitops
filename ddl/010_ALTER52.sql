USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro52 ADD COLUMN email STRING;

ALTER TABLE employee_pro52 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro52 DROP COLUMN department;

ALTER TABLE employee_pro52 ALTER COLUMN salary TYPE INT;
