
CREATE TABLE employee_v9 (
    emp_id INT,
    emp_name STRING,
    department STRING,
    salary DECIMAL(10,2),
    created_date TIMESTAMP
 ) USING DELTA;

 INSERT INTO employee_v9 VALUES
 (1, 'Amit', 'IT', 70000, current_timestamp()),
 (2, 'Neha', 'HR', 55000, current_timestamp()),
 (3, 'Rohit', 'Finance', 80000, current_timestamp());


 ALTER TABLE employee_v9 ADD COLUMN email STRING;

 ALTER TABLE employee_v9 SET TBLPROPERTIES (
   'quality' = 'silver',
   'modified_by' = 'gitops_pipeline'
 );

