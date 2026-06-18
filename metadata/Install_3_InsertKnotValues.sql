/*
    INSERT KNOT VALUES
    
    Populates the reference data (knots) for the metadata model.
    These are the enumerated values used by anchors and ties.
*/

-- ============================================================
-- CONTAINER TYPE
-- ============================================================

MERGE INTO metadata.COT_ContainerType k
USING (SELECT 'File'  AS val, 1 AS id UNION ALL
       SELECT 'Table',       2 UNION ALL
       SELECT 'View',        3 UNION ALL
       SELECT 'Stage',       4) v
ON k.COT_ContainerType = v.val
WHEN NOT MATCHED THEN INSERT (COT_ID, COT_ContainerType) VALUES (v.id, v.val);

-- ============================================================
-- CONFIGURATION TYPE
-- ============================================================

MERGE INTO metadata.CFT_ConfigurationType k
USING (SELECT 'Workflow' AS val, 1 AS id UNION ALL
       SELECT 'Source',         2 UNION ALL
       SELECT 'Target',         3) v
ON k.CFT_ConfigurationType = v.val
WHEN NOT MATCHED THEN INSERT (CFT_ID, CFT_ConfigurationType) VALUES (v.id, v.val);
