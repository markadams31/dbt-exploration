-- Create the warehouse database and the login dbt connects with.
-- Idempotent: safe on container restart.
IF DB_ID('warehouse') IS NULL
    CREATE DATABASE warehouse;
GO

IF SUSER_ID('transformer') IS NULL
    CREATE LOGIN transformer WITH PASSWORD = 'Localdev_2024!', CHECK_POLICY = OFF;
GO

USE warehouse;
IF USER_ID('transformer') IS NULL
    CREATE USER transformer FOR LOGIN transformer;
-- db_owner because dbt creates and drops whole schemas as it materialises.
ALTER ROLE db_owner ADD MEMBER transformer;
GO
