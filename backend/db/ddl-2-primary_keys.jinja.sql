
-- Primary keys --------------------------------------------------------------------------------------------------------
-- concept
DO $$
    BEGIN
        if NOT EXISTS (SELECT constraint_name
                       FROM information_schema.table_constraints
                       -- schema has dot at end, have to strip it
                       WHERE constraint_schema = SUBSTRING('{{schema}}' FROM 1 FOR (LENGTH('{{schema}}') - 1))
                         AND table_name = 'concept'
                         AND constraint_type = 'PRIMARY KEY') then
            ALTER TABLE {{schema}}concept ADD PRIMARY KEY (concept_id);
        end if;
    END $$;

-- code_sets
DO $$
    BEGIN
        if NOT EXISTS (SELECT constraint_name
                       FROM information_schema.table_constraints
                       WHERE constraint_schema = SUBSTRING('{{schema}}' FROM 1 FOR (LENGTH('{{schema}}') - 1))
                         AND table_name = 'code_sets'
                         AND constraint_type = 'PRIMARY KEY') then
            ALTER TABLE {{schema}}code_sets ADD PRIMARY KEY (codeset_id);
        end if;
    END $$;

-- fetch_audit
DO $$
    BEGIN
        if NOT EXISTS (SELECT constraint_name FROM information_schema.table_constraints WHERE table_name = 'fetch_audit' AND constraint_type = 'PRIMARY KEY') then
            ALTER TABLE fetch_audit ADD PRIMARY KEY ("table", "primary_key", status_initially);
        end if;
    END $$;