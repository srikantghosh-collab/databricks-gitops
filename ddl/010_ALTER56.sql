USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro56 ADD COLUMN email STRING;

ALTER TABLE employee_pro56 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro56 DROP COLUMN department;

ALTER TABLE employee_pro56 ALTER COLUMN salary TYPE INT;
