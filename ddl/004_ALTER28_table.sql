USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro28 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro28  RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro28 DROP COLUMN department;

ALTER TABLE employee_pro28 ALTER COLUMN salary TYPE INT;