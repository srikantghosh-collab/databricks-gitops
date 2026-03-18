USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

ALTER TABLE employee_pro57 ADD COLUMN email STRING;

ALTER TABLE employee_pro57 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_pro57 DROP COLUMN department;

ALTER TABLE employee_pro57 ALTER COLUMN salary TYPE INT;
