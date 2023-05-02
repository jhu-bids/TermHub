import { LRUCache } from 'lru-cache';
import { get } from 'lodash';
import { backend_url, axiosGet } from './State';

class DataAccess {

	constructor() {
		this.cache = new LRUCache({
				max: 100, // number of items to keep
				maxAge: 1000 * 60 * 60, // 1 hour
		});
	}

	saveCache() {
		const data = JSON.stringify(this.cache.dump());
		localStorage.setItem('data-access-cache', data);
	}

	loadCache() {
		const data = localStorage.getItem('data-access-cache');
		if (data) {
			this.cache.load(JSON.parse(data));
		}
	}

	clearCache() {
		this.cache.reset();
		localStorage.removeItem('data-access-cache');
	}

	store_concepts_to_cache(concepts) {
		concepts.forEach(concept => {
			this.cache.set(`concepts.${concept.concept_id}`, concept);
		});
	}

	async getConcepts(concept_ids=[], shape="array") {
		let all_cached_concepts = this.cache.get('concepts');
		let cached_concepts = {};
		let uncachedConceptIds = [];
		let uncachedConcepts = {};
		concept_ids.forEach(concept_id => {
			if (all_cached_concepts && all_cached_concepts[concept_id]) {
				cached_concepts[concept_id] = all_cached_concepts[concept_id];
			} else {
				uncachedConceptIds.push(concept_id);
			}
		}
		);
		if (uncachedConceptIds.length) {
			const url = backend_url(
				"get-concepts?" + uncachedConceptIds.map(c=>`id=${c}`).join("&")
			);
		}
		const data = await fetch('concepts', url);
		data.forEach(concept => {
			uncachedConcepts[concept.concept_id] = concept;
		});
		const results = {...cached_concepts, ...uncachedConcepts};
		const not_found = concept_ids.filter(
			x => !Object.values(results).map(c=>c.concept_id).includes(x));
		if (not_found.length) {
		  	window.alert("Warning in DataAccess.getConcepts: couldn't find concepts for " +
				not_found.join(', '))
		}
		if (shape === 'array') {
			return Object.values(results);
		}
		return results;
	}

	async getSubgraphEdges(concept_ids=[], format='array') {
		if (!concept_ids.length) {
			return [];
		}
		const url = backend_url(
			"subgraph?" + concept_ids.map(c=>`cid=${c}`).join("&")
		);
		const data = await fetch('subgraph', url);
		return data;
	}

	async fetch(type, url) {
		const response = await axiosGet(url);
		const data = get(response, 'data', []);
		if (type === 'concepts') {
			this.store_concepts_to_cache(data);
		}
		return data;
	}
}



