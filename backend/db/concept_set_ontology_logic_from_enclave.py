from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from pyspark.sql import SparkSession

spark = SparkSession \
    .builder \
    .appName("Python Spark SQL basic example") \
    .config("spark.jars", "./postgresql-42.5.1.jar") \
    .getOrCreate()
    # .config("spark.jars", "/path_to_postgresDriver/postgresql-42.2.5.jar") \

df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://localhost:5432/databasename") \
    .option("dbtable", "tablename") \
    .option("user", "username") \
    .option("password", "password") \
    .option("driver", "org.postgresql.Driver") \
    .load()

df.printSchema()

CONCEPT_DF = "CONCEPT_DF"
CONCEPT_RELATIONSHIP_DF = "CONCEPT_RELATIONSHIP_DF"
CONCEPT_ANCESTOR_DF = "CONCEPT_ANCESTOR_DF"
vocab_table_aliases = {"concept": CONCEPT_DF, "concept_relationship": CONCEPT_RELATIONSHIP_DF, "concept_ancestor": CONCEPT_ANCESTOR_DF}


def MASTER_QUERY_TEMPLATE(query):
	return f"SELECT C.concept_id, C.concept_name FROM ({query}) C"


def CONCEPT_SET_QUERY_TEMPLATE(conceptIds):
    return f"select concept_id, concept_name from {CONCEPT_DF} where concept_id in (" + ', '.join([str(c_id) for c_id in conceptIds]) + ")"


def CONCEPT_SET_DESCENDANTS_TEMPLATE(conceptIds):
	return f"""select c.concept_id, c.concept_name
from {CONCEPT_DF} c
join {CONCEPT_ANCESTOR_DF} ca on c.concept_id = ca.descendant_concept_id
and ca.ancestor_concept_id in ({', '.join([str(c_id) for c_id in conceptIds])})
and c.invalid_reason is null
"""


def CONCEPT_SET_MAPPED_TEMPLATE(conceptsetQuery):
	return f"""select distinct cr.concept_id_1 as concept_id, c2.concept_name
FROM
(
{conceptsetQuery}
) C
join {CONCEPT_RELATIONSHIP_DF} cr on C.concept_id = cr.concept_id_2 and cr.relationship_id = 'Maps to' and cr.invalid_reason IS NULL
join {CONCEPT_DF} c2 on cr.concept_id_1 = c2.concept_id
"""


def CONCEPT_SET_INCLUDE_TEMPLATE(includeQuery):
	return f"""select distinct I.concept_id, I.concept_name FROM
(
{includeQuery}
) I
"""


def CONCEPT_SET_EXCLUDE_TEMPLATE(excludeQuery):
    return f"""LEFT JOIN
(
{excludeQuery}
) E ON I.concept_id = E.concept_id
WHERE E.concept_id is null
"""


def buildConceptSetSubQuery(concepts: list, descendantConcepts: list):
    queries = []
    if (len(concepts) > 0):
        queries.append(CONCEPT_SET_QUERY_TEMPLATE(concepts))

    if (len(descendantConcepts) > 0):
        queries.append(CONCEPT_SET_DESCENDANTS_TEMPLATE(descendantConcepts))

    return "\nUNION\n".join(queries)


def buildConceptSetMappedQuery(mappedConcepts: list, mappedDescendantConcepts: list):
    conceptSetQuery = buildConceptSetSubQuery(mappedConcepts, mappedDescendantConcepts)
    return CONCEPT_SET_MAPPED_TEMPLATE(conceptSetQuery)


def buildConceptSetQuery(
          concepts: list,
          descendantConcepts: list,
          mappedConcepts: list,
          mappedDesandantConcepts: list):

    if (len(concepts) == 0):
        return f"select concept_id, concept_name from {CONCEPT_DF} where 0=1"

    conceptSetQuery = buildConceptSetSubQuery(concepts, descendantConcepts)

    if (len(mappedConcepts) > 0) or (len(mappedDesandantConcepts) > 0):
        buildConceptSetMappedQuery(mappedConcepts, mappedDesandantConcepts)  # Does this do anything?
        conceptSetQuery += "UNION\n" + buildConceptSetMappedQuery(mappedConcepts, mappedDesandantConcepts)

    return conceptSetQuery


def get_concept_id_list(df):
    return df.select("concept_id").rdd.flatMap(lambda x: x).collect()


def buildExpressionQuery(new_codeset_rows: DataFrame):
    #### Populate each subset of cocnepts from the flags set in each concept set item:
    # (1a) Cache the included concepts:
    included_concepts_df = new_codeset_rows.where(~F.col("isExcluded"))
    # (1b) Get concept_id lists for each included subset
    includeConcepts = get_concept_id_list(included_concepts_df)
    includeDescendantConcepts = get_concept_id_list(
        included_concepts_df.where(F.col("includeDescendants"))
    )
    includeMappedConcepts = get_concept_id_list(
        included_concepts_df.where(F.col("includeMapped"))
    )
    includeMappedDescendantConcepts = get_concept_id_list(
        included_concepts_df.where((F.col("includeMapped")) & (F.col("includeDescendants")))
    )

    # (2a) Cache the excluded concepts:
    excluded_concepts_df = new_codeset_rows.where(F.col("isExcluded"))
    # (2b) Get concept_id lists for each excluded subset
    excludeConcepts = get_concept_id_list(excluded_concepts_df)
    excludeDescendantConcepts = get_concept_id_list(
        excluded_concepts_df.where((F.col("includeDescendants")))
    )
    excludeMappedConcepts = get_concept_id_list(
        excluded_concepts_df.where(F.col("includeMapped"))
    )
    excludeMappedDescendantConcepts = get_concept_id_list(
        excluded_concepts_df.where((F.col("includeMapped")) & (F.col("includeDescendants")))
    )

    # each ArrayList contains the concepts that are used in the sub-query of the codeset expression query
    includeQuery = buildConceptSetQuery(includeConcepts, includeDescendantConcepts, includeMappedConcepts, includeMappedDescendantConcepts)
    conceptSetQuery = CONCEPT_SET_INCLUDE_TEMPLATE(includeQuery)

    if (len(excludeConcepts) > 0):
        excludeQuery = buildConceptSetQuery(excludeConcepts, excludeDescendantConcepts, excludeMappedConcepts, excludeMappedDescendantConcepts)
        excludeConceptsQuery = CONCEPT_SET_EXCLUDE_TEMPLATE(excludeQuery)
        conceptSetQuery += excludeConceptsQuery

    return conceptSetQuery
