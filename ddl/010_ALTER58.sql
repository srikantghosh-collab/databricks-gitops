USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro58 ADD COLUMN email STRING;

ALTER TABLE employee_pro58 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro58 DROP COLUMN department;

ALTER TABLE employee_pro58 ALTER COLUMN salary TYPE INT;
