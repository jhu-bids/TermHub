from argparse import ArgumentParser
import re
import util

'''
transform pipeline.sql files from enclave code workbook git exports to
code repository formatted pyspark.

examples below
'''

# the code workbook version looks like:
cwb_example = '''
@transform_pandas(
Output(rid="ri.foundry.main.dataset.ed57bcba-a5eb-4505-ba31-8da5d615ff09"),
concept=Input(rid="ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772"),
concept_ancestor=Input(rid="ri.foundry.main.dataset.c5e0521a-147e-4608-b71e-8f53bcdbe03c")
)
SELECT    c1.vocabulary_id AS ancestor_vocabulary_id
    , ca.ancestor_concept_id
    , c1.concept_name AS ancestor_concept_name
    , ca.min_levels_of_separation
    , ca.max_levels_of_separation
    , c2.vocabulary_id AS descendant_vocabulary_id
    , ca.descendant_concept_id
    , c2.concept_name AS descendant_concept_name
FROM concept_ancestor ca
JOIN concept c1 ON ca.ancestor_concept_id = c1.concept_id
JOIN concept c2 ON ca.descendant_concept_id = c2.concept_id
'''

# the code repository version should look sort of like:
cr_example = '''
@transform_df(
    Output("/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/transforms-sql/src/main/concept_ancestor_plus"),
    ca=Input("/N3C Export Area/OMOP Vocabularies/concept_ancestor"),
    c=Input("/N3C Export Area/OMOP Vocabularies/concept"),
)
def concept_ancestor_plus(ca, c, ctx):
    spark = SparkSession.builder.getOrCreate()
    ca.createOrReplaceTempView('concept_ancestor')
    c.createOrReplaceTempView('c1')
    c.createOrReplaceTempView('c2')
    df = spark.sql(\'''                                         # don't include the backslash
        SELECT    c1.vocabulary_id AS ancestor_vocabulary_id
                , ca.ancestor_concept_id
                , c1.concept_name AS ancestor_concept_name
                , ca.min_levels_of_separation
                , ca.max_levels_of_separation
                , c2.vocabulary_id AS descendant_vocabulary_id
                , ca.descendant_concept_id
                , c2.concept_name AS descendant_concept_name
        FROM concept_ancestor ca
        JOIN c1 ON ca.ancestor_concept_id = c1.concept_id
        JOIN c2 ON ca.descendant_concept_id = c2.concept_id
    \''')
    return df
'''

def split_document(doc):
        queries = re.split('\n*@transform_pandas', doc)[1:]
        return queries

def convert_workbook_node(query):
        return query

def run(input_path: str, output_path: str) -> None:
        with util.smart_open(input_path) as f:
                sql = ''.join(f.readlines())

        in_queries = split_document(whole_doc)
        out_queries = [convert_workbook_node(query) for query in in_queries]
        print(out_queries)

def get_parser():
        """Add required fields to parser.

        Returns:
            ArgumentParser: Argeparse object.
        """
        package_description = ''
        parser = ArgumentParser(description=package_description)

        parser.add_argument(
                '-i', '--input_path',
                # default='./pipeline.sql',
                help='Path to folder where you want output file')
        parser.add_argument(
                '-o', '--output_path',
                # default='./pipeline.py',
                help='Path to where you want output file')

        return parser

def cli():
        """Command line interface for package.

        Side Effects: Executes program."""
        parser = get_parser()
        kwargs = parser.parse_args()
        kwargs_dict: Dict = vars(kwargs)

        args = {key: kwargs_dict[key] for key in ['input_path', 'output_path']}
        run(**args)
        return

if __name__ == '__main__':
        cli()
