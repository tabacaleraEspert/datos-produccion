-- Tabla RendimientoReal para eficiencias de máquinas (desde Minuta).
-- Ejecutar en Azure SQL si la tabla no existe.
-- Schema: dbo

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'RendimientoReal')
BEGIN
    CREATE TABLE dbo.RendimientoReal (
        ID                 INT           IDENTITY(1,1) PRIMARY KEY,
        id_maquina         INT           NOT NULL,
        Fecha              DATE          NOT NULL,
        Turno              NVARCHAR(10)   NOT NULL,
        Eficiencia         DECIMAL(10,2) NULL,
        Velocidad          DECIMAL(18,4) NULL,
        Unidad             NVARCHAR(50)  NULL,
        RendimientoDeseado DECIMAL(18,4) NULL,
        VelocidadDeseado   DECIMAL(18,4) NULL,
        FechaCarga         DATETIME2(0)  NULL
    );
    PRINT 'Tabla dbo.RendimientoReal creada.';
END
GO
