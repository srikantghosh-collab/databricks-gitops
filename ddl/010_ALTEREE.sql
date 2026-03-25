USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_proEE ADD COLUMNS (email STRING);

ALTER TABLE employee_proEE RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_proEE DROP COLUMN department;

ALTER TABLE employee_proEE ALTER COLUMN salary TYPE INT;