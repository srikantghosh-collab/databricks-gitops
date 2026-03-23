USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro99 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro99 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro99 DROP COLUMN department;

ALTER TABLE employee_pro99 ALTER COLUMN salary TYPE INT;