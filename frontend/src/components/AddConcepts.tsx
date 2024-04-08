
import React, {useState, } from 'react';

import AsyncSelect from 'react-select/async';

import {useDataGetter} from "../state/DataGetter";

interface Concept {
  readonly concept_id: number;
  readonly concept_name: string;
  readonly domain_id: string;
  readonly vocabulary_id: string;
  readonly concept_class_id: string;
  readonly standard_concept: string;
  readonly concept_code: string;
  readonly invalid_reason: string;
  readonly domain_cnt: number;
  readonly domain: string;
  readonly total_cnt: number;
  readonly distinct_person_cnt: string;
}

export function AddConcepts() {
  const dataGetter = useDataGetter();

  let concepts: Concept[] = [];

  const fetchConcepts = (inputValue: string) => {
    return concepts.filter((i) =>
        i.label.toLowerCase().includes(inputValue.toLowerCase())
    );
  };

  const promiseOptions = (inputValue: string) => {
    return dataGetter.fetchAndCacheItems(dataGetter.apiCalls.concepts, concept_ids);
  }
      new Promise<Concept[]>((resolve) => {
        setTimeout(() => {
          resolve(filterColors(inputValue));
        }, 1000);
      });

  // return <AsyncSelect cacheOptions /*defaultOptions*/ loadOptions={promiseOptions} />
}