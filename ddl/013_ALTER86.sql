USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

ALTER TABLE employee_pro86 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro86 RENAME COLUMN emp_name TO full_name;

this is the new DDL execution

ALTER TABLE employee_pro86 DROP COLUMN department;

ALTER TABLE employee_pro86 ALTER COLUMN salary TYPE INT;