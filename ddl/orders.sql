
-- CREATE TABLE IF NOT EXISTS employee_pro14 (
--     emp_id INT,
--     emp_name STRING,
--     department STRING,
--     salary DECIMAL(10,2),
--     created_date TIMESTAMP
-- )
-- USING DELTA;

-- INSERT INTO employee_pro14 VALUES
-- (1, 'John', 'IT', 60000, current_timestamp()),
-- (2, 'Sara', 'HR', 50000, current_timestamp()),
-- (3, 'Mike', 'Finance', 70000, current_timestamp());

-- ALTER TABLE employee_pro14 SET TBLPROPERTIES (
--     'delta.logRetentionDuration' = 'interval 30 days',
--     'delta.deletedFileRetentionDuration' = 'interval 30 days'
-- );
-- ALTER TABLE employee_pro14 ADD COLUMNS (email STRING);

-- ALTER TABLE employee_pro14 RENAME COLUMN emp_name TO full_name;

-- ALTER TABLE employee_pro14 DROP COLUMN department;

-- ALTER TABLE employee_pro14 ALTER COLUMN salary TYPE INT;

-- ALTER TABLE employee_pro14 ALTER COLUMN salary COMMENT 'Monthly salary in INR';

-- ALTER TABLE employee_pro14 SET TBLPROPERTIES ( 'quality' = 'silver',
-- 'modified_by' = 'devops_pipeline' );

-- ALTER TABLE employee_pro14 RENAME TO employee_sigmoid;

DROP TABLE employee_pro2;


-- CREATE TABLE orders (
--     order_id INT,
--     customer_id INT,
--     order_date DATE
-- )
-- USING DELTA
-- PARTITIONED BY (order_date);

-- OPTIMIZE orders
-- ZORDER BY (customer_id);