-- Создание пользователя для репликации
CREATE USER repl_user REPLICATION LOGIN PASSWORD '123';

-- Создание базы данных
CREATE DATABASE tg_bot;

-- Переключение на созданную базу данных
\connect tg_bot;
CREATE TABLE IF NOT EXISTS emails (
        id SERIAL PRIMARY KEY,
        email VARCHAR(120) UNIQUE
);
CREATE TABLE IF NOT EXISTS phones (
        id SERIAL PRIMARY KEY,
        phone_number VARCHAR(20) UNIQUE
);
INSERT INTO emails (email) VALUES ('test@example.com');
INSERT INTO emails (email) VALUES ('coolemail@yandex.com');
INSERT INTO phones (phone_number) VALUES ('89775217911');
INSERT INTO phones (phone_number) VALUES ('+7(900)6667788');
