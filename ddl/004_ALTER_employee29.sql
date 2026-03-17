USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro29 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro29 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro29 DROP COLUMN department;

ALTER TABLE employee_pro29 ALTER COLUMN salary TYPE INT;