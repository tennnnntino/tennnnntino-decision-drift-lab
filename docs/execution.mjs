/* Route-bound connector simulation. No credentials, I/O or external dispatch. */
import {checkPolicy} from './engine.mjs';
import {DEFAULT_POLICY} from './policy.mjs';

const routes = new Map([['draft', ['prepare-draft', 'internal']], ['send', ['send-document', 'external']]]);
const fields = ['target', 'content', 'tenant'];
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const tick = value => Number.isSafeInteger(value) && value >= 0;

function bindingFor(route, request) {
  if (!routes.has(route) || !object(request) || Object.keys(request).length !== fields.length ||
      !fields.every(key => Object.hasOwn(request, key) && typeof request[key] === 'string' && request[key])) {
    return null;
  }
  return [route, ...fields.map(key => request[key])];
}

export class SimulatedConnector {
  #policy;
  #approvals = new Map();

  constructor(policy = DEFAULT_POLICY) {
    this.#policy = checkPolicy(structuredClone(policy));
  }

  approve(approvalId, route, request, expiresAt) {
    const binding = bindingFor(route, request);
    if (typeof approvalId !== 'string' || !approvalId || this.#approvals.has(approvalId) || !binding || !tick(expiresAt)) {
      throw new Error('Invalid or duplicate simulated approval');
    }
    this.#approvals.set(approvalId, {binding, expiresAt, state: 'ACTIVE'});
  }

  revoke(approvalId) {
    const approval = this.#approvals.get(approvalId);
    if (!approval) throw new Error('Unknown simulated approval');
    if (approval.state === 'ACTIVE') approval.state = 'REVOKED';
  }

  attempt(claim, {route, request, now, approval_id: approvalId}) {
    const binding = bindingFor(route, request);
    const effective = binding ? {name: routes.get(route)[0], scope: routes.get(route)[1]} : null;
    const field = key => Object.hasOwn(claim, key) && typeof claim[key] === 'string' ? claim[key] : null;
    const declared = object(claim) ? {name: field('name'), scope: field('scope')} : null;
    const report = (reason = null) => ({
      result: reason ? 'BLOCK_IN_SIMULATION' : 'ALLOW_IN_SIMULATION', reason, declared, effective,
      policy_version: this.#policy.policy_version, authenticated: false, executed: false,
    });
    if (!binding || !tick(now)) return report('INVALID_EXECUTION_CONTEXT');
    if (!declared || declared.name !== effective.name || declared.scope !== effective.scope) return report('DECLARATION_MISMATCH');
    const requiresHuman = Object.hasOwn(claim, 'requires_human') ? claim.requires_human : true;
    if (typeof requiresHuman !== 'boolean') return report('INVALID_DECLARATION');
    if (!requiresHuman && this.#policy.exempt_actions.some(item => item.name === effective.name && item.scope === effective.scope)) {
      return report();
    }
    const approval = this.#approvals.get(approvalId);
    if (!approval) return report('APPROVAL_MISSING');
    if (approval.state !== 'ACTIVE') return report('APPROVAL_' + approval.state);
    if (now >= approval.expiresAt) return report('APPROVAL_EXPIRED');
    if (!approval.binding.every((value, index) => value === binding[index])) return report('APPROVAL_BINDING_MISMATCH');
    approval.state = 'CONSUMED';
    return report();
  }
}
