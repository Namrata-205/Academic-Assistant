// Match the Python engine's direct-prerequisite coverage rule.
export function diagnosticCoverage(target, bank, links) {
  const assessed = new Set(bank.map(q => q.concept_id));
  const prerequisites = [...new Set(links.filter(e => e.target === target && e.source !== target).map(e => e.source))];
  return [...prerequisites.filter(id => assessed.has(id)), ...(assessed.has(target) ? [target] : [])];
}
