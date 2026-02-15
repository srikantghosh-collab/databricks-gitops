
CREATE TABLE IF NOT EXISTS employees (
  emp_id INT,
  emp_name STRING,
  department STRING,
  salary DECIMAL(10,2),
  created_date TIMESTAMP
) USING DELTA;

INSERT INTO employee VALUES
(1, 'John', 'IT', 60000, current_timestamp()),
(2, 'Sara', 'HR', 50000, current_timestamp()),
(3, 'Mike', 'Finance', 70000, current_timestamp());

ALTER TABLE employee SET TBLPROPERTIES (
  'delta.logRetentionDuration' = 'interval 30 days',
  'delta.deletedFileRetentionDuration' = 'interval 30 days'
);
























