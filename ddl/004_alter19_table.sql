USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro19 ADD COLUMNS (email STRING);

ALTER TABLE employee_pro19 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro19 DROP COLUMN department;

ALTER TABLE employee_pro19 ALTER COLUMN salary TYPE INT;