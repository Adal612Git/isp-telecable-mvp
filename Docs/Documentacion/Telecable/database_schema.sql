-- SQL schema for MVP system
-- This script creates a PostgreSQL database with tables for users, roles,
-- customers, products, orders, order items, payments, logs and authentication tokens.
-- It uses mostly standard SQL, with PostgreSQL-specific SERIAL data types for
-- auto-incremented identifiers. Adapt data types if using another RDBMS.

-- Create the database (execute this outside of psql or with superuser privileges)
-- Uncomment the next lines if you need to create the database yourself. Replace
-- "sistema_mvp" with your desired database name.
-- CREATE DATABASE sistema_mvp
--     WITH ENCODING 'UTF8';

-- Connect to the database before running the remainder of this file.
-- \c sistema_mvp

-- Table of roles used to group permissions.
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- Table of application users. Store only hashed passwords.
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Many‑to‑many association between users and roles.
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- Table of customers (could correspond to users or external clients).  If a
-- customer is also a user of your application, the optional user_id column
-- links the two.
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(30),
    address TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Table of products or services offered by the system.
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'MXN',
    stock INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Orders placed by customers. Each order belongs to a customer and can have
-- multiple associated items. The total_amount field can be computed in
-- application code or via triggers.
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'MXN',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Items belonging to an order. Each item references a product and stores the
-- quantity and unit price at the time of the order.
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Payments associated with orders. This table stores minimal information about
-- payments; adjust the fields according to your payment gateway integration.
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    payment_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'MXN',
    payment_method VARCHAR(50) NOT NULL,
    status VARCHAR(30) NOT NULL,
    transaction_reference VARCHAR(100),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Application logs for auditing and diagnostics.  Store an optional user_id,
-- the action performed, the entity affected, and a free‑form description.
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    entity VARCHAR(100),
    record_id INTEGER,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Authentication tokens for session management or API access.  Each token has
-- an expiration and references a user.  Use secure random values for the
-- token field.
CREATE TABLE auth_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Example indexes to speed up queries.  Add more indexes to suit your access patterns.
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_payments_order_id ON payments(order_id);

