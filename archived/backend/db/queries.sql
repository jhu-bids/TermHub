


-- from https://unite.nih.gov/workspace/data-integration/code/repos/ri.stemma.main.repository.aea80f94-828b-4795-9603-c3228b153414/contents/refs%2Fheads%2Fmaster/transforms-python/src/myproject/datasets/concept_set_items_to_all_concept_ids.py
-- Concept Set Ontology > Concept Set Ontology logic > concept_set_items_to_all_concept_ids.py
CONCEPT_DF (codeset_items):
codeset_id	item_id	                                concept_id	isExcluded	includeDescendants	includeMapped	annotation	                    created_by	                            created_at	                source_application
1000076438	0b273fed-91c8-491e-8716-e2675b0b26be	45770902	true	    false	            false	        Generated from Parent Dataset	51ffdc0e-e7e1-440e-bdab-9fbfe552dd1b	2023-01-09T18:29:17.842Z	TermHub
1000076438	006b4ccc-4e70-4583-903b-d32881ec78fd	37396524	false	    true	            false	        Generated from Parent Dataset	51ffdc0e-e7e1-440e-bdab-9fbfe552dd1b	2023-01-09T18:29:17.842Z	TermHub
1000076438	01b968c9-0198-4c0e-b305-cda204a76cd6	4024659	    true	    false	            false	        Generated from Parent Dataset	51ffdc0e-e7e1-440e-bdab-9fbfe552dd1b	2023-01-09T18:29:17.842Z	TermHub
1000076438	07aa4e64-f4df-45ab-a124-23c29d9b56b0	35626042	true	    false	            false		                                    6387db50-9f12-48d2-b7dc-e8e88fdf51e3	2023-01-09T18:29:34.781Z	TermHub
-- line 70, query:
select distinct I.concept_id, I.concept_name
FROM (
    select concept_id, concept_name
    from CONCEPT_DF
    where concept_id in (45606061, 35208592, 45591691, 45533840, 45572343, 45591702)
) I;

-- line 71, master_query:
SELECT C.concept_id, C.concept_name
FROM (
    select distinct I.concept_id, I.concept_name
    FROM (
        select concept_id, concept_name
        from CONCEPT_DF
        where concept_id in (45606061, 35208592, 45591691, 45533840, 45572343, 45591702)
    ) I
) C

