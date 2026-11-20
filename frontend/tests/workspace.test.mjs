import test from 'node:test';
import assert from 'node:assert/strict';

const TICK=()=>new Promise(resolve=>setTimeout(resolve,0));
const fixtureName="TEST FIXTURE — NOT REAL";
const fixture={
  id:"test-only",name:fixtureName,summary:"An evidence-only test case.",kind:"prospect",stage:"POTENTIAL_PRE_COMPANY",country:"DE",sector:"Test",tags:[],team:[],watched:false,why_now:"Test commercial intent",scores:{quality:42,confidence:47,breakdown:[]},
  evidence:[{id:"test-e",source_id:"test",source_name:"Test publisher",title:"Fixture source",url:"https://example.org/fixture",claim:"Test commercial intent",quote:"<script>untrusted test input</script>",signal_type:"PROTOTYPE",first_observed_at:"2020-01-01T13:00:00Z",retrieved_at:"2020-01-01T13:00:00Z"}]
};
// Exercise the same event handlers and rendered HTML used by the workspace.
// The adapter supplies only the DOM calls made by these tests. It does not
// model browser layout, accessibility behavior, or network transport.
class Element {
  constructor(){this.innerHTML="";this.style={};this.attributes={};this.value="";this.open=false;this.listeners={};this.classList={add(){},remove(){},toggle(){}}}
  setAttribute(k,v){this.attributes[k]=v}
  addEventListener(name,fn){this.listeners[name]=fn}
  closest(){return new Element()}
  scrollIntoView(){}
  getBoundingClientRect(){return {height:0,width:0}}
  showModal(){this.open=true}
  close(){this.open=false;this.listeners.close?.()}
}
test('research workspace UI contracts',async t=>{
  const elements=new Map();
  const element=selector=>{if(!elements.has(selector))elements.set(selector,new Element());return elements.get(selector)};
  const listeners={};const requests=[];const html=selector=>element(selector).innerHTML;
  const local={watched:false,note:"",decision:"unreviewed"};
  const responses=async(path,options={})=>{
    const url=new URL(path,'http://localhost'),route=url.pathname.replace('/api/v1','');
    const body=options.body?JSON.parse(options.body):undefined;requests.push({route,params:url.searchParams,body});
    let payload={};let status=200;
    if(route==='/stats')payload={prospects:1,portfolio:0,watchlist:+local.watched,evidence:1,mode:'recorded',best_find:null};
    else if(route==='/sources')payload={items:[{id:'test',name:fixtureName,enabled:true,can_scan:true,status:'available'}]};
    else if(route==='/settings')payload={country:'DE',interval_hours:24,priority_threshold:60};
    else if(['/imports','/duplicates'].includes(route))payload={items:[]};
    else if(route==='/coverage')payload={items:[{country:'Germany',country_code:'DE'}]};
    else if(route==='/discovery/plan')payload={country:'DE',technology:'robotics',configured:false,items:[{language:'de',scope:'campus',query:'TEST FIXTURE — NOT REAL: robotics'}]};
    else if(route==='/discovery/web')payload={items:[],status:'credential_required',message:'Set BRAVE_SEARCH_API_KEY.'};
    else if(route==='/import-url')payload=body;
    else if(route==='/leads')payload={items:[{...fixture,...local}],total:1,page:1,limit:12,facets:{countries:['DE'],sectors:['Test'],sources:['test']}};
    else if(route==='/leads/test-only')payload={...fixture,...local};
    else if(route==='/leads/test-only/watch'){local.watched=body.watched;payload={...fixture,...local}}
    else if(route==='/leads/test-only/review'){local.note=body.note;local.decision=body.decision}
    else if(route==='/scans')payload={id:'test-run',mode:'live',source_id:'test',status:'credential_required',errors:['TEST FIXTURE — NOT REAL: key required']};
    else {status=404;payload={detail:'Unknown test route'};}
    return {ok:status<400,status,json:async()=>payload};
  };
  const old={};
  for(const key of ['window','document','fetch','location','history','FormData'])old[key]=globalThis[key];
  function move(value){globalThis.location=new URL(value,'http://localhost')}
  move('http://localhost/?view=discover');
  globalThis.document={querySelector:element,addEventListener:(name,fn)=>listeners[name]=fn};
  globalThis.window={addEventListener(){},scrollTo(){},devicePixelRatio:1};
  globalThis.fetch=responses;
  globalThis.history={replaceState:(_,title,url)=>move(url),pushState:(_,title,url)=>move(url)};
  globalThis.FormData=class {constructor(f){this.data=f.data}get(k){return this.data[k]??null}has(k){return k in this.data}};
  t.after(()=>{for(const [k,v] of Object.entries(old)){if(v===undefined)delete globalThis[k];else globalThis[k]=v}});
  await import('../app.js');await TICK();
  await t.test('renders API-backed search and exposes only attributed signal links',()=>{
    assert.match(html('#result-region'),/TEST FIXTURE — NOT REAL/);
    assert.match(html('#result-region'),/https:\/\/example\.org\/fixture/);
    assert.match(html('#metrics'),/Discovery leads/);
    assert.equal(requests.find(r=>r.route==='/leads').params.get('kind'),'prospect');
  });
  await t.test('submits search on Enter and persists country filters in the URL',async()=>{
    const input={id:'q',value:'quantum',matches:()=>false};
    listeners.keydown({key:'Enter',target:input,preventDefault(){}});
    await TICK();
    assert.equal(new URL(location).searchParams.get('q'),'quantum');
    listeners.change({target:{id:'',value:'DE',dataset:{filter:'country'},matches:()=>true}});
    await TICK();
    const last=requests.filter(r=>r.route==='/leads').at(-1);
    assert.equal(last.params.get('q'),'quantum');assert.equal(last.params.get('country'),'DE');
  });
  const click=(attrs,dataset)=>{const node={tagName:'BUTTON',dataset,disabled:false,hasAttribute:k=>attrs.includes(k)};listeners.click({target:{closest:()=>node},preventDefault(){}})};
  await t.test('uses the saved discovery country, suspends it for registry searches, and allows removal',async()=>{
    click(['data-view'],{view:'discover'});await TICK();
    assert.equal(location.searchParams.get('country'),'DE');
    click(['data-stage'],{stage:'NEWLY_INCORPORATED'});await TICK();
    assert.equal(location.searchParams.has('country'),false);
    click(['data-stage'],{stage:'POTENTIAL_PRE_COMPANY'});await TICK();
    assert.equal(location.searchParams.get('country'),'DE');
    click([],{action:'all-countries'});await TICK();
    assert.equal(location.searchParams.has('country'),false);
  });
  await t.test('opens a dossier, escapes untrusted evidence and distinguishes observation dates',async()=>{
    click(['data-lead'],{lead:fixture.id});await TICK();
    assert.equal(element('#detail-dialog').open,true);assert.match(html('#detail-content'),/Evidence timeline/);
    assert.match(html('#detail-content'),/&lt;script&gt;untrusted test input&lt;\/script&gt;/);
    assert.match(html('#detail-content'),/Published Unknown/);
    assert.match(html('#detail-content'),/First observed 01 Jan 2020/);
  });
  await t.test('saves a watchlist change and analyst review through the API',async()=>{
    click(['data-watch'],{watch:fixture.id,watched:'false'});await TICK();
    assert.equal(local.watched,true);
    const form={id:'review-form',dataset:{id:fixture.id},data:{note:'Test note',decision:'review'},querySelector:()=>null};
    await listeners.submit({target:form,preventDefault(){}});
    assert.equal(local.note,'Test note');assert.equal(local.decision,'review');
  });
  await t.test('reports a missing credential as the terminal scan result',async()=>{
    const form={id:'scan-form',data:{source_id:'test',mode:'live'},querySelector:()=>null};
    element('#action-dialog').open=true;
    await listeners.submit({target:form,preventDefault(){}});
    assert.match(html('#action-content'),/Credential required/);
    assert.match(html('#action-content'),/key required/);
    assert.equal(requests.filter(r=>r.route==='/scans/test-run').length,0);
  });
  await t.test('generates local query suggestions and retains them after a missing-key web search and manual intake',async()=>{
    click(['data-view'],{view:'sources'});await TICK();
    click(['data-ops-tab'],{opsTab:'plan'});
    await listeners.submit({target:{id:'planner-form',data:{country:'DE',technology:'robotics'},querySelector:()=>null},preventDefault(){}});
    assert.match(html('#ops-results'),/TEST FIXTURE — NOT REAL: robotics/);
    assert.equal(requests.filter(r=>r.route==='/discovery/web').length,0);
    click(['data-plan-execute'],{planExecute:'0'});await TICK();
    assert.match(html('#ops-results'),/BRAVE_SEARCH_API_KEY/);
    click([],{action:'import'});await TICK();
    await listeners.submit({target:{id:'import-form',data:{url:'https://example.org/test',title:fixtureName,note:'Test note'},querySelector:()=>null},preventDefault(){}});
    assert.match(html('#ops-results'),/TEST FIXTURE — NOT REAL: robotics/);
    assert.match(html('#ops-results'),/BRAVE_SEARCH_API_KEY/);
  });

});

