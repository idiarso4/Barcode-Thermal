-- Drop the table if it exists
DROP TABLE IF EXISTS captureticket;

-- Create the table with the correct structure
CREATE TABLE captureticket (
    id SERIAL PRIMARY KEY,
    plat_no VARCHAR(50),
    date_masuk TIMESTAMP,
    date_keluar TIMESTAMP NULL,
    status VARCHAR(50),
    biaya DECIMAL(10,2) NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vehicle_type VARCHAR(50) NULL
);

-- Insert the ticket data
INSERT INTO captureticket (id, plat_no, date_masuk, status)
VALUES (8429, 'TKT20250414190611_8469', '2025-04-14 19:06:11.048622', 'MASUK'); 