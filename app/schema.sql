CREATE TABLE IF NOT EXISTS users (
 id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL, email VARCHAR(190) NOT NULL UNIQUE,
 password VARCHAR(255) NOT NULL, role ENUM('employee','support','admin') NOT NULL DEFAULT 'employee'
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS cis (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(190) NOT NULL UNIQUE, kind VARCHAR(90) NOT NULL) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS services (
 id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(190) NOT NULL, description TEXT NOT NULL,
 line VARCHAR(80) NOT NULL, price VARCHAR(190) NOT NULL,
 status ENUM('Эксплуатируется','Готова к эксплуатации','Архив') NOT NULL DEFAULT 'Эксплуатируется'
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS service_cis (service_id INT NOT NULL, ci_id INT NOT NULL, PRIMARY KEY(service_id,ci_id),
 FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE, FOREIGN KEY(ci_id) REFERENCES cis(id)) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS service_links (service_id INT NOT NULL, dependency_id INT NOT NULL, PRIMARY KEY(service_id,dependency_id),
 FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE, FOREIGN KEY(dependency_id) REFERENCES services(id) ON DELETE CASCADE) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS incidents (
 id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(190) NOT NULL, description TEXT NOT NULL,
 service_id INT NOT NULL, author_id INT NOT NULL, assignee_id INT NULL, priority VARCHAR(2) NOT NULL,
 status VARCHAR(30) NOT NULL DEFAULT 'Новая', resolution TEXT NULL,
 created_at DATETIME NOT NULL, responded_at DATETIME NULL, resolved_at DATETIME NULL,
 FOREIGN KEY(service_id) REFERENCES services(id), FOREIGN KEY(author_id) REFERENCES users(id), FOREIGN KEY(assignee_id) REFERENCES users(id)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS incident_cis (incident_id INT NOT NULL, ci_id INT NOT NULL, PRIMARY KEY(incident_id,ci_id),
 FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE, FOREIGN KEY(ci_id) REFERENCES cis(id)) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS history (id INT AUTO_INCREMENT PRIMARY KEY, incident_id INT NOT NULL, user_id INT NOT NULL,
 action TEXT NOT NULL, created_at DATETIME NOT NULL, FOREIGN KEY(incident_id) REFERENCES incidents(id), FOREIGN KEY(user_id) REFERENCES users(id)) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS messages (id INT AUTO_INCREMENT PRIMARY KEY, sender_id INT NOT NULL, recipient_id INT NOT NULL,
 body TEXT NOT NULL, created_at DATETIME NOT NULL, FOREIGN KEY(sender_id) REFERENCES users(id), FOREIGN KEY(recipient_id) REFERENCES users(id)) CHARACTER SET utf8mb4;
