
all this helped me get my bearings. not sure if i'll want any of it again:

    ann_pre = {x[0]: x[1].groupby('annotation') for x in counts.groupby('annotation')}

    for pre, g in counts.groupby('prefix'):
        print(f'{pre}   {len(g)}')
        for ann, gg in g.groupby('annotation'):
            print(f'    {ann}   {len(gg)}')

        z = dict(zip(['vsac_enclave', 'vsac_csv', 'hcup_enclave', 'hcup_csv', ], [
            set(counts[counts.prefix == '[VSAC]'].concept_set_name),
            set(v_versions[v_versions.prefix == '[VSAC]'].concept_set_name),
            set(counts[counts.prefix == '[HCUP]'].concept_set_name),
            set(h_versions[h_versions.prefix == '[HCUP]'].concept_set_name),
        ]))

        for k,v in z.items():
            print(f'sets in {k}: {len(v)}')

        print(f"vsac enclave sets: {len(set(counts[counts.prefix == '[VSAC]'].concept_set_name))}")
        print(f"vsac csv sets: {len(set(v_versions[v_versions.prefix == 'VSAC']))}")
        print(f"hcup enclave sets: {len(set(counts[counts.prefix == '[HCUP]'].concept_set_name))}")
        print(f"hcup csv sets: {len(set(v_versions[v_versions.prefix == 'HCUP']))}")
        #print(f"hcup csv sets: {len(set(h_versions.concept_set_name)")

        'vsac_enclave', 'vsac_cs', 'hcup_enclav', 'hcup_cs',
        set(counts[counts.prefix == '[VSAC]'].concept_set_name)
        set(v_versions[v_versions.prefix == '[VSAC]'].concept_set_name)
        set(counts[counts.prefix == '[HCUP]'].concept_set_name)
        set(v_versions[v_versions.prefix == '[HCUP]'].concept_set_name)

        hcup_dfs[2].merge(hcup_dfs[1], left_on="codeset_id", right_on="concept_set_id", how="inner").groupby(['concept_set_name', 'codeset_id']).size()
           # .merge(z['hcup_enclave'], on='concept_set_name')
        pd.DataFrame(
            hcup_dfs[2].merge(hcup_dfs[1], left_on="codeset_id", right_on="concept_set_id", how="inner").groupby(
                ['concept_set_name', 'codeset_id']).size()).reset_index().merge(z['hcup_enclav'], on='concept_set_name')
        try:
            hcup_csv = set(v_versions.concept_set_name)
            assert len(set(counts[counts.prefix == '[VSAC]'].concept_set_name) - set(v_versions.concept_set_name))
            assert len(set(v_versions.concept_set_name) - set(counts[counts.prefix == '[VSAC]'].concept_set_name))
            assert len(set(counts[counts.prefix == '[HCUP]'].concept_set_name) - set(h_versions.concept_set_name))
            assert len(set(h_versions.concept_set_name) - set(counts[counts.prefix == '[HCUP]'].concept_set_name))
        except AssertionError as ae:
            print("\n".join(set(v_versions.concept_set_name) - set(counts[counts.prefix == '[VSAC]'].concept_set_name)))
            print(ae)