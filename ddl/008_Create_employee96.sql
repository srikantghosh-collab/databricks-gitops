USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

CREATE TABLE IF NOT EXISTS employee_pro96 (
    emp_id INT,
    emp_name STRING,
    department STRING,
    salary DECIMAL(10,2),
    created_date TIMESTAMP
)
USING DELTA;