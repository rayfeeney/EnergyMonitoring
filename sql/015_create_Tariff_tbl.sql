CREATE TABLE EnergyMonitoring.Tariff
(
    TariffId                    INT NOT NULL AUTO_INCREMENT,
    SupplierName                VARCHAR(100) NOT NULL,
    TariffName                  VARCHAR(200) NOT NULL,
    EffectiveFromDate           DATE NOT NULL,
    EffectiveToDate             DATE NULL,
    ImportRatePencePerKWh       DECIMAL(10,4) NOT NULL,
    StandingChargePencePerDay   DECIMAL(10,4) NOT NULL,
    ExportRatePencePerKWh       DECIMAL(10,4) NULL,
    ExitFeeGBP                  DECIMAL(10,2) NULL,
    ExitFeeAppliesUntilDate     DATE NULL,

    PRIMARY KEY (TariffId)
);