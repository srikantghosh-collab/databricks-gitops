USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro83 ADD COLUMN email STRING;

ALTER TABLE employee_pro83 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro83 ALTER COLUMN salary TYPE INT;

ALTER TABLE employee_pro83 DROP COLUMN department;

