USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

INSERT INTO employee_pro80 VALUES
(1, 'John', 'IT', 60000, current_timestamp()),
(2, 'Sara', 'HR', 50000, current_timestamp()),
(3, 'Mike', 'Finance', 70000, current_timestamp()),
(4, 'David', 'IT', 65000, current_timestamp()),
(5, 'Emma', 'HR', 52000, current_timestamp());


-- USE CATALOG hive_metastore;
-- USE SCHEMA sigmoid_employee;

-- ALTER TABLE employee_pro48 ADD COLUMN email STRING;

-- ALTER TABLE employee_pro48 RENAME COLUMN emp_name TO full_name;

-- ALTER TABLE employee_pro48 DROP COLUMN department;

-- ALTER TABLE employee_pro48 ALTER COLUMN salary TYPE INT;