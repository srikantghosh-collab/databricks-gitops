USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro71 ADD COLUMN email STRING;

ALTER TABLE employee_pro71 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro71 ALTER COLUMN salary TYPE INT;

ALTER TABLE employee_pro71 DROP COLUMN department;

