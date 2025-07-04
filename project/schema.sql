
CREATE DATABASE IF NOT EXISTS student_portal;
USE student_portal;

CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    date_posted DATE DEFAULT CURRENT_DATE
);

CREATE TABLE gallery (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_path VARCHAR(255),
    caption VARCHAR(255),
    uploaded_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE faqs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question TEXT,
    answer TEXT
);

CREATE TABLE counselor_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    message TEXT,
    submitted_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
