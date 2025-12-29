-- Emergency Response Platform Database Initialization
-- This script creates the database and sets up proper indexes for optimal performance

-- Create database (run this manually if needed)
-- CREATE DATABASE emergency_response CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CREATE DATABASE emergency_response_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CREATE DATABASE emergency_response_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE emergency_response;

-- Create indexes for optimal performance (these will be created by SQLAlchemy, but documented here)

-- Users table indexes
-- PRIMARY KEY (id) - automatically created
-- UNIQUE KEY (email) - automatically created
-- INDEX idx_role (role) - created by model definition

-- Volunteer profiles indexes  
-- PRIMARY KEY (id) - automatically created
-- INDEX idx_location (latitude, longitude) - for spatial queries
-- INDEX idx_availability (availability_status) - for filtering available volunteers
-- FOREIGN KEY (user_id) REFERENCES users(id) - cascade delete

-- Skills table indexes
-- PRIMARY KEY (id) - automatically created
-- UNIQUE KEY (name) - automatically created
-- INDEX idx_category (category) - for filtering by skill category

-- Volunteer skills indexes
-- PRIMARY KEY (id) - automatically created
-- UNIQUE KEY unique_volunteer_skill (volunteer_id, skill_id) - prevent duplicates
-- INDEX idx_verification_status (verification_status) - for admin queries
-- INDEX idx_volunteer_verified (volunteer_id, verification_status) - for matching
-- FOREIGN KEY (volunteer_id) REFERENCES volunteer_profiles(id) - cascade delete
-- FOREIGN KEY (skill_id) REFERENCES skills(id) - cascade delete
-- FOREIGN KEY (verified_by) REFERENCES users(id) - set null on delete

-- Emergency requests indexes
-- PRIMARY KEY (id) - automatically created
-- INDEX idx_location_priority (latitude, longitude, priority_level) - for matching
-- INDEX idx_status_created (status, created_at) - for dashboard queries
-- INDEX idx_authority (authority_id) - for authority dashboard
-- FOREIGN KEY (authority_id) REFERENCES users(id) - cascade delete

-- Emergency required skills indexes
-- PRIMARY KEY (id) - automatically created
-- UNIQUE KEY unique_emergency_skill (emergency_id, skill_id) - prevent duplicates
-- FOREIGN KEY (emergency_id) REFERENCES emergency_requests(id) - cascade delete
-- FOREIGN KEY (skill_id) REFERENCES skills(id) - cascade delete

-- Assignments indexes
-- PRIMARY KEY (id) - automatically created
-- UNIQUE KEY unique_assignment (emergency_id, volunteer_id) - prevent duplicates
-- INDEX idx_volunteer_status (volunteer_id, status) - for volunteer dashboard
-- INDEX idx_emergency_status (emergency_id, status) - for emergency tracking
-- FOREIGN KEY (emergency_id) REFERENCES emergency_requests(id) - cascade delete
-- FOREIGN KEY (volunteer_id) REFERENCES volunteer_profiles(id) - cascade delete

-- Activity logs indexes
-- PRIMARY KEY (id) - automatically created
-- INDEX idx_user_action (user_id, action) - for user activity queries
-- INDEX idx_entity (entity_type, entity_id) - for entity activity queries
-- INDEX idx_created_at (created_at) - for chronological queries
-- FOREIGN KEY (user_id) REFERENCES users(id) - set null on delete

-- Performance optimization settings
SET GLOBAL innodb_buffer_pool_size = 268435456; -- 256MB, adjust based on available memory
SET GLOBAL query_cache_size = 67108864; -- 64MB query cache
SET GLOBAL query_cache_type = 1; -- Enable query cache

-- Ensure proper character set for emoji and international characters
ALTER DATABASE emergency_response CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Create a user for the application (adjust credentials as needed)
-- CREATE USER 'emergency_app'@'localhost' IDENTIFIED BY 'secure_password_here';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON emergency_response.* TO 'emergency_app'@'localhost';
-- FLUSH PRIVILEGES;