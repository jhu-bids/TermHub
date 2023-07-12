-- Primary keys --------------------------------------------------------------------------------------------------------
-- ALTER TABLE {{schema}}concept ADD PRIMARY KEY(concept_id); -- fixing in case primary key already exists
DO $$
    BEGIN
        if NOT EXISTS (SELECT constraint_name FROM {{schema}}information_schema.table_constraints WHERE table_name = 'concept' AND constraint_type = 'PRIMARY KEY') then
            ALTER TABLE {{schema}}concept ADD PRIMARY KEY (concept_id);
        end if;
    END $$;

-- ALTER TABLE {{schema}}code_sets ADD PRIMARY KEY(codeset_id);
DO $$
    BEGIN
        if NOT EXISTS (SELECT constraint_name FROM {{schema}}information_schema.table_constraints WHERE table_name = 'code_sets' AND constraint_type = 'PRIMARY KEY') then
            ALTER TABLE {{schema}}code_sets ADD PRIMARY KEY (codeset_id);
        end if;
    END $$;