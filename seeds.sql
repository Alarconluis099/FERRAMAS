-- Datos de ejemplo para desarrollo
-- Ejecutar después de schema.sql

INSERT INTO users (correo, contraseña, usuario, descuento_porcentaje, role) VALUES
('admin@example.com', 'scrypt:32768:8:1$x1g6yPppbRCaSMBm$0b27f820a355dc26e21e6150d35b08a9020ae0df2a74d166cc483a5a8b7ad8df8995fc43aa36a020c8e9b7bc46855f1f881045e34a11ee38bd110f12efbddfca', 'admin', 15, 'admin')
ON DUPLICATE KEY UPDATE correo=VALUES(correo);

-- Usuario staff por defecto (password: Staff123!)
INSERT INTO users (correo, contraseña, usuario, descuento_porcentaje, role) VALUES
('staff@example.com', 'scrypt:32768:8:1$ug1AQiTy7AOdWiSa$aac105fc0ff161ebdb38edb8ab569985f39b2bfc5254450c861ac155833dfb2949152b8ed95e622e7061d456ef822352ad27733b63520e44cb1054224fd2468a', 'staff', 10, 'staff')
ON DUPLICATE KEY UPDATE correo=VALUES(correo);

-- Usuario cliente estándar (password: Cliente123!)
INSERT INTO users (correo, contraseña, usuario, descuento_porcentaje, role) VALUES
('cliente@example.com', 'scrypt:32768:8:1$VXASTAYs3DG6kVqr$1e3d15621fb9d22ec220254dc343038677180777d8b23f51de588cede67e9b16e66821396ee9e471822d353559fa30320931a4aa60b4d6c7f52bcf68a6260d71', 'cliente', 5, 'user')
ON DUPLICATE KEY UPDATE correo=VALUES(correo);

INSERT INTO tools (id_tool, name, description, stock, precio) VALUES
(100, 'Martillo', 'Martillo de acero carbono', 100, 19990),
(110, 'Caja de Clavos', 'Clavos estándar 2 pulgadas', 200, 5990),
(120, 'Taladro', 'Taladro percutor 500W', 50, 45990)
ON DUPLICATE KEY UPDATE name=VALUES(name);
