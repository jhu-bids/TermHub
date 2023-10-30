// imports from env.local;
// workflow will overwrite env.local with dev or prod during deployment
import {API_ROOT, DEPLOYMENT} from "./env.local";
export {API_ROOT, DEPLOYMENT};

export const SOURCE_APPLICATION = "TermHub";
export const SOURCE_APPLICATION_VERSION = "0.3.2 (Beta)";
export const VERSION = SOURCE_APPLICATION_VERSION;
export const SERVICE_USER_ID = "6387db50-9f12-48d2-b7dc-e8e88fdf51e3";
