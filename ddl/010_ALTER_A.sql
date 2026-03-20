USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_A ADD COLUMNS (email STRING);

ALTER TABLE employee_A RENAME COLUMN emp_name TO full_name;

this is the new DDL generation

ALTER TABLE employee_A DROP COLUMN department;

ALTER TABLE employee_A ALTER COLUMN salary TYPE INT;