USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro64 ADD COLUMN email STRING;

ALTER TABLE employee_pro64 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro64 ALTER COLUMN salary TYPE INT;

ALTER TABLE employee_pro64 DROP COLUMN department;

