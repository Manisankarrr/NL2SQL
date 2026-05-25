-- ============================================================
-- BarberSQL — Full Schema Setup
-- Database: barbershopsql
-- Run this entire file once in MySQL Workbench:
--   1. Open MySQL Workbench
--   2. File → Open SQL Script → select this file
--   3. Click the lightning bolt (Execute All)
-- ============================================================

-- Step 1: Create database if it doesn't exist, then use it
CREATE DATABASE IF NOT EXISTS barbershopsql
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE barbershopsql;

-- Step 2: Drop tables in reverse FK dependency order
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS barbers;
DROP TABLE IF EXISTS services;

-- Step 3: Create tables

CREATE TABLE customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE barbers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    specialty VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE services (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    duration_minutes INT NOT NULL,
    price DECIMAL(8,2) NOT NULL
);

CREATE TABLE appointments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    barber_id INT,
    service_id INT,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status ENUM('scheduled','completed','cancelled') DEFAULT 'scheduled',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (barber_id) REFERENCES barbers(id) ON DELETE SET NULL,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL
);

-- Step 4: Seed data

INSERT INTO customers (name, phone) VALUES
    ('Rahul',   '9876543210'),
    ('Priya',   '9123456789'),
    ('Ravi',    '9988776655'),
    ('Anitha',  '9090909090'),
    ('Karthik', '9001234567');

INSERT INTO barbers (name, specialty) VALUES
    ('Murugan', 'Hair Styling'),
    ('Selvan',  'Beard Grooming'),
    ('Bala',    'Hair Color');

INSERT INTO services (name, duration_minutes, price) VALUES
    ('Haircut',    30, 150.00),
    ('Shave',      20,  80.00),
    ('Hair Color', 60, 400.00),
    ('Beard Trim', 15,  60.00);

INSERT INTO appointments
    (customer_id, barber_id, service_id, appointment_date, appointment_time, status)
VALUES
    (
        (SELECT id FROM customers WHERE name = 'Rahul'),
        (SELECT id FROM barbers  WHERE name = 'Murugan'),
        (SELECT id FROM services WHERE name = 'Haircut'),
        CURDATE(), '10:00:00', 'completed'
    ),
    (
        (SELECT id FROM customers WHERE name = 'Priya'),
        (SELECT id FROM barbers  WHERE name = 'Bala'),
        (SELECT id FROM services WHERE name = 'Hair Color'),
        CURDATE() + INTERVAL 1 DAY, '11:30:00', 'scheduled'
    ),
    (
        (SELECT id FROM customers WHERE name = 'Ravi'),
        (SELECT id FROM barbers  WHERE name = 'Selvan'),
        (SELECT id FROM services WHERE name = 'Shave'),
        CURDATE() + INTERVAL 2 DAY, '14:00:00', 'cancelled'
    ),
    (
        (SELECT id FROM customers WHERE name = 'Anitha'),
        (SELECT id FROM barbers  WHERE name = 'Murugan'),
        (SELECT id FROM services WHERE name = 'Haircut'),
        CURDATE() + INTERVAL 3 DAY, '16:00:00', 'scheduled'
    ),
    (
        (SELECT id FROM customers WHERE name = 'Karthik'),
        (SELECT id FROM barbers  WHERE name = 'Selvan'),
        (SELECT id FROM services WHERE name = 'Beard Trim'),
        CURDATE() + INTERVAL 4 DAY, '09:30:00', 'scheduled'
    ),
    (
        (SELECT id FROM customers WHERE name = 'Rahul'),
        (SELECT id FROM barbers  WHERE name = 'Selvan'),
        (SELECT id FROM services WHERE name = 'Shave'),
        CURDATE() + INTERVAL 5 DAY, '12:00:00', 'scheduled'
    ),
    (
        (SELECT id FROM customers WHERE name = 'Priya'),
        (SELECT id FROM barbers  WHERE name = 'Murugan'),
        (SELECT id FROM services WHERE name = 'Haircut'),
        CURDATE() + INTERVAL 6 DAY, '15:00:00', 'scheduled'
    ),
    (
        (SELECT id FROM customers WHERE name = 'Ravi'),
        (SELECT id FROM barbers  WHERE name = 'Bala'),
        (SELECT id FROM services WHERE name = 'Hair Color'),
        CURDATE() + INTERVAL 7 DAY, '10:30:00', 'scheduled'
    );
