
CREATE TABLE IF NOT EXISTS employee_v27 (
    emp_id INT,
    emp_name STRING,
    department STRING,
    salary DECIMAL(10,2),
    created_date TIMESTAMP
 ) USING DELTA;

INSERT INTO employee_v27
(emp_id, emp_name, department, salary, created_date)
VALUES
(1, 'Amit', 'IT', 70000, current_timestamp()),
(2, 'Neha', 'HR', 55000, current_timestamp()),
(3, 'Rohit', 'Finance', 80000, current_timestamp());

ALTER TABLE employee_v27
SET TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name'
);

ALTER TABLE employee_v27 DROP COLUMN department;

-- 1. Add new column
ALTER TABLE employee_v27 ADD COLUMN salary_int INT;

-- 2. Backfill data
UPDATE employee_v27 SET salary_int = CAST(salary AS INT);

-- 3. Drop old column
ALTER TABLE employee_v27 DROP COLUMN salary;

-- 4. Rename new column
ALTER TABLE employee_v27 RENAME COLUMN salary_int TO salary;


TRUNCATE TABLE employee_v27;
