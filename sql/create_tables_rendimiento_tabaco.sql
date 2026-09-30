-- Tabla RendimientoTabaco (desde Minuta).
-- Ejecutar en Azure SQL si la tabla no existe.
-- Schema: dbo

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'RendimientoTabaco')
BEGIN
    CREATE TABLE dbo.RendimientoTabaco (
        ID                 INT           IDENTITY(1,1) PRIMARY KEY,
        Fecha              DATE          NOT NULL,
        ConsumoTeoricoKg    DECIMAL(18,4) NULL,
        ConsumoRealKg       DECIMAL(18,4) NULL,
        FechaCarga         DATETIME2(0)  NULL
    );
    PRINT 'Tabla dbo.RendimientoTabaco creada.';
END
GO
