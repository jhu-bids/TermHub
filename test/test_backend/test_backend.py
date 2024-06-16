"""Tests for backend web server and utilities"""
import os
from typing import Dict, Union

import pandas as pd
import requests
import sys
import unittest
from dateutil.parser import parse
from pathlib import Path
from requests import Response
from urllib.parse import urljoin

THIS_TEST_DIR = Path(os.path.dirname(__file__))
TEST_DIR = THIS_TEST_DIR.parent
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.analysis import InvalidCompareSchemaError, counts_compare_schemas, counts_over_time
from backend.routes.db import get_concepts, get_researchers, get_cset_members_items


TEST_DIR = os.path.dirname(__file__)
BACKEND_URL_BASE = 'http://127.0.0.1:8000/'


class TestBackend(unittest.TestCase):

    @staticmethod
    def _upload_file(file_path, url) -> Response:
        with open(file_path, 'r') as file:
            file_data = file.read()
            response: Response = requests.post(url, data={'csv': file_data})
        if response.status_code == 200:
            print('INFO: File successfully uploaded to ', url)
        else:
            print('ERROR: Failed to upload file: ', response.status_code, file=sys.stderr)
        return response

    # todo: this was refactored, so need a new test
    @unittest.skip("Skipping. Test not implemented.")
    def test_hierarchify_list_of_parent_kids(self):
        """test hierarchify_list_of_parent_kids()"""
        # # Case 1
        # parent_child_list = [(3290077, 3219427), (3219427, 3429308), (3219427, 3458111), (3457827, 3465375)]
        # expected = {
        #     3290077: {
        #         3219427: {
        #             3429308: {},
        #             3458111: {}
        #         }
        #     },
        #     3457827: {
        #         3465375: {},
        #     }
        # }
        # actual = hierarchify_list_of_parent_kids(parent_child_list, [3290077, 3457827])
        # self.assertEqual(actual, expected)
        #
        # # Case 2
        # parent_child_list = [
        #     ('1', '1.1'), ('1', '1.2'), ('2', '2.1'), ('2', '2.2'), ('1.2', '1.2.1'), ('1.2.1', '1.2.1.1')]
        # expected = {
        #     "1": {
        #         "1.1": {},
        #         "1.2": {
        #             "1.2.1": {
        #                 "1.2.1.1": {}
        #             }
        #         }
        #     },
        #     "2": {
        #         "2.2": {},
        #         "2.1": {}
        #     }
        # }
        # actual = hierarchify_list_of_parent_kids(parent_child_list, ['1', '2'])
        # self.assertEqual(actual, expected)
        #
        # # Case 3 (as of 2022/12/21. won't reflect any changes made since)
        # # http://127.0.0.1:8000/cr-hierarchy?rec_format=flat&codeset_id=400614256|411456218|419757429|484619125
        # selected_parent_ids = [45913937, 45939036, 4232595, 4104506, 44806369, 1569489, 46269776, 46270376, 44803835, 3150869, 45951072, 3248359, 37312153, 40545662, 44804338, 257583, 45921434, 1569488, 3557638, 44792264, 3429308, 3141647, 46269802, 3457827, 3380541, 3124989, 4315386, 3099599, 44788836, 4119298, 45926650, 3401254, 46269782, 44830115, 44782563, 3375330, 4163244, 3151160, 4152420, 3261225, 4152418, 40345758, 4166508, 4244339, 46270082, 3293658, 45562456, 3400715, 36684335, 45766865, 45766728, 261895, 4015948, 37108581, 3330760, 40545246, 3188624, 46269777, 3337245, 4112831, 4270073, 4125953, 4225553, 46270322, 45768965, 40337130, 4083395, 4295034, 3066368, 3438741, 3124988, 40547144, 42689618, 45940512, 46274062, 45561757, 40345759, 3339509, 3124991, 45768912, 46269783, 45940320, 3288849, 4152292, 45769438, 42690682, 45929656, 46269771, 44805004, 4172303, 46273454, 4279553, 37396521, 3370221, 40316544, 40337129, 261048, 4217558, 4269178, 4017191, 40307554, 3105910, 40300138, 40545247, 46284163, 4245292, 40337132, 40316543, 3266697, 42536208, 40316547, 4286497, 3255273, 40337131, 3267799, 3168355, 3153572, 45946655, 3141621, 46274059, 45939199, 4143828, 45906019, 44824289, 440748, 4206340, 3458794, 3124987, 3150934, 3446337, 3472327, 3451367, 4215256, 3079647, 3467849, 317009, 4017293, 4265861, 3280432, 4136683, 4050961, 44792263, 3150866, 40664816, 40345717, 138056, 44788780, 37206717, 3080832, 4214589, 40395880, 40395876, 4119300, 45572171, 3420840, 4138077, 44803711, 4022592, 3352113, 3163091, 45906038, 3161077, 37206130, 44805092, 45924581, 45917669, 4191479, 3274552, 3441776, 3439569, 3425801, 4144104, 44824288, 3297885, 40595784, 3150865, 3240676, 40395537, 45938784, 3458111, 3137830, 44832424, 3201654, 3124967, 44810352, 259043, 2617553, 44809514, 44807085, 37108580, 443801, 45911260, 3460598, 45768911, 4200851, 3248228, 46274060, 40307535, 4120262, 3156397, 44789217, 3398938, 3476610, 44799960, 3387915, 40307557, 3420635, 4235703, 40395885, 4017187, 3150938, 3150937, 45920275, 45769352, 3247833, 40546234, 4017026, 4015951, 3397511, 3435332, 4059321, 46273452, 4191827, 44834769, 3285967, 40395887, 3281529, 3150936, 3150935, 40316545, 4214588, 3465375, 3430639, 4120261, 4170623, 258780, 45939829, 40545665, 45932474, 3449892, 42539549, 4015819, 3460949, 4110056, 4144889, 3137832, 3124996, 3304776, 45766868, 4246105, 3452171, 4112669, 44803708, 40395881, 3330199, 3105909, 3260480, 4110642, 4155470, 4145356, 3155659, 45586674, 37208352, 4008897, 3267178, 46269773, 3150868, 3124993, 46274124, 3250032, 44804958, 45909236, 4137804, 40345760, 42690582, 3375458, 3099585, 3342936, 44807895, 45909769, 45601134, 4057432, 3337088, 4196712, 46269786, 3477945, 45924727, 4307038, 3099598, 3468370, 3313569, 45768910, 3180839, 45936352, 40544275, 45557625, 44831278, 4155465, 37310241, 45946099, 3141624, 40395890, 4211648, 3159274, 44831284, 3425430, 45601133, 3150940, 254980, 45543270, 40545663, 4051466, 45936680, 4328679, 45910696, 3297761, 4179205, 3239995, 40297857, 3349096, 36716970, 3164757, 4190882, 3466410, 3074097, 3304420, 40307556, 44803846, 40345721, 3271036, 3431337, 4138392, 44793048, 3439675, 4081994, 4233784, 45913803, 256716, 4194289, 3067242, 3275332, 4142738, 252942, 3236083, 44832423, 3472300, 4112670, 764677, 4017182, 46269772, 45945887, 3240140, 3326360, 3297228, 3403760, 762862, 4250891, 45948183, 3151089, 4312524, 45955254, 45772937, 4207479, 40300133, 42538508, 252658, 4145497, 3456756, 3365063, 46269775, 3141622, 4141622, 44810117, 3310337, 45907864, 46269785, 3124992, 3329107, 45596282, 3150871, 40628141, 40436413, 3442305, 4017183, 40563020, 40307536, 4215257, 4017025, 3078828, 44792265, 44833611, 37108745, 3218006, 4141621, 45581860, 40395882, 3228802, 3254024, 4152417, 46269767, 44791725, 40297859, 44807127, 3125023, 44788789, 4230358, 4050732, 40297860, 45949000, 46269774, 44792262, 4141978, 3315821, 3459941, 3245639, 4152913, 45920173, 44831279, 4051985, 40545251, 44807733, 4277596, 40566169, 4250128, 4148124, 45586675, 4152911, 36684328, 4053917, 4335886, 45562457, 40545249, 40316548, 4015947, 4189168, 3091356, 4313588, 3150867, 46269784, 40395878, 3382999, 313236, 4325853, 257581, 3162019, 3275788, 40481763, 45572170, 45576951, 46270029, 3427698, 3120383, 3309832, 40545664, 4212099, 4123253, 3099584, 46269788, 3271865, 44810118, 4235401, 45766866, 3064432, 45938316, 4225554, 44826679, 3105912, 40640771, 40307538, 45943393, 4155468, 44806050, 3264337, 3099596, 40300136, 4156136, 257905, 40395891, 3308988, 3124995, 45773005, 45591558, 4145496, 256448, 46269781, 4069449, 46269779, 42536541, 44803920, 3451853, 42536648, 259055, 3436486, 45769350, 45917166, 4193019, 3477978, 4110048, 45771045, 45938447, 3105913, 40337153, 4309833, 4143474, 3332964, 45907865, 4278831, 3377749, 37116845, 44831280, 44783610, 252341, 40337152, 45572169, 44805087, 44805089, 45943394, 46269787, 3265859, 3475208, 45908186, 45548116, 3380698, 45769351, 4112828, 3141623, 261889, 3287129, 45572168, 46273487, 4017192, 4138760, 4050734, 3400990, 4244061, 45769442, 46273635, 43530693, 42690688, 3447664, 45955255, 3228357, 4166517, 3438966, 4147509, 255841, 44837135, 45924275, 4308356, 45567265, 45927141, 44821988, 45907808, 4137525, 44821987, 3430638, 3478313, 3375675, 40483397, 3099587, 45557624, 3105911, 3137829, 4169883, 4017184, 45955026, 43530745, 45769441, 4177944, 46269789, 3343637, 3472500, 3137831, 44810131, 45768963, 4155473, 3241129, 3219427, 3234322, 3163987, 2101898, 3263624, 44807940, 45557626, 46270028, 3158690, 45772073, 42690663, 40545666, 45936903, 3345773, 44824287, 261325, 3424363, 3172954, 3112998, 45954259, 45948999, 3369638, 44808268, 4050733, 45941262, 40566165, 45948039, 44788824, 3257682, 1569490, 37312152, 3376743, 40561687, 3293711, 45591559, 3151306, 4057952, 45944525, 2617798, 40389375, 44808238, 3452456, 3124994, 3125021, 3379169, 45591560, 3141648, 3262344, 765431, 40300134, 44788825, 44793424, 45543269, 42539089, 3308688, 43021747, 258564, 1569491, 4080516, 45576952, 4245676, 42689665, 4309350, 4119299, 40395889, 3454187, 40395540, 40664872, 3432874, 44793074, 46269770, 44804959, 40545248, 3256726, 312950, 45766727, 4155469, 44788779, 45581859, 45548118, 4110051, 3377072, 3124964, 4146581, 3161263, 4056405, 3661412, 4281815, 3427139, 45954260, 44805091, 44805093, 3124990, 4112836, 764949, 3475819, 3254509, 46269780, 3067259, 46269790, 3079384, 4283362, 45946240, 3115991, 45769443, 42689663, 35609846, 45945309, 3124228, 40545669, 46269801, 40545253, 3466361, 4321845, 46273462, 40345719, 40316546, 46270030, 40381380, 3379022, 3248443, 761844, 45935503, 44820889, 45909454, 45567266, 42536649, 44805920, 46269778, 3282266, 4144757, 43530700, 44823144, 36674599, 3314546, 44837136, 44788781, 4125022, 4301938, 4110635, 46270573, 4120260, 40303860, 3328829, 3314864, 40546155, 3112997, 42535716, 4110177, 3290077, 37109103, 45768964, 3403922, 4211530, 2108536, 45769389, 4193588, 4271333, 4075237, 35609847, 42538744, 45944861, 45757063, 3273133, 3290814, 4112826, 45949333, 3137833, 40563017, 3227834, 2617554, 3426709, 42536207, 761986, 4209097, 4125951, 45548117, 4161595]
        # selected_roots: List[int] = top_level_cids(selected_parent_ids)
        # with open(os.path.join(os.path.dirname(__file__), 'all_subsumes_tuples_2022_12_21.pickle'), 'rb') as f:
        #     parent_child_list = pickle.load(f)
        # result = hierarchy_list_of_parent_kids(parent_child_list, selected_roots)
        # actual_subset = {}  # todo: result[...]
        # expected_subset = {}  # todo
        # self.assertEqual(1, 1)  # todo
        pass


    # todo: _upload_file has to be changed
    #  a. to do something like the frontend: axios.post(url, {csv: data})
    #  b. create instance of: class UploadCsvVersionWithConcepts
    @unittest.skip("Skipping tests for incomplete feature. See: https://github.com/jhu-bids/TermHub/issues/799")
    def test_route_csv_upload_new_cset_version_with_concepts(self):
        """Test: Upload new cset version from CSV"""
        url = urljoin(BACKEND_URL_BASE, 'upload-csv-new-cset-version-with-concepts')
        csv_path = os.path.join(
            TEST_DIR, 'input', 'test_enclave_wrangler', 'test_dataset_upload', 'type-2-diabetes-mellitus.csv')
        response: Response = self._upload_file(csv_path, url)
        self.assertEqual(response.json()['result'], 'success')

    @unittest.skip("Deactivated test. Not yet implemented.")  # todo: implement
    def test__current_counts_and_deltas(self):
        """Test _current_counts_and_deltas()
        todo: Can make sure that all row counts are >0 for all tables that are defined in the db/config.py, i.e. in
         DERIVED_TABLE_DEPENDENCY_MAP (keys or anywhere in values) or STANDALONE_TABLES.
        todo: Would be good to have a test for count deltas where at least 1 table delta that refresh day != 0
        """
        pass

    @unittest.skip("Deactivated test. Not yet implemented.")  # todo: implement
    def test_negative_deltas(self):
        """Tests to detect any unanticipated negative deltas (decreases in row counts) at any point in the history of
        the database and its refreshes, especially brand new deltas.
        todo: any negative delta ideally in the db should be looked at and approved, otherwise throw some err. should be
         a scheduled / cron test, not a test that runs on PRs on pushes. and we should have a config in db/config.py
         where we list out which deltas we've looked at and either approved as expected / OK, or otherwise addressed.
         Thus, any delta found not in this config would throw an err. Could also make test more performant by only
         checking deltas for any new data / comparisons newer than the last approved case in the config.
        """
        pass

    @unittest.skip("Deactivated test. See docstring for more info.")
    def test_counts_compare_schemas(self):
        """Test counts_compare_schemas()

        In addition to assertions, also ensures that counts_compare_schemas() runs without error.

        Performance: counts_compare_schemas() taking 2 minutes as of 2024/05/26.
        todo: If re-activated, make this ideally run not on PRs to develop, as it is long running. It makes sense to
         have it run on PR to main, or push to develop or main. It especially makes sense to have it run routinely, as
         it could be used to detect delta issues with the refresh, even when no changes were made in the codebase.
        todo: maybe reactivate one day. deactivated for several reasons:
         - as of 2024/05/26, we're relying on Azure backups, and not on this feature anymore.
         - the test that was here didn't make sense
           - I couldn't think of a good test case for this, other than running it and making sure it doesn't error, and
            that the columnns and values are formatted as expected.
           - if a row count was 0 on a backup schema, it could be (and is likely) because of a newly added table, and
           it's not worth keeping track of which tables got added when just so this could test something.
           - if a row count was 0 for the current schema, this is important. However, this belongs on a test for
             _current_counts_and_deltas(), so see that test for more.
           - if counts are the same between the two schemas, that's of course ok
           - if counts are the same increased, that is often expected, so ok
           - this one maybe has merit, but not for this test. See: test_negative_deltas()

        todo: consider pickling df2. However, if counts_compare_schemas() changes, this will either break or otherwise
         could possibly lead to inaccurate results.
        todo: Might want to use a newer backup than n3c_backup_20230221. How often to update? Any way to auto update?
         Any reason not automate to compare against like the 2nd or nth oldest backup, or maybe by the nearest date
         greater than some time ago, e.g. 2 weeks?
        todo: performance: df1 and df2 both tally 'n3c'. would have to refactor significantly though to only fetch that
         data once. maybe this test is being set up strangely because it's testing both (i) a known, statically declared
         backup, and (ii) the latest backup detected in the DB.
        """
        # Part 1: Ensure that the most recent backup is newer than a previous known backup
        # - If no backup schema in counts, df1 will be None. If shchema passed for df2 doesn't exist, it will be None.
        df1: Union[pd.DataFrame, None] = counts_compare_schemas(compare_schema='most_recent_backup', verbose=False)
        try:
            df2: Union[pd.DataFrame, None] = counts_compare_schemas(compare_schema='n3c_backup_20230414', verbose=False)
        except InvalidCompareSchemaError:
            df2 = None
        if df1 is not None and df2 is not None:
            df1_date = parse(df1.columns[3][11:])
            df2_date = parse(df2.columns[3][11:])
            self.assertGreater(df1_date, df2_date)  # compare date substring w/in schema name
        # todo: think of a test, if applicable. see docstring for why this test was removed
        # if df1 is not None:
        #     # Part 2: Ensure that table rows are not empty
        #     schema_column = df1.columns[2]
        #     schema_backup_column = df1.columns[3]
        #     for _index, row in df1.iterrows():
        #         for schema in [schema_column, schema_backup_column]:
        #             self.assertGreater(row[schema], 0, msg=f"Table '{row['table']}' had 0 rows in schema '{schema}'")

    def test_counts_over_time(self):
        """test counts_over_time()"""
        consistent_critical_tables = [
            'all_csets', 'code_sets', 'concept', 'concept_ancestor', 'concept_relationship',
            'concept_relationship_plus', 'concept_set_container', 'concept_set_counts_clamped', 'concept_set_members',
            'concept_set_version_item', 'concepts_with_counts', 'cset_members_items',
            'deidentified_term_usage_by_domain_clamped', 'omopconceptset', 'omopconceptsetcontainer', 'researcher']
        # dates where 1+ consistent, critical tables had row count of 0. I actually don't know why this was, but the
        #  most important thing for this test is to encounter new errors. Otherwise, it can test to see if something
        #  broke in our records or how the function is down counts. But for rather than worrying about these anomolous
        #  past cases, we ought to be concerned about the present state of the DB and the code.
        known_anomalous_dates = ['2023-06-29', '2023-11-05']
        df = counts_over_time(verbose=False)
        # newest_backup_col: handles case where newest backup was not the only backup that day, e.g. '2023-05-03 2'
        newest_run_col_date_str = str(max([parse(x.split()[0]) for x in df.columns])).split()[0]
        newest_run_col = max([x for x in df.columns if x.startswith(newest_run_col_date_str)])
        for date_col in df.columns:
            table_counts: Dict[str, int] = df[date_col].to_dict()
            for table_name, row_count in table_counts.items():
                if table_name == "COMMENT":  # all entries are table names except for this 1
                    # Test: no db count run should have an empty 'COMMENT' field
                    self.assertFalse(df[date_col][table_name].isspace(), msg=f"Empty 'COMMENT' field in run {date_col}")
                else:
                    if date_col in known_anomalous_dates:  # see comment for: known_anomalous_dates
                        continue
                    # Other than `consistent_critical_tables`, tables may be added/removed, so skip for older backups
                    if date_col != newest_run_col and table_name not in consistent_critical_tables:
                        continue
                    # Test: all consistent, critical tables should have non-zero row counts
                    elif table_name in consistent_critical_tables:
                        self.assertGreater(row_count, 0, msg=f"Table '{table_name}' had 0 rows in run '{date_col}'")
                    # Test: all other row counts should be non-zero
                    # todo: reactivate when/if counts_over_time() filters out tables that no longer exist
                    # self.assertGreater(df[col][row], 0, msg=f"Table '{row}' had 0 rows in run '{col}'")

    def test_get_concepts(self):
        """ Tests get_related_csets in backend/routes/app.py."""
        self.assertEqual(get_concepts([396155663, 643758668]),[])

    """ This test is based on the cr_hierarchy function so it would need to be changed since that function may retire,
    but is a data counts test still needed?
    def test_cr_hierarchy_data_counts(self):

        '''Test backend: cr_hierarchy, defined in backend/app.py
        Prereq: Server must be running'''
        url = BACKEND_URL_BASE + 'cr-hierarchy'
        response = requests.get(url=url, params={
            'codeset_ids': '400614256|87065556'
        }).json()
        self.assertEqual(len(response['data_counts']), 0)
    """

    # todo: re-implement? get_related_csets() no longer exists. but we do have a way to see related csets in TermHub,
    #  so how can we test that?
    # def test_get_related_csets(self):
    #     """ Test the related csets output of cr_hierarchy defined in backend/routes/app.py.
    #     The related csets output is given by get_related_csets in backend/routes/app.py.
    #     """
    #     related_csets = get_related_csets([396155663,643758668])
    #     related_cs_ids = [concept['codeset_id']for concept in related_csets]
    #     self.assertEqual(related_cs_ids,[93330599, 128430450, 201986476, 396155663, 643758668])
    #     self.assertEqual(related_csets[2],{'codeset_id': 201986476, 'concept_set_version_title': '[VSAC] Social Determinants of Health Goals (v2)',
    #                       'project': 'RP-4A9E27', 'concept_set_name': '[VSAC] Social Determinants of Health Goals',
    #                       'alias': '[VSAC] Social Determinants of Health Goals', 'source_application': 'UNITE',
    #                       'source_application_version': '2.0', 'codeset_created_at': '2022-03-16 18:47:09.939000+00:00',
    #                       'atlas_json': None, 'is_most_recent_version': True, 'version': 2.0, 'comments': None,
    #                       'codeset_intention': 'Clinical Focus: The value sets in this group represent all of the individual domain goals identified by the Gravity Project; Data Element Scope: Supports the Gravity SDOH Clinical Care FHIR Implementation guide for the exchange of goal resource elements.; Inclusion Criteria: Includes SNOMED CT goals that have been identified through the Gravity Project community consensus voting process',
    #                       'limitations': 'Exclusion Criteria: N/A', 'issues': None, 'update_message': 'Initial version.',
    #                       'codeset_status': 'Finished', 'has_review': True, 'reviewed_by': None, 'codeset_created_by': '6387db50-9f12-48d2-b7dc-e8e88fdf51e3',
    #                       'provenance': 'Steward: The Gravity Project; OID: 2.16.840.1.113762.1.4.1247.71; Code System(s): SNOMEDCT; Definition Type: Grouping; Definition Version: Latest; Accessed: 2022-02-23 15:28:52; dih_id:1000000232\n\nset include descendants = FALSE',
    #                       'atlas_json_resource_url': None, 'parent_version_id': None, 'authoritative_source': 'The Gravity Project',
    #                       'is_draft': False, 'codeset_rid': 'ri.phonograph2-objects.main.object.199e59df-b414-4742-9fde-564de4a885ce',
    #                       'project_id': None, 'assigned_informatician': None, 'assigned_sme': None, 'container_status': 'Under Construction',
    #                       'stage': 'Awaiting Editing', 'container_intention': None, 'n3c_reviewer': None, 'archived': False,
    #                       'container_created_by': '6387db50-9f12-48d2-b7dc-e8e88fdf51e3', 'container_created_at': '2022-02-24 00:06:05.027000+00:00',
    #                       'container_rid': 'ri.phonograph2-objects.main.object.f2a45883-78d4-4cd8-a994-0d5a0dcdeb45',
    #                       'distinct_person_cnt': 4425, 'total_cnt': 8825, 'counts': {'Expression item and member -- no flags': 21, 'Expression item only -- includeDescendants': 1, 'Expression items': 22, 'Members': 21},
    #                       'concepts': '21', 'researchers': {'6387db50-9f12-48d2-b7dc-e8e88fdf51e3': ['container_created_by', 'codeset_created_by']},
    #                       'selected': False, 'intersecting_concepts': 2, 'recall': 1.0, 'precision': 0.09523809523809523})
    #     selected_csets = [cset for cset in related_csets if cset['selected']]
    #     self.assertEqual(selected_csets,[396155663,643758668])

    def test_get_researchers(self):
        """Test get_researchers()"""
        # todo: re-activate this alterantive method? Or should this go into another test?
        #  Why did we ever call get_related_csets() as part of this test?
        #  it would seem that the proper test for the line below would be for: get_all_researcher_ids()
        # related_csets = get_related_csets([396155663, 643758668])  # get_related_csets() doesn't exist
        # researcher_ids = get_all_researcher_ids(related_csets)
        # self.assertEqual(get_researchers(list(researcher_ids)), expected)
        researchers = {
            '48fd3b68-84fc-47e7-bdf4-3de94554b986': {
                'multipassId': '48fd3b68-84fc-47e7-bdf4-3de94554b986',
                'institutionsId': 'https://ror.org/00za53h95',
                'name': 'Lisa Eskenazi',
                'emailAddress': 'leskena2@jh.edu', 'unaPath': 'InCommon',
                'signedDua': True,
                'citizenScientist': False, 'internationalScientistWithDua': False,
                'institution': 'Johns Hopkins University',
                'orcidId': '0000-0001-8693-7838',
                'rid': 'ri.phonograph2-objects.main.object.40351088-da7e-4be5-8562-b9085ab659c6'},
            '6387db50-9f12-48d2-b7dc-e8e88fdf51e3': {
                'citizenScientist': None,
                'emailAddress': 'termhub-support@jh.edu',
                'institution': 'Johns Hopkins University BIDS',
                'institutionsId': None,
                'internationalScientistWithDua': None,
                'multipassId': '6387db50-9f12-48d2-b7dc-e8e88fdf51e3',
                'name': 'UNITEConceptSetBulkImportUser',
                'orcidId': None,
                'rid': None,
                'signedDua': None,
                'unaPath': None},
            '4bf7076c-6723-49cc-b4e5-f6c6ada1bdae': {
                'citizenScientist': False,
                'emailAddress': 'lehmann@jhmi.edu',
                'institution': 'Johns Hopkins University',
                'institutionsId': 'https://ror.org/00za53h95',
                'internationalScientistWithDua': False,
                'multipassId': '4bf7076c-6723-49cc-b4e5-f6c6ada1bdae',
                'name': 'Harold Lehmann',
                'orcidId': '0000-0002-7698-219X',
                'rid': 'ri.phonograph2-objects.main.object.5dff2d61-20b3-43eb-9f7d-934a9c19d0a7',
                'signedDua': True,
                'unaPath': 'InCommon'},
            'fake-id': {
                'multipassId': 'fake-id',
                'name': 'unknown',
                'emailAddress': 'unknown'}
        }
        for obj_id in researchers.keys():
            actual: Dict[str, Dict] = get_researchers(obj_id)
            expected: Dict[str, Dict] = {obj_id: researchers[obj_id]}
            self.assertEqual(actual, expected)
        self.assertEqual(get_researchers(list(researchers.keys())), researchers)

    def test_get_cset_members_items(self):
        """Test test_get_cset_members_items()"""
        key = lambda d: f"{d['codeset_id']}.{d['concept_id']}"
        csmi = get_cset_members_items([396155663, 643758668]).sort(key=key)
        expected = [
            {'codeset_id': 643758668.0, 'concept_id': 4091006, 'csm': True,
             'item': True, 'item_flags': 'includeDescendants', 'isExcluded': False,
             'includeDescendants': True, 'includeMapped': False},
            {'codeset_id': 396155663.0, 'concept_id': 4052321, 'csm': True, 'item': True,
             'item_flags': '', 'isExcluded': False, 'includeDescendants': False, 'includeMapped': False},
            {'codeset_id': 643758668.0, 'concept_id': 4052321, 'csm': True, 'item': True,
             'item_flags': 'includeDescendants', 'isExcluded': False, 'includeDescendants': True,
             'includeMapped': False},
            {'codeset_id': 396155663.0, 'concept_id': 4091006, 'csm': True,
             'item': True, 'item_flags': '', 'isExcluded': False, 'includeDescendants': False, 'includeMapped': False}
        ].sort(key=key)
        self.assertEquals(csmi, expected)

    def test_get_cset_members_items__cols(self):
        """Test test_get_cset_members_items() using columns param.

        Even though same codeset IDs as test_get_cset_members_items(), should reduce distinct rows from 4 to 2."""
        key = lambda d: {d['concept_id']}
        csmi = get_cset_members_items(
            [396155663, 643758668], columns=['concept_id', 'vocabulary_id', 'standard_concept']).sort(key=key)
        expected = [
            {'concept_id': 4091006, 'standard_concept': 'S', 'vocabulary_id': 'SNOMED'},
            {'concept_id': 4052321, 'standard_concept': 'S', 'vocabulary_id': 'SNOMED'}].sort(key=key)
        self.assertEquals(csmi, expected)
