const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require('playwright');
const pointer=JSON.parse(fs.readFileSync('intelligence-publication.json','utf8'));
const base=(process.env.INTELLIGENCE_TEST_BASE||'http://127.0.0.1:8765/').replace(/\/?$/,'/');
async function ready(page){await page.waitForFunction(()=>['ready','error'].includes(document.documentElement.dataset.intelligenceState),null,{timeout:180000});}
async function downloaded(page,label){const waiting=page.waitForEvent('download');await page.getByRole('button',{name:label,exact:true}).click();const item=await waiting;const stream=await item.createReadStream();const chunks=[];for await(const c of stream)chunks.push(c);return JSON.parse(Buffer.concat(chunks).toString('utf8'));}
(async()=>{const browser=await chromium.launch({headless:true});try{
  const page=await browser.newPage({acceptDownloads:true});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'intelligence.html');await ready(page);
  assert.equal(await page.locator('html').getAttribute('data-intelligence-state'),'ready',await page.locator('#intel-status').innerText());
  assert.match(await page.locator('#intel-status').innerText(),new RegExp(String(pointer.records)));
  await page.locator('#intel-query').fill('annexation');await page.locator('#intel-search').click();
  await page.waitForFunction(()=>Number(document.getElementById('intel-results').dataset.matchCount)>0,null,{timeout:180000});
  const results=await downloaded(page,'Download all matching IDs');assert.equal(results.revision,pointer.revision);assert.ok(results.records.length>0);
  await page.locator('#intel-results .row button').first().click();
  await page.waitForFunction(()=>Boolean(document.getElementById('intel-graph').dataset.recordId),null,{timeout:180000});
  const graph=await downloaded(page,'Download complete graph candidates');assert.equal(graph.record_id,results.records[0].id);assert.equal(graph.version,results.records[0].version);assert.equal(graph.review,'unreviewed');
  const metadata=await downloaded(page,'Download collection.json');assert.equal(metadata.records,pointer.records);
  const tampered=await browser.newPage();await tampered.route(pointer.base_url+'collection.json',r=>r.fulfill({status:200,contentType:'application/json',headers:{'access-control-allow-origin':'*'},body:'{"tampered":true}'}));
  await tampered.goto(base+'intelligence.html');await ready(tampered);assert.equal(await tampered.locator('html').getAttribute('data-intelligence-state'),'error');assert.match(await tampered.locator('#intel-status').innerText(),/hash mismatch/i);assert.equal(await tampered.locator('#intel-search').isDisabled(),true);
  const wrongHost=await browser.newPage();await wrongHost.route(base+'intelligence-publication.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...pointer,data_repository:'unexpected/repository'})}));
  await wrongHost.goto(base+'intelligence.html');await ready(wrongHost);assert.equal(await wrongHost.locator('html').getAttribute('data-intelligence-state'),'error');assert.match(await wrongHost.locator('#intel-status').innerText(),/Unexpected intelligence host/);assert.deepEqual(errors,[]);
  console.log(JSON.stringify({schema:'intelligence-browser-verification-v1',data_revision:pointer.revision,records:pointer.records,literal_search_matches:results.records.length,graph_version_verified:true,metadata_download_verified:true,tampered_data_rejected:true,unexpected_host_rejected:true,base,scope:'Retrieval and integrity checks only; not factual validation or Google indexing.'}));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
