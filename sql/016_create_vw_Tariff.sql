CREATE OR REPLACE VIEW EnergyMonitoring.vw_Tariff
AS
SELECT
    TariffId,
    SupplierName,
    TariffName,
    EffectiveFromDate,
    EffectiveToDate,
    ImportRatePencePerKWh,
    StandingChargePencePerDay,
    ExportRatePencePerKWh,
    ExitFeeGBP,
    ExitFeeAppliesUntilDate
FROM EnergyMonitoring.Tariff;