-- Schema base para WebFerramas
-- Ejecutar: mysql -u root -p ferramas < schema.sql

CREATE TABLE IF NOT EXISTS users (
  id_user INT AUTO_INCREMENT PRIMARY KEY,
  correo VARCHAR(120) NOT NULL UNIQUE,
  contraseña VARCHAR(255) NOT NULL,
  usuario VARCHAR(60) NOT NULL UNIQUE,
  descuento_porcentaje INT DEFAULT 0,
  role VARCHAR(20) NOT NULL DEFAULT 'user',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tools (
  id_tool INT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  description TEXT,
  stock INT DEFAULT 0,
  precio INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_tools_name (name),
  INDEX idx_tools_price (precio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pedidos (
  id_pedido INT AUTO_INCREMENT PRIMARY KEY,
  id_user INT NOT NULL,
  estado_pedido VARCHAR(20) NOT NULL DEFAULT 'pendiente',
  monto_total INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pedidos_user FOREIGN KEY (id_user) REFERENCES users(id_user)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pedido_detalle (
  id_detalle INT AUTO_INCREMENT PRIMARY KEY,
  id_pedido INT NOT NULL,
  id_tool INT NOT NULL,
  cantidad INT NOT NULL,
  precio_unitario INT NOT NULL,
  CONSTRAINT fk_detalle_pedido FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido)
    ON DELETE CASCADE,
  CONSTRAINT fk_detalle_tool FOREIGN KEY (id_tool) REFERENCES tools(id_tool)
    ON DELETE RESTRICT,
  INDEX idx_detalle_pedido (id_pedido)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transacciones (
  id_transaccion INT AUTO_INCREMENT PRIMARY KEY,
  id_pedido INT NOT NULL,
  monto_transaccion INT NOT NULL,
  metodo_pago VARCHAR(40) NOT NULL,
  token VARCHAR(128) NULL,
  status VARCHAR(30) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_trans_pedido FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido)
    ON DELETE CASCADE,
  INDEX idx_trans_pedido (id_pedido)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
