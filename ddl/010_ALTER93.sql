USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro93 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro93 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro93 DROP COLUMN department;

ALTER TABLE employee_pro93 ALTER COLUMN salary TYPE INT;