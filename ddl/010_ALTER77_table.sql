USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro77 ADD COLUMN email STRING;

ALTER TABLE employee_pro77 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro77 ALTER COLUMN salary TYPE INT;

ALTER TABLE employee_pro77 DROP COLUMN department;

