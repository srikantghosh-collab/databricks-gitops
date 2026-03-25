USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_devops ADD COLUMNS (email STRING);

ALTER TABLE employee_devops RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_devops DROP COLUMN department;

ALTER TABLE employee_devops ALTER COLUMN salary TYPE INT;