-- ============================================================
-- BarberSQL — Full Schema Setup
-- Database: barbershopsql
-- Run in MySQL Workbench:
--   File → Open SQL Script → select this file
--   Click the lightning bolt (Execute All, Ctrl+Shift+Enter)
-- ============================================================

CREATE DATABASE IF NOT EXISTS barbershopsql
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE barbershopsql;

-- ── Drop in FK dependency order ──────────────────────────────
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS barbers;
DROP TABLE IF EXISTS services;
DROP EVENT IF EXISTS auto_complete_past_appointments;
SET FOREIGN_KEY_CHECKS = 1;

-- ── Tables ───────────────────────────────────────────────────

CREATE TABLE customers (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    name       VARCHAR(100) NOT NULL,
    phone      VARCHAR(20),
    email      VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE barbers (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    name       VARCHAR(100) NOT NULL,
    specialty  VARCHAR(100),
    is_active  BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE services (
    id               INT PRIMARY KEY AUTO_INCREMENT,
    name             VARCHAR(100) NOT NULL,
    duration_minutes INT NOT NULL,
    price            DECIMAL(8,2) NOT NULL
);

CREATE TABLE appointments (
    id               INT PRIMARY KEY AUTO_INCREMENT,
    customer_id      INT,
    barber_id        INT,
    service_id       INT,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status           ENUM('scheduled','completed','cancelled') DEFAULT 'scheduled',
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (barber_id)   REFERENCES barbers(id)   ON DELETE SET NULL,
    FOREIGN KEY (service_id)  REFERENCES services(id)  ON DELETE SET NULL
);

-- ── Seed: customers ──────────────────────────────────────────

INSERT INTO customers (name, phone) VALUES
    ('Rahul',   '9876543210'),
    ('Priya',   '9123456789'),
    ('Ravi',    '9988776655'),
    ('Anitha',  '9090909090'),
    ('Karthik', '9001234567');

-- ── Seed: barbers ────────────────────────────────────────────

INSERT INTO barbers (name, specialty) VALUES
    ('Murugan', 'Hair Styling'),
    ('Selvan',  'Beard Grooming'),
    ('Bala',    'Hair Color');

-- ── Seed: services ───────────────────────────────────────────

INSERT INTO services (name, duration_minutes, price) VALUES
    ('Haircut',    30, 150.00),
    ('Shave',      20,  80.00),
    ('Hair Color', 60, 400.00),
    ('Beard Trim', 15,  60.00);

-- ── Seed: appointments ───────────────────────────────────────
-- Past appointments are explicitly set as completed.
-- Future appointments use CURDATE() so they are always upcoming
-- regardless of when this schema is executed.

INSERT INTO appointments
    (customer_id, barber_id, service_id, appointment_date, appointment_time, status)
VALUES
    -- past completed
    (
        (SELECT id FROM customers WHERE name='Rahul'),
        (SELECT id FROM barbers   WHERE name='Murugan'),
        (SELECT id FROM services  WHERE name='Haircut'),
        CURDATE() - INTERVAL 6 DAY, '10:00:00', 'completed'
    ),
    (
        (SELECT id FROM customers WHERE name='Priya'),
        (SELECT id FROM barbers   WHERE name='Bala'),
        (SELECT id FROM services  WHERE name='Hair Color'),
        CURDATE() - INTERVAL 5 DAY, '11:30:00', 'completed'
    ),
    (
        (SELECT id FROM customers WHERE name='Ravi'),
        (SELECT id FROM barbers   WHERE name='Selvan'),
        (SELECT id FROM services  WHERE name='Shave'),
        CURDATE() - INTERVAL 4 DAY, '14:00:00', 'completed'
    ),
    (
        (SELECT id FROM customers WHERE name='Anitha'),
        (SELECT id FROM barbers   WHERE name='Murugan'),
        (SELECT id FROM services  WHERE name='Haircut'),
        CURDATE() - INTERVAL 3 DAY, '16:00:00', 'completed'
    ),
    (
        (SELECT id FROM customers WHERE name='Karthik'),
        (SELECT id FROM barbers   WHERE name='Selvan'),
        (SELECT id FROM services  WHERE name='Beard Trim'),
        CURDATE() - INTERVAL 2 DAY, '09:30:00', 'completed'
    ),
    -- past cancelled
    (
        (SELECT id FROM customers WHERE name='Rahul'),
        (SELECT id FROM barbers   WHERE name='Selvan'),
        (SELECT id FROM services  WHERE name='Shave'),
        CURDATE() - INTERVAL 1 DAY, '12:00:00', 'cancelled'
    ),
    -- today
    (
        (SELECT id FROM customers WHERE name='Priya'),
        (SELECT id FROM barbers   WHERE name='Murugan'),
        (SELECT id FROM services  WHERE name='Haircut'),
        CURDATE(), '15:00:00', 'scheduled'
    ),
    -- future scheduled
    (
        (SELECT id FROM customers WHERE name='Ravi'),
        (SELECT id FROM barbers   WHERE name='Bala'),
        (SELECT id FROM services  WHERE name='Hair Color'),
        CURDATE() + INTERVAL 1 DAY, '10:30:00', 'scheduled'
    ),
    (
        (SELECT id FROM customers WHERE name='Anitha'),
        (SELECT id FROM barbers   WHERE name='Selvan'),
        (SELECT id FROM services  WHERE name='Beard Trim'),
        CURDATE() + INTERVAL 2 DAY, '09:00:00', 'scheduled'
    ),
    (
        (SELECT id FROM customers WHERE name='Karthik'),
        (SELECT id FROM barbers   WHERE name='Murugan'),
        (SELECT id FROM services  WHERE name='Haircut'),
        CURDATE() + INTERVAL 3 DAY, '14:00:00', 'scheduled'
    ),
    (
        (SELECT id FROM customers WHERE name='Rahul'),
        (SELECT id FROM barbers   WHERE name='Bala'),
        (SELECT id FROM services  WHERE name='Hair Color'),
        CURDATE() + INTERVAL 4 DAY, '11:00:00', 'scheduled'
    ),
    (
        (SELECT id FROM customers WHERE name='Priya'),
        (SELECT id FROM barbers   WHERE name='Selvan'),
        (SELECT id FROM services  WHERE name='Shave'),
        CURDATE() + INTERVAL 5 DAY, '16:00:00', 'scheduled'
    );

-- ── Auto-status event ────────────────────────────────────────
-- Enables the MySQL event scheduler and creates an event that
-- runs every hour to mark past scheduled appointments as completed.
-- This means status is always accurate without manual updates.

SET GLOBAL event_scheduler = ON;

DELIMITER $$

CREATE EVENT auto_complete_past_appointments
ON SCHEDULE EVERY 1 HOUR
STARTS NOW()
DO
BEGIN
    UPDATE appointments
    SET status = 'completed'
    WHERE appointment_date < CURDATE()
      AND status = 'scheduled';
END$$

DELIMITER ;

-- ── Verify ───────────────────────────────────────────────────

SELECT
    a.id,
    c.name            AS customer,
    a.appointment_date,
    a.appointment_time,
    a.status
FROM appointments a
JOIN customers c ON a.customer_id = c.id
ORDER BY a.appointment_date;