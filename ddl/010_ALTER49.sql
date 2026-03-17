USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro49 ADD COLUMN email STRING;

ALTER TABLE employee_pro49 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro49 DROP COLUMN department;

ALTER TABLE employee_pro49 ALTER COLUMN salary TYPE INT;
