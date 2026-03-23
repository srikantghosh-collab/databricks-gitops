USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro98 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro98 RENAME COLUMN emp_name TO full_name;

this is the new column

ALTER TABLE employee_pro98 DROP COLUMN department;

ALTER TABLE employee_pro98 ALTER COLUMN salary TYPE INT;