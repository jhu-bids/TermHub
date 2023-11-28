DROP TABLE IF EXISTS concept_graph CASCADE;

CREATE TABLE IF NOT EXISTS concept_graph AS (
     SELECT ancestor_concept_id AS source_id,
            -- 'Child of' AS relationship_id,
            descendant_concept_id AS target_id
     FROM concept_ancestor
     WHERE min_levels_of_separation = 1
     /*
     UNION
     SELECT concept_id_1,
            relationship_id,
            concept_id_2
     FROM concept_relationship
     WHERE relationship_id IN ('Is a', 'Replaces')
      */
);

CREATE INDEX cg_idx1 ON concept_graph(source_id);

CREATE INDEX cg_idx2 ON concept_graph(target_id);

/*
        # load_csv(con, 'relationship', 'dataset', schema='n3c')
        # rels = sql_query(con, f"""
        #     SELECT concept_id_1, concept_id_2 -- , relationship_id
        #     FROM n3c.concept_relationship cr
        #     JOIN relationship r ON cr.relationship_id = r.relationship_id
        #     WHERE r.defines_ancestry=1 and r.is_hierarchical=1
        # """)
        # rels = sql_query(con, f"""
        #     SELECT ancestor_concept_id, descendant_concept_id
        #     FROM n3c.concept_ancestor
        #     WHERE min_levels_of_separation = 1
        # """)
        query = f"""
            SELECT * FROM (
                SELECT ancestor_concept_id AS source_id, descendant_concept_id AS target_id
                FROM n3c.concept_ancestor
                WHERE min_levels_of_separation = 1
                -- LIMIT 1000
            ) x
            UNION
            SELECT * FROM (
                SELECT concept_id_1, concept_id_2
                FROM CONCEPT_RELATIONSHIP
                WHERE relationship_id = 'Subsumes'
                -- LIMIT 1000
            ) y
        """
 */
 SELECT 1; -- in case ending on a comment breaks the ddl parser