export const endpoint = node => typeof node === 'object' ? node.id : node;
export function neighbours(id,links) {
  return new Set([id,...links.filter(e=>endpoint(e.source)===id||endpoint(e.target)===id).flatMap(e=>[endpoint(e.source),endpoint(e.target)])]);
}
export function expandVisible(ids,id,links) {
  return new Set([...ids,...neighbours(id,links)]);
}
export function visibleWorkspace({all,allowed,focus,expanded,hidden}) {
  const base=all?allowed:expanded;
  return new Set([...base].filter(id=>allowed.has(id)&&!hidden.has(id)));
}
export function resetPositions(nodes) {
  nodes.forEach((n,i)=>{n.x=Math.cos(i*2.4)*Math.sqrt(i+1)*22;n.y=Math.sin(i*2.4)*Math.sqrt(i+1)*22;n.z=(i%9-4)*30;delete n.fx;delete n.fy;delete n.fz;});
}
