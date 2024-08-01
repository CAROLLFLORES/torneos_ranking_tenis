create  database if not EXISTS apur;


CREATE TABLE if NOT EXISTS apur.usuario (
    id_usuario INT  AUTO_INCREMENT not null,
    nombre VARCHAR(100),
    apellido varchar (255),
    email varchar(255) not null,
    username VARCHAR(255) not null ,
    password VARCHAR(255) not null,
    fecha  data not null,
    constraint pk_usuarios primary key (id_usuario),
    constraint uq_email UNIQUE(email)      
) ENGINE=InnoDB; 
"""InnoDB = es un motor de almacenamiento transaccional para MySQL, conocido por su soporte de transacciones ACID (Atomicidad, Consistencia, Aislamiento y Durabilidad).
Es el motor de almacenamiento predeterminado en MySQL para nuevas tablas debido a sus características avanzadas.
Cuando creas una tabla en MySQL, puedes especificar el motor de almacenamiento usando la opción ENGINE. Por ejemplo, para crear una tabla usando InnoDB, usarías:
Este comando crea una tabla llamada mi_tabla y especifica que debe usar el motor de almacenamiento InnoDB.
En resumen, ENGINE=InnoDB le indica a MySQL que debe usar el motor InnoDB para la tabla, aprovechando sus características avanzadas para el manejo de datos."""


CREATE TABLE apur.jugador (
    dni INT,
    nombre VARCHAR(45),
    apellido VARCHAR(45),
    sexo CHAR(1),
    foto BLOB NULL
    constraint pk_jugador primary key (dni)
)ENGINE=InnnoDB;



CREATE TABLE apur.categoria (
    id_categoria INT PRIMARY KEY AUTO_INCREMENT,
    nombre_categoria VARCHAR(45)
)ENGINE=InnoDB;


CREATE TABLE apur.partido (
    id_partido INT PRIMARY KEY AUTO_INCREMENT,
    fecha DATE,
    id_categoria INT,
    FOREIGN KEY (id_categoria) REFERENCES categoria(id_categoria)
)ENGINE=InnoDB;


CREATE TABLE apur.resultado_partido (
    id_resultado INT PRIMARY KEY AUTO_INCREMENT,
    id_partido INT,
    id_jugador1 INT,
    id_jugador2 INT,
    resultado_jugador1 INT,
    resultado_jugador2 INT,
    FOREIGN KEY (id_partido) REFERENCES partido(id_partido),
    FOREIGN KEY (id_jugador1) REFERENCES jugador(dni),
    FOREIGN KEY (id_jugador2) REFERENCES jugador(dni)
)ENGINE=InnoDB;

CREATE TABLE apur.ranking (
    id_ranking INT PRIMARY KEY AUTO_INCREMENT,
    id_categoria INT,
    id_jugador INT,
    posicion INT,
    pj INT,
    pg INT,
    puntaje_total_categoria INT,
    puntaje_acumulado INT,
    bimestre INT,
    anio INT,
    FOREIGN KEY (id_categoria) REFERENCES categoria(id_categoria),
    FOREIGN KEY (id_jugador) REFERENCES jugador(dni)
)ENGINE=InnoDB;


CREATE TABLE apur.enfrentamiento (
    id_enfrentamiento INT PRIMARY KEY AUTO_INCREMENT,
    id_jugador1 INT,
    id_jugador2 INT,
    id_partido INT,
    FOREIGN KEY (id_jugador1) REFERENCES jugador(dni),
    FOREIGN KEY (id_jugador2) REFERENCES jugador(dni),
    FOREIGN KEY (id_partido) REFERENCES partido(id_partido)
)ENGINE=InnoDB;











