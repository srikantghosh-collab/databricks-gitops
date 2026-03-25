USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_proFF ADD COLUMNS (email STRING);

ALTER TABLE employee_proFF RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_proFF DROP COLUMN department;

ALTER TABLE employee_proFF ALTER COLUMN salary TYPE INT;