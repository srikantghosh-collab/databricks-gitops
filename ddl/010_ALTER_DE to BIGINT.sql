USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_DE ALTER COLUMN salary TYPE BIGINT;