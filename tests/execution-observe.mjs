import {SimulatedConnector} from '../docs/execution.mjs';

const send = {name: 'send-document', scope: 'external', requires_human: false};
const draft = {name: 'prepare-draft', scope: 'internal', requires_human: false};
const request = {target: 'demo-target', content: 'Synthetic content', tenant: 'demo'};
const connector = new SimulatedConnector();
const results = [];
const attempt = (claim = send, {route = 'send', now = 1, approval_id, ...overrides} = {}) =>
  results.push(connector.attempt(claim, {route, request: {...request, ...overrides}, now, approval_id}));

attempt(draft, {route: 'draft'});
attempt(draft);
attempt({...send, human_approval: {approved: true, actor_type: 'HUMAN'}});
attempt(send, {route: 'unknown'});
connector.approve('A', 'send', request, 5);
attempt(send, {approval_id: 'A', target: 'different'});
attempt(send, {approval_id: 'A', content: 'different'});
attempt(send, {approval_id: 'A', tenant: 'different'});
attempt(send, {approval_id: 'A'});
attempt(send, {approval_id: 'A'});
connector.approve('B', 'send', request, 5);
connector.revoke('B');
attempt(send, {approval_id: 'B'});
connector.approve('C', 'send', request, 5);
attempt(send, {approval_id: 'C', now: 5});
connector.approve('D', 'draft', request, 5);
attempt(send, {approval_id: 'D'});

console.log(JSON.stringify(results));
