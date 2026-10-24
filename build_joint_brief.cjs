/* Build a reviewable saved-input brief from the same renderer as the browser. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function run(){
  const root=__dirname,read=name=>fs.readFileSync(path.join(root,name),'utf8');
  const data=JSON.parse(read('results/joint_planning.json')),analysis=JSON.parse(read('results/analysis.json')),context={};vm.createContext(context);
  for(const name of ['joint_planning.js','joint_brief.js'])vm.runInContext(read(name),context);
  const report=read('results/SaltShield_Wachusett.html'),map=report.match(/id="joint-map">([\s\S]*?)<\/div>/)?.[1];
  if(!map)throw Error('Build the current workspace before creating the linked brief.');
  const embedded=JSON.parse(report.match(/const ANALYSIS=(.*);\n/)[1]).joint;
  if(!context.SaltShieldJoint.matches(embedded.source_sha256,data.source_sha256)||!context.SaltShieldJoint.matches(embedded.default.input_snapshot,data.default.input_snapshot)||!context.SaltShieldJoint.matches(embedded.reach_sensitivity,data.reach_sensitivity))throw Error('The workspace is stale. Rebuild it before creating the linked brief.');
  const ids=new Set(data.default.plans.pooled.selected_cell_ids);
  const mapSvg=map.replace(/<path class="joint-cell"[^>]*>/g,tag=>tag.replace(/fill="[^"]*"/, 'fill="'+(ids.has(tag.match(/data-cell="([^"]+)"/)[1])?'#007aff':'#e1e6e2')+'"'));
  const html=context.SaltShieldJointBrief.render({scenario:data.default,policy:'pooled',data,sensitivity:data.reach_sensitivity,mapSvg,sources:analysis.official_sources});
  const output=path.join(root,'results/SaltShield_Linked_Brief.html');fs.writeFileSync(output,html);return {output,bytes:Buffer.byteLength(html)};
}
module.exports={run};if(require.main===module)console.log(JSON.stringify(run(),null,2));
