USE CATALOG hive_metastore;
USE SCHEMA demo_ddl_db;

INSERT INTO employee_pro22 VALUES
(1, 'John', 'IT', 60000, current_timestamp()),
(2, 'Sara', 'HR', 50000, current_timestamp()),
(3, 'Mike', 'Finance', 70000, current_timestamp());
-- (4, 'David', 'IT', 65000, current_timestamp()),
-- (5, 'Emma', 'HR', 52000, current_timestamp()),
-- (6, 'Liam', 'Finance', 72000, current_timestamp()),
-- (7, 'Olivia', 'Marketing', 58000, current_timestamp()),
-- (8, 'Noah', 'Sales', 61000, current_timestamp()),
-- (9, 'Ava', 'IT', 64000, current_timestamp()),
-- (10, 'William', 'Finance', 75000, current_timestamp());

-- ALTER TABLE employee_pro17 SET TBLPROPERTIES (
--     'delta.logRetentionDuration' = 'interval 30 days',
--     'delta.deletedFileRetentionDuration' = 'interval 30 days'
-- );   
-- DROP TABLE employee_pro14;
-- ALTER TABLE employee_pro14 ADD COLUMNS (email STRING);

-- ALTER TABLE employee_pro14 RENAME COLUMN emp_name TO full_name;

-- ALTER TABLE employee_pro14 DROP COLUMN department;

-- ALTER TABLE employee_pro14 ALTER COLUMN salary TYPE INT;

-- ALTER TABLE employee_pro14 ALTER COLUMN salary COMMENT 'Monthly salary in INR';

-- ALTER TABLE employee_pro7 SET TBLPROPERTIES ( 'quality' = 'silver',
-- 'modified_by' = 'devops_pipeline' );

-- ALTER TABLE employee_pro7 RENAME TO employee_sigmoid;




-- CREATE TABLE orders (
--     order_id INT,
--     customer_id INT,
--     order_date DATE
-- )
-- USING DELTA
-- PARTITIONED BY (order_date);

-- OPTIMIZE orders
-- ZORDER BY (customer_id);