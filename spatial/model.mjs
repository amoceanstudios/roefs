// Pure adapter: accept persisted objects, never invent business values.
export const SECTORS = {
  customers: {label: 'Klanten', color: '#74e7dc', x: -19},
  workorders: {label: 'Opdrachten', color: '#b8a3ff', x: 0},
  invoices: {label: 'Facturen', color: '#efd08e', x: 19}
};
export function universe(data) {
  const width = Math.max(4, Math.ceil(Math.sqrt(Math.max(0, ...Object.keys(SECTORS).map(k => (data[k] || []).length)))));
  return Object.entries(SECTORS).flatMap(([kind, sector], index) => (data[kind] || []).map((record, i) => ({
    key: `${kind}:${record.id}`, kind, record,
    label: String(record.name || record.description || record.number || `#${record.id}`),
    position: [(index - 1) * (width * 3.3 + 9) + (i % width - (width - 1) / 2) * 3.3, 1 + Math.min(4, Math.log2(1 + Math.max(0, Number(record.amount || 0))) / 4), (Math.floor(i / width) - (width - 1) / 2) * 3.2],
    urgent: record.priority === 'Spoed' || (kind === 'invoices' && record.status !== 'Betaald' && Boolean(record.due_date) && record.due_date < new Date().toISOString().slice(0,10)),
    color: sector.color
  })));
}
export function linkedCustomer(node, data) {
  if (node.kind === 'customers') return node.record.id;
  if (node.record.customer_id) return node.record.customer_id;
  return data.objects?.find(o => String(o.id) === String(node.record.object_id))?.customer_id;
}
export function related(node, data) {
  const customerId = linkedCustomer(node, data);
  if (!customerId) return [];
  return universe(data).filter(n => n.key !== node.key && String(linkedCustomer(n, data)) === String(customerId));
}
