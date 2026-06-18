/*
    CREATE CONFIGURATION MANAGEMENT PROCEDURES

    Store and manage workflow JSON definitions in the metadata
    CF_Configuration anchor, using the same model as the SQL Server
    version's workflow.xml storage.
*/

-- ============================================================
-- UPSERT CONFIGURATION
-- ============================================================

CREATE OR REPLACE PROCEDURE metadata._ConfigurationUpsert(
    CONFIG_NAME VARCHAR,
    CONFIG_CONTENT VARCHAR,
    CONFIG_TYPE VARCHAR DEFAULT 'Workflow'
)
RETURNS INT
LANGUAGE SQL
AS
$$
BEGIN
    LET cf_id INT;
    LET cft_id TINYINT;
    LET now_ts TIMESTAMP_TZ := SYSDATE();

    -- Look up configuration type knot
    SELECT CFT_ID INTO :cft_id FROM metadata.CFT_ConfigurationType WHERE CFT_ConfigurationType = :CONFIG_TYPE;

    -- Find existing configuration by name
    SELECT cf.CF_ID INTO :cf_id
    FROM metadata.CF_Configuration cf
    JOIN metadata.CF_NAM_Configuration_Name nam ON nam.CF_NAM_CF_ID = cf.CF_ID
    WHERE nam.CF_NAM_Configuration_Name = :CONFIG_NAME;

    IF (:cf_id IS NULL) THEN
        -- Create new configuration
        SELECT metadata.CF_Configuration_ID_SEQ.NEXTVAL INTO :cf_id;
        INSERT INTO metadata.CF_Configuration (CF_ID) VALUES (:cf_id);

        INSERT INTO metadata.CF_NAM_Configuration_Name (CF_NAM_CF_ID, CF_NAM_Configuration_Name)
        VALUES (:cf_id, :CONFIG_NAME);

        INSERT INTO metadata.CF_TYP_Configuration_Type (CF_TYP_CF_ID, CF_TYP_CFT_ID)
        VALUES (:cf_id, :cft_id);

        INSERT INTO metadata.CF_CNT_Configuration_Content (CF_CNT_CF_ID, CF_CNT_Configuration_Content, CF_CNT_ChangedAt)
        VALUES (:cf_id, :CONFIG_CONTENT, :now_ts);
    ELSE
        -- Update content (historized: insert new version)
        INSERT INTO metadata.CF_CNT_Configuration_Content (CF_CNT_CF_ID, CF_CNT_Configuration_Content, CF_CNT_ChangedAt)
        VALUES (:cf_id, :CONFIG_CONTENT, :now_ts);
    END IF;

    RETURN :cf_id;
END;
$$;

-- ============================================================
-- GET CONFIGURATION
-- ============================================================

CREATE OR REPLACE PROCEDURE metadata._ConfigurationGet(
    CONFIG_NAME VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
    LET result VARCHAR;

    SELECT CF_CNT_Configuration_Content INTO :result
    FROM metadata.lCF_Configuration
    WHERE CF_NAM_Configuration_Name = :CONFIG_NAME;

    RETURN :result;
END;
$$;

-- ============================================================
-- LIST CONFIGURATIONS
-- ============================================================

CREATE OR REPLACE PROCEDURE metadata._ConfigurationList()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
    LET result VARCHAR DEFAULT '';

    SELECT LISTAGG(CF_NAM_Configuration_Name || ' | ' || CF_TYP_CFT_ConfigurationType || ' | ' || CF_CNT_ChangedAt, '\n')
    INTO :result
    FROM metadata.lCF_Configuration
    GROUP BY 1=1;

    RETURN :result;
END;
$$;

-- ============================================================
-- DELETE CONFIGURATION
-- ============================================================

CREATE OR REPLACE PROCEDURE metadata._ConfigurationDelete(
    CONFIG_NAME VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
    LET cf_id INT;

    SELECT cf.CF_ID INTO :cf_id
    FROM metadata.CF_Configuration cf
    JOIN metadata.CF_NAM_Configuration_Name nam ON nam.CF_NAM_CF_ID = cf.CF_ID
    WHERE nam.CF_NAM_Configuration_Name = :CONFIG_NAME;

    IF (:cf_id IS NULL) THEN
        RETURN 'Not found: ' || :CONFIG_NAME;
    END IF;

    DELETE FROM metadata.CF_CNT_Configuration_Content WHERE CF_CNT_CF_ID = :cf_id;
    DELETE FROM metadata.CF_TYP_Configuration_Type WHERE CF_TYP_CF_ID = :cf_id;
    DELETE FROM metadata.CF_NAM_Configuration_Name WHERE CF_NAM_CF_ID = :cf_id;
    DELETE FROM metadata.TR_formed_CF_from WHERE CF_ID_from = :cf_id;
    DELETE FROM metadata.CF_Configuration WHERE CF_ID = :cf_id;

    RETURN 'Deleted: ' || :CONFIG_NAME;
END;
$$;
