USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro38 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro38 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro38 DROP COLUMN department;

ALTER TABLE employee_pro38 ALTER COLUMN salary TYPE INT;