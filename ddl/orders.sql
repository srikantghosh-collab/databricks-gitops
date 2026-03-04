CREATE TABLE orders
(
order_id INT,
customer_id INT,
amount DOUBLE,
order_date DATE
)
USING DELTA
PARTITIONED BY (order_date);