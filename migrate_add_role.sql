-- Migración: añadir columna role a tabla users si no existe y poblar valores por defecto.
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';
-- Normalizar valores nulos o vacíos
UPDATE users SET role='user' WHERE role IS NULL OR role='';
-- Promocionar usuario llamado 'admin' si existe
UPDATE users SET role='admin' WHERE usuario='admin';
