USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

CREATE TABLE IF NOT EXISTS employee_pro59 (
    emp_id INT,
    emp_name STRING,
    department STRING,
    salary DECIMAL(10,2),
    created_date TIMESTAMP
)
USING DELTA;