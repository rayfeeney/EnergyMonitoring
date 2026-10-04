CREATE TABLE EnergyMonitoring.GreenhouseTargetLocationMap
(
    LocationId              INT NOT NULL,
    TargetRuleLocationName  VARCHAR(100) NOT NULL,

    PRIMARY KEY (LocationId)
);