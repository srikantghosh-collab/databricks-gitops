USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro67 ADD COLUMN email STRING;

ALTER TABLE employee_pro67 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro67 ALTER COLUMN salary TYPE INT;

ALTER TABLE employee_pro67 DROP COLUMN department;

