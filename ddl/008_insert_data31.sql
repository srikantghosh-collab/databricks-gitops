USE CATALOG hive_metastore;
USE SCHEMA sigmoid_employee;

INSERT INTO employee_pro31 VALUES
(1, 'John', 'IT', 60000, current_timestamp()),
(2, 'Sara', 'HR', 50000, current_timestamp()),
(3, 'Mike', 'Finance', 70000, current_timestamp()),
(4, 'David', 'IT', 65000, current_timestamp()),
(5, 'Emma', 'HR', 52000, current_timestamp());