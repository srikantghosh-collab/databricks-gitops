-- ==============================
-- 1️⃣ CREATE TABLE (Reversible)
-- ==============================
CREATE TABLE employee_v2 (
    emp_id INT,
    emp_name STRING,
    department STRING,
    salary DECIMAL(10,2),
    created_date TIMESTAMP
) USING DELTA;

-- ==============================
-- 2️⃣ INSERT (Not DDL – ignored by rollback logic)
-- ==============================
INSERT INTO employee_v2 VALUES
(1, 'Amit', 'IT', 70000, current_timestamp()),
(2, 'Neha', 'HR', 55000, current_timestamp()),
(3, 'Rohit', 'Finance', 80000, current_timestamp());

-- ==============================
-- 3️⃣ ALTER – ADD COLUMN (Reversible)
-- ==============================
ALTER TABLE employee_v2 ADD COLUMN email STRING;

-- ==============================
-- 4️⃣ ALTER – SET PROPERTIES (Reversible)
-- ==============================
ALTER TABLE employee_v2 SET TBLPROPERTIES (
  'quality' = 'silver',
  'modified_by' = 'gitops_pipeline'
);

-- ==============================
-- 5️⃣ TRUNCATE (Irreversible)
-- ==============================
TRUNCATE TABLE employee_v2;

-- ==============================
-- 6️⃣ DROP (Irreversible)
-- ==============================
DROP TABLE employee_v2;
