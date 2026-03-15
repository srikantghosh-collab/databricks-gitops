USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro20 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro20 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro20 DROP COLUMN department;

ALTER TABLE employee_pro20 ALTER COLUMN salary TYPE INT;