ALTER TABLE EnphaseInterval
    ADD COLUMN ChargedWh INT NULL AFTER ExportedWh,
    ADD COLUMN DischargedWh INT NULL AFTER ChargedWh,
    ADD COLUMN BatterySocPct DECIMAL(5,2) NULL AFTER DischargedWh;