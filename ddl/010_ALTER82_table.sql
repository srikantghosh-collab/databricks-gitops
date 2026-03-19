USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro82 ADD COLUMN email STRING;

ALTER TABLE employee_pro82 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro82 ALTER COLUMN salary TYPE INT;

ALTER TABLE employee_pro82 DROP COLUMN department;

