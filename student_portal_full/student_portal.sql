-- Create database
CREATE DATABASE IF NOT EXISTS student_portal;
USE student_portal;
DROP TABLE users;
-- Users table (students, teachers, admins)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    student_identifier VARCHAR(30) UNIQUE,
    role ENUM('admin', 'teacher', 'student') NOT NULL
);

-- Subjects table (optional, can be linked with materials)
CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- Materials table (uploaded files like PDFs)
CREATE TABLE IF NOT EXISTS materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT,
    title VARCHAR(200),
    description TEXT,
    filename VARCHAR(300),
    uploaded_by INT,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    date DATE NOT NULL,
    status ENUM('present', 'absent') NOT NULL,
    marked_by INT,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (marked_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (student_id, date) -- Only one record per student per day
);

CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_name VARCHAR(100),
    status ENUM('Present', 'Absent'),
    date DATE,
    marked_by VARCHAR(100)
);


select * from  users;