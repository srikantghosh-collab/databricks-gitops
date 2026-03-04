CREATE TABLE orders_v2 (
order_id INT,
customer_id INT,
amount DOUBLE,
order_date DATE
)
USING DELTA
PARTITIONED BY (order_date);
OPTIMIZE orders_v2
ZORDER BY (customer_id);