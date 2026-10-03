CREATE OR REPLACE VIEW EnergyMonitoring.vw_MonitoringDeviceLocation
AS
SELECT
    md.MonitoringDeviceId,
    md.SourceSystemCode,
    md.SourceDeviceId,
    md.DeviceName,
    mdlh.LocationId,
    l.locationName AS LocationName,
    mdlh.StartDateTime,
    mdlh.EndDateTime
FROM EnergyMonitoring.MonitoringDevice AS md

INNER JOIN EnergyMonitoring.MonitoringDeviceLocationHistory AS mdlh
    ON mdlh.MonitoringDeviceId = md.MonitoringDeviceId
    AND mdlh.IsActive = 1

INNER JOIN orchids.location AS l
    ON l.locationId = mdlh.LocationId

WHERE md.IsActive = 1
  AND l.isActive = 1;