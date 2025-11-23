-- Archivo opcional: ejecutar manualmente si prefieres aplicar índices fuera de la app
-- Añade índices para acelerar búsquedas por correo y usuario en la tabla users
-- Ejecutar en MySQL (reemplaza `ferramas` por tu base de datos si es distinto):

USE `ferramas`;

-- Índice para busquedas por correo (útil en login por correo)
CREATE INDEX IF NOT EXISTS idx_users_correo ON users (correo);

-- Índice para búsquedas por usuario (útil en login por nombre de usuario)
CREATE INDEX IF NOT EXISTS idx_users_usuario ON users (usuario);

-- FULLTEXT index recomendado para búsquedas de herramientas (name, description)
-- Mejora búsquedas tipo 'MATCH...AGAINST' frente a LIKE '%q%'.
CREATE FULLTEXT INDEX IF NOT EXISTS idx_tools_fulltext ON tools (name, description);

-- Nota: si tu versión de MySQL no soporta `IF NOT EXISTS` en CREATE INDEX,
-- ejecuta en su lugar (comprobar antes si el índice existe):
-- SHOW INDEX FROM users WHERE Column_name='correo';
-- SHOW INDEX FROM users WHERE Column_name='usuario';
