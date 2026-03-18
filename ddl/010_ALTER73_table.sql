USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro73 ADD COLUMN email STRING;

ALTER TABLE employee_pro73 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro73 ALTER COLUMN salary TYPE INT;

ALTER TABLE employee_pro73 DROP COLUMN department;

