USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro72 ADD COLUMN email STRING;

ALTER TABLE employee_pro72 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro72 ALTER COLUMN salary TYPE INT;

ALTER TABLE employee_pro72 DROP COLUMN department;

