
CREATE TABLE IF NOT EXISTS employee_v25 (
    emp_id INT,
    emp_name STRING,
    department STRING,
    salary DECIMAL(10,2),
    created_date TIMESTAMP
 ) USING DELTA;

INSERT INTO employee_v25
(emp_id, emp_name, department, salary, created_date)
VALUES
(1, 'Amit', 'IT', 70000, current_timestamp()),
(2, 'Neha', 'HR', 55000, current_timestamp()),
(3, 'Rohit', 'Finance', 80000, current_timestamp());


ALTER TABLE employee_v25 DROP COLUMN department;

ALTER TABLE employee_v25 ALTER COLUMN salary TYPE INT;

TRUNCATE TABLE employee_v25;
