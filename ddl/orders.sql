CREATE TABLE IF NOT EXISTS employee_v32 (
    emp_id INT,
    emp_name STRING,
    department STRING,
    salary DECIMAL(10,2),
    created_date TIMESTAMP
)
USING DELTA;

INSERT INTO employee_v32 VALUES
    (1, 'John', 'IT', 60000, current_timestamp()),
    (2, 'Sara', 'HR', 50000, current_timestamp()),
    (3, 'Mike', 'Finance', 70000, current_timestamp());

ALTER TABLE employee_v32 SET TBLPROPERTIES (
    'delta.logRetentionDuration' = 'interval 30 days',
    'delta.deletedFileRetentionDuration' = 'interval 30 days'
);

ALTER TABLE employee_v32 ADD COLUMNS (email STRING);

-- REQUIRED before any RENAME COLUMN
ALTER TABLE employee_v32 SET TBLPROPERTIES ('delta.columnMapping.mode' = 'name');

ALTER TABLE employee_v32 RENAME COLUMN emp_name TO full_name;

ALTER TABLE employee_v32 ALTER COLUMN salary COMMENT 'Monthly salary in INR';

ALTER TABLE employee_v32 SET TBLPROPERTIES (
    'quality' = 'silver',
    'modified_by' = 'devops_pipeline'
);

ALTER TABLE employee_v32 RENAME TO employee_master;
