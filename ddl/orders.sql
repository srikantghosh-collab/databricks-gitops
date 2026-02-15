
ALTER TABLE employee_master DROP COLUMN department;

ALTER TABLE employee_master ALTER COLUMN salary TYPE INT;

TRUNCATE TABLE employee_master;

DROP TABLE employee_master;

