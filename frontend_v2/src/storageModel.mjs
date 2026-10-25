import {validateResponse} from "./requestJson.mjs";
import {cleanCollections} from "./collectionModel.mjs";
const memory={local:new Map(),session:new Map()};
const volatile={local:new Set(),session:new Set()};
let failure=false;const listeners=new Set();
export function storageFailed(){return failure;}
export function subscribeStorage(fn){listeners.add(fn);return ()=>listeners.delete(fn);}
function failed(){if(!failure){failure=true;for(const fn of listeners)fn();}}
function storage(kind){return globalThis[kind==='session'?'sessionStorage':'localStorage'];}
export function makeStorage(kind='local') {return {
 getItem(key){if(volatile[kind].has(key))return memory[kind].get(key) ?? null;try{const value=storage(kind)?.getItem(key);if(value!=null){memory[kind].set(key,value);return value;}return memory[kind].get(key) ?? null;}catch{failed();return memory[kind].get(key) ?? null;}},
 setItem(key,value){memory[kind].set(key,String(value));try{storage(kind).setItem(key,String(value));volatile[kind].delete(key);return true;}catch{volatile[kind].add(key);failed();return false;}},
 removeItem(key){memory[kind].delete(key);try{storage(kind).removeItem(key);volatile[kind].delete(key);return true;}catch{volatile[kind].add(key);failed();return false;}},
 keys(){try{return [...new Set([...Object.keys(storage(kind)),...memory[kind].keys()])];}catch{failed();return [...memory[kind].keys()];}}
};}
export const safeLocal=makeStorage(),safeSession=makeStorage('session');
const strings=value=>Array.isArray(value)?[...new Set(value.filter(x=>typeof x==='string').map(x=>x.slice(0,120)))].slice(0,200):[];
const date=value=>typeof value==='string' && Number.isFinite(Date.parse(value));
const safeMessage=m=>m && ['assistant','user'].includes(m.role) && typeof m.text==='string' && (!m.createdAt || date(m.createdAt)) && (!m.data || validStoredAnswer(m.data,m.text));
function validStoredAnswer(data,text){try{if(!data || typeof data!=='object' || Array.isArray(data))return false;validateResponse('/advisor',{...data,answer:text});return ['rules'].every(k=>data[k]==null || (Array.isArray(data[k]) && data[k].every(r=>r && typeof r==='object')));}catch{return false;}}
export function normalizeStored(key,value,fallback) {
 if(key==='curricupath-collections-v1')return cleanCollections(value);
 if(key==='curricupath-continuation-v1')return value && typeof value==='object' && /^#(plan|explore|advisor)(\?|$)/.test(value.hash)?value:{};
 if(key==='curricupath-profile'){
   if(!value || typeof value!=='object' || Array.isArray(value))return fallback;
   const defaults={name:'',programme:'',stage:'year_4_semester_1',stream:'general',completed:[],current:[],planned:[],repeating:[],historyConfirmed:false,reviewNote:'',interests:[],careers:[],workload:'',format:'',...fallback};
   const out={...defaults};for(const k of ['name','programme','stage','stream','reviewNote','workload','format'])if(typeof value[k]==='string')out[k]=value[k].slice(0,k==='reviewNote'?2000:120);
   for(const k of ['completed','current','planned','repeating','interests','careers'])out[k]=strings(value[k]);out.historyConfirmed=value.historyConfirmed===true;return out;
 }
 if(['curricupath-saved-courses','curricupath-comparison','curricupath-recent-courses','curricupath-completed'].includes(key))return strings(value);
 if(key==='curricupath-conversation-v1')return Array.isArray(value)?value.filter(safeMessage).slice(-100):fallback;
 if(key==='curricupath-saved-answers-v1')return Array.isArray(value)?value.filter(m=>safeMessage({...m,role:'assistant'}) && typeof m.id==='string' && m.data && date(m.savedAt)).slice(0,30):fallback;
 if(key==='curricupath-scenarios-v1')return Array.isArray(value)?value.filter(d=>d && typeof d.id==='string' && typeof d.name==='string' && typeof d.programme==='string' && typeof d.baseKey==='string' && Array.isArray(d.planned) && Array.isArray(d.assumedCompleted) && Array.isArray(d.removedCompleted) && d.terms && typeof d.terms==='object' && !Array.isArray(d.terms) && [...d.planned,...d.assumedCompleted,...d.removedCompleted].every(c=>typeof c==='string') && Object.values(d.terms).every(t=>['1','2','unassigned'].includes(t))).slice(-8):fallback;
 if(Array.isArray(fallback))return Array.isArray(value)?value:fallback;
 if(typeof fallback==='boolean')return typeof value==='boolean'?value:fallback;
 if(typeof fallback==='string')return typeof value==='string'?value:fallback;
 return value && typeof value==='object' && !Array.isArray(value)?value:fallback;
}
export function storedJson(key,fallback){const raw=safeLocal.getItem(key);if(raw===null)return fallback;try{return normalizeStored(key,JSON.parse(raw),fallback);}catch{safeLocal.setItem('curricupath-recovery-v1',JSON.stringify({key,raw:raw.slice(0,50000),at:new Date().toISOString()}));return fallback;}}
export function personalKeys(){return safeLocal.keys().filter(k=>k.startsWith('curricupath-') && !['curricupath-theme','curricupath-motion','curricupath-sidebar-collapsed'].includes(k));}
export function personalExport(){return {schema:1,exportedAt:new Date().toISOString(),scope:'Device-local CurricuPath records; may contain private declarations and conversations',records:Object.fromEntries(personalKeys().map(k=>{const raw=safeLocal.getItem(k);try{return [k,JSON.parse(raw)];}catch{return [k,raw];}}))};}
export function clearPersonal(){let success=true;for(const k of personalKeys())if(!safeLocal.removeItem(k))success=false;for(const k of safeSession.keys().filter(k=>k.startsWith('curricupath-')))if(!safeSession.removeItem(k))success=false;return success;}
