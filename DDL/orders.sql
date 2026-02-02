CREATE TABLE IF NOT EXISTS orders (
  id INT,
  amount INT
);

ALTER TABLE orders ADD COLUMN discount INT;
DROP TABLE orders;
