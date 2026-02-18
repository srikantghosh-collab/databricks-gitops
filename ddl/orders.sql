
CREATE TABLE IF NOT EXISTS employee_v26 (
    emp_id INT,
    emp_name STRING,
    department STRING,
    salary DECIMAL(10,2),
    created_date TIMESTAMP
 ) USING DELTA;

INSERT INTO employee_v26
(emp_id, emp_name, department, salary, created_date)
VALUES
(1, 'Amit', 'IT', 70000, current_timestamp()),
(2, 'Neha', 'HR', 55000, current_timestamp()),
(3, 'Rohit', 'Finance', 80000, current_timestamp());

ALTER TABLE employee_v26
SET TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name'
);

ALTER TABLE employee_v26 DROP COLUMN department;


ALTER TABLE employee_v26 ADD COLUMN salary_int INT;


UPDATE employee_v26 SET salary_int = CAST(salary AS INT);


ALTER TABLE employee_v26 DROP COLUMN salary;


ALTER TABLE employee_v26 RENAME COLUMN salary_int TO salary;


TRUNCATE TABLE employee_v26;

ALTER TABLE employee_v26 ADD COLUMN country STRING;
