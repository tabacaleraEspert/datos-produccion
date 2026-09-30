-- Tabla ProduccionDiariaPorTurno (desde Minuta).
-- Ejecutar en Azure SQL si la tabla no existe.
-- Schema: dbo

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'ProduccionDiariaPorTurno')
BEGIN
    CREATE TABLE dbo.ProduccionDiariaPorTurno (
        ID                 INT           IDENTITY(1,1) PRIMARY KEY,
        Id_Maquina         INT           NOT NULL,
        Fecha              DATE          NOT NULL,
        Turno              NVARCHAR(10)  NOT NULL,
        CantidadProducida  INT           NOT NULL,
        FechaCarga         DATETIME2(0)  NULL
    );
    PRINT 'Tabla dbo.ProduccionDiariaPorTurno creada.';
END
GO
