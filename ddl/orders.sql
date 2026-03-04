CREATE TABLE orders_v1 (
order_id INT,
customer_id INT,
amount DOUBLE,
order_date DATE
)
USING DELTA
PARTITIONED BY (order_date);

-- Optimization
OPTIMIZE orders_v1
ZORDER BY (customer_id);