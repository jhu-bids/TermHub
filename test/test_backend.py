"""Tests

How to run:
    python -m unittest discover

TODO's
 - Test framework: Current implementation is ad-hoc for purposes of development.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urljoin
from dateutil.parser import parse
import requests
import unittest

from requests import Response

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.analysis import counts_compare_schemas, counts_over_time
from backend.routes.graph import subgraph

TEST_DIR = os.path.dirname(__file__)
BACKEND_URL_BASE = 'http://127.0.0.1:8000/'
COUNT_TEST_EXCEPTIONS = ['concept_set_json', 'rxnorm_med_cset', 'small_snomed']


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
        # result = hierarchify_list_of_parent_kids(parent_child_list, selected_roots)
        # actual_subset = {}  # todo: result[...]
        # expected_subset = {}  # todo
        # self.assertEqual(1, 1)  # todo
        pass

    def test_csets_update(self):
        """Test backend: csets_update
        Prereq: Server must be running"""
        # TODO: make a put request: requests.put(url, data, params, header)
        # TODO: Change this to make a temporary copy of the file, update that, push, then delete tempfile & push again.
        # TODO: can improve by using 'mock':
        #  https://betterprogramming.pub/why-you-should-use-a-put-request-instead-of-a-post-request-13b593b6e67c
        url = BACKEND_URL_BASE + 'datasets/csets'
        response = requests.put(url=url, json={
            'dataset_path': 'test/heroes.csv',
            'row_index_data_map': {
                3: {
                    'first_name': 'Spider',
                    'last_name': 'Man'
                }
            }
        }).json()
        self.assertEqual(response['result'], 'success')

    # TODO: _upload_file has to be changed
    #  a. to do something like the frontend: axios.post(url, {csv: data})
    #  b. create instance of: class UploadCsvVersionWithConcepts
    def test_route_csv_upload_new_cset_version_with_concepts(self):
        """Test: Upload new cset version from CSV"""
        url = urljoin(BACKEND_URL_BASE, 'upload-csv-new-cset-version-with-concepts')
        csv_path = os.path.join(
            TEST_DIR, 'input', 'test_enclave_wrangler', 'test_dataset_upload', 'type-2-diabetes-mellitus.csv')
        response: Response = self._upload_file(csv_path, url)
        self.assertEqual(response.json()['result'], 'success')

    def test_counts_compare_schemas(self):
        """test counts_compare_schemas()"""
        # Part 1: Ensure that the most recent backup is newer than a previous known backup
        df1 = counts_compare_schemas(compare_schema='most_recent_backup')
        df2 = counts_compare_schemas(compare_schema='n3c_backup_20230221')
        df1_date = parse(df1.columns[3][11:])
        df2_date = parse(df2.columns[3][11:])
        self.assertGreater(df1_date, df2_date)
        # Part 2: Ensure that table rows are not empty
        schema_column = df1.columns[2]
        schema_backup_column = df1.columns[3]
        for _index, row in df1.iterrows():
            if row['table'] in COUNT_TEST_EXCEPTIONS:
                continue
            for schema in [schema_column, schema_backup_column]:
                self.assertGreater(row[schema], 0, msg=f"Table '{row['table']}' had 0 rows in schema '{schema}'")

    def test_counts_over_time(self):
        """test counts_over_time()"""
        consistent_critical_tables = [
            'all_csets', 'code_sets', 'concept', 'concept_ancestor', 'concept_relationship',
            'concept_relationship_plus', 'concept_set_container', 'concept_set_counts_clamped', 'concept_set_members',
            'concept_set_version_item', 'concepts_with_counts', 'cset_members_items',
            'deidentified_term_usage_by_domain_clamped', 'omopconceptset', 'omopconceptsetcontainer', 'researcher']
        df = counts_over_time()
        # newest_backup_col: handles case where newest backup was not the only backup that day, e.g. '2023-05-03 2'
        newest_run_col_date_str = str(max([parse(x.split()[0]) for x in df.columns])).split()[0]
        newest_run_col = max([x for x in df.columns if x.startswith(newest_run_col_date_str)])
        for col in df.columns:
            for row, cell in df[col].items():
                if row == "COMMENT":
                    # Part 1: no db count run should have an empty 'COMMENT' field
                    self.assertFalse(df[col][row].isspace(), msg=f"Empty 'COMMENT' field in schema {col}")
                else:
                    if row in COUNT_TEST_EXCEPTIONS:
                        continue
                    # Other than `consistent_critical_tables`, tables may be added/removed, so skip for older backups
                    if col != newest_run_col and row not in consistent_critical_tables:
                        continue
                    # Part 2: all other row counts should be non-zero
                    self.assertGreater(df[col][row], 0, msg=f"Table '{row}' had 0 rows in run '{col}'")

    def test_subgraph(self):
        "tests subgraphs"
        #Basic unit test for a simple connected graph without a complex hierarchy
        edges1 = subgraph([1738170, 1738171, 1738202, 1738203])
        self.assertEqual(edges1, [
            (
                "1738170",
                "1738171"
            ),
            (
                "1738170",
                "1738202"
            ),
            (
                "1738170",
                "1738203"
            )
        ])
        #Test for a concept set that files in the gaps (i.e between child and grandparent)
        edges2 = subgraph([1738170,19122186])
        self.assertEqual(edges2,
                         [
                             (
                                 "1738170",
                                 "1738203"
                             ),
                             (
                                 "1738203",
                                 "19122186"
                             )
                         ])
        #Test for a more complex hierarchial relationship
        edges3 = subgraph([321588,4027255,43530856,4024552,316139,45766164,43530961])
        self.assertEqual(edges3,
                         [
                             (
                                 "4024552",
                                 "316139"
                             ),
                             (
                                 "316139",
                                 "43530961"
                             ),
                             (
                                 "316139",
                                 "45766164"
                             ),
                             (
                                 "321588",
                                 "4024552"
                             ),
                             (
                                 "321588",
                                 "4027255"
                             ),
                             (
                                 "4027255",
                                 "43530856"
                             )
                         ]
                         )
        #Testing a relationship where a common ancestor is needed to connect the graph
        edges3 = subgraph([4027255, 43530856, 4024552, 316139, 45766164, 43530961])
        self.assertEqual(edges3,
                         [
                             (
                                 "4024552",
                                 "316139"
                             ),
                             (
                                 "316139",
                                 "43530961"
                             ),
                             (
                                 "316139",
                                 "45766164"
                             ),
                             (
                                 "321588",
                                 "4024552"
                             ),
                             (
                                 "321588",
                                 "4027255"
                             ),
                             (
                                 "4027255",
                                 "43530856"
                             )
                         ]
                         )
            
# Uncomment this and run this file directly to run all tests
if __name__ == '__main__':
    test_subgraph()
#     unittest.main()