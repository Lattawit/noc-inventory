CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    device_type VARCHAR(30) NOT NULL,
    vendor VARCHAR(50),
    vlan INT,
    status VARCHAR(10) NOT NULL DEFAULT 'up',
    location_id INT REFERENCES locations(id) ON DELETE SET NULL,
    last_checked TIMESTAMP,
    notes TEXT
);

INSERT INTO locations (name, description) VALUES
('Server Room', 'Main data center rack A'),
('Floor 1 IDF', 'Access switches for floor 1'),
('Floor 2 IDF', 'Access switches for floor 2');

INSERT INTO devices (hostname, ip_address, device_type, vendor, vlan, status, location_id, notes) VALUES
('core-sw01', '10.0.0.1', 'Switch', 'Cisco', 1, 'up', 1, 'Core L3 switch'),
('edge-rtr01', '10.0.0.254', 'Router', 'Cisco', 1, 'up', 1, 'Internet edge router'),
('fw01', '10.0.0.253', 'Firewall', 'Fortinet', 1, 'up', 1, 'Perimeter firewall'),
('acc-sw11', '10.0.10.2', 'Switch', 'Cisco', 10, 'up', 2, 'Floor 1 access switch'),
('ap-f2-01', '10.0.20.10', 'Access Point', 'Ubiquiti', 20, 'down', 3, 'Needs replacement');