USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro63 ADD COLUMN email STRING;

ALTER TABLE employee_pro63 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro63 DROP COLUMN department;

