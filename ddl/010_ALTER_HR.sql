USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_HR ADD COLUMNS (email STRING);

ALTER TABLE employee_HR RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_HR DROP COLUMN department;

ALTER TABLE employee_HR ALTER COLUMN salary TYPE INT;