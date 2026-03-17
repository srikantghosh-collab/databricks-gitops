USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro42 ADD COLUMN (email STRING);

ALTER TABLE employee_pro42 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro42 DROP COLUMN department;

ALTER TABLE employee_pro42 ALTER COLUMN salary TYPE INT;