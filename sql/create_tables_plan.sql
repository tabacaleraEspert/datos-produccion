-- Tablas para el Plan de Producción (layout V22).
-- Ejecutar en Azure SQL si las tablas no existen.
-- Schema: dbo

-- Planificaciones (Plan por marca/día)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'ProduccionPlanificaciones')
BEGIN
    CREATE TABLE dbo.ProduccionPlanificaciones (
        Id_Plan          INT           NOT NULL,
        Version          NVARCHAR(20)  NULL,
        Id_Proceso       INT           NOT NULL,
        Id_Producto      INT           NOT NULL,
        Id_Marca         INT           NOT NULL,
        Id_TipoTabaco    INT           NOT NULL,
        Id_TipoCajetilla INT           NOT NULL,
        Id_VariedadProducto INT        NOT NULL,
        Fecha            DATE          NOT NULL,
        CantidadAProducir INT          NOT NULL,
        Estado           NVARCHAR(50)  NULL,
        cantidadProducida INT          NULL,
        FechaCarga       DATETIME2(0)  NULL
    );
    PRINT 'Tabla dbo.ProduccionPlanificaciones creada.';
END
GO

-- Real (Real por marca/día)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'ProduccionReal')
BEGIN
    CREATE TABLE dbo.ProduccionReal (
        Id_Plan          INT           NOT NULL,
        Version          NVARCHAR(20)  NULL,
        Id_Proceso       INT           NOT NULL,
        Id_Producto      INT           NOT NULL,
        Id_Marca         INT           NOT NULL,
        Id_TipoTabaco    INT           NOT NULL,
        Id_TipoCajetilla INT           NOT NULL,
        Id_VariedadProducto INT        NOT NULL,
        Fecha            DATE          NOT NULL,
        CantidadProducida INT          NOT NULL,
        Estado           NVARCHAR(50)  NULL,
        FechaCarga       DATETIME2(0)  NULL
    );
    PRINT 'Tabla dbo.ProduccionReal creada.';
END
GO
