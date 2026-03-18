USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro55 ADD COLUMN email STRING;

ALTER TABLE employee_pro55 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro55 DROP COLUMN department;

ALTER TABLE employee_pro55 ALTER COLUMN salary TYPE INT;
