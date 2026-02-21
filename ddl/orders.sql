
CREATE TABLE IF NOT EXISTS employee_v40(
    emp_id INT,
    emp_name STRING,
    department STRING,
    salary DECIMAL(10,2),
    created_date TIMESTAMP
)
USING DELTA;

INSERT INTO employee_v40 VALUES
    (1, 'John', 'IT', 60000, current_timestamp()),
    (2, 'Sara', 'HR', 50000, current_timestamp()),
    (3, 'Mike', 'Finance', 70000, current_timestamp());

ALTER TABLE employee_v40 SET TBLPROPERTIES (
    'delta.logRetentionDuration' = 'interval 30 days',
    'delta.deletedFileRetentionDuration' = 'interval 30 days'
);

ALTER TABLE employee_v40 DROP column salary;