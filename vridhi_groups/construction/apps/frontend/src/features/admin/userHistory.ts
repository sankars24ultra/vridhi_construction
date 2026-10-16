const fieldNames: Record<string, string> = {
  name: 'Full name', username: 'Username', email: 'Email', phone: 'Contact number',
  active: 'Account status', global_access: 'Global access', access: 'Access',
  export_report: 'Export report', mode: 'Write access', add_user: 'Add/Edit users',
  reset_password: 'Reset Password', activate_deactivate: 'Activate/Deactivate',
  delete_user: 'Delete users', history: 'History', overview: 'Overview',
  procurement: 'Procurement', inventory: 'Inventory', cashflow: 'Cash flow',
  labor: 'Labor and Wages', users: 'Users page', new_purchase_order: 'Create/Edit Purchase Order',
  edit_purchase_order: 'Edit Purchase Order', add_payment: 'Add Payment',
  quick_entry: 'Quick Entry', upload_plan_document: 'Upload Plan Document', update_status: 'Update Status',
  receive_stock: 'Receive Stock', use_stock: 'Use Stock', new_application: 'New Application', record_receipt: 'Record Receipt',
  new_labor_contract: 'New Labor Contract', add_worker: 'Add Worker', log_weekly_work: 'Log Weekly Work',
  pay_weekly_work: 'Pay Weekly Work', edit_worker: 'Edit Worker', deactivate_worker: 'Deactivate Worker',
  download_contract_files: 'Download Contract Files', download_history_files: 'Download History Files',
};

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function displayValue(value: unknown, key: string): string {
  if (value === undefined || value === null || value === '') return 'Not provided';
  if (key === 'active') return value ? 'Active' : 'Inactive';
  if (typeof value === 'boolean') return value ? 'Allowed' : 'Blocked';
  if (value === 'allow') return 'Allowed';
  if (value === 'block') return 'Blocked';
  if (key === 'mode') return value === 'all' ? 'All actions' : 'Selected actions';
  return String(value);
}

export function userHistoryChanges(action: string, details: Record<string, unknown> | null, projectNames: Record<string, string> = {}): string[] {
  if (action === 'user_password_reset') return ['Password changed. Existing sessions were signed out.'];
  if (action === 'user_deleted') return ['Account deleted. Sign-in disabled; project and audit history retained.'];
  const changes: string[] = [];
  const before = objectValue(details?.before);
  const after = objectValue(details?.after);
  const created = action === 'user_created';
  const compare = (previous: Record<string, unknown>, current: Record<string, unknown>, path: string[] = []) => {
    for (const key of new Set([...Object.keys(previous), ...Object.keys(current)])) {
      if (/password|secret|token/i.test(key)) continue;
      const oldValue = previous[key];
      const newValue = current[key];
      const label = [...path, fieldNames[key] || key.replaceAll('_', ' ')].join(' · ');
      if (key === 'project_permissions') {
        const oldProjects = objectValue(oldValue);
        const newProjects = objectValue(newValue);
        for (const projectId of new Set([...Object.keys(oldProjects), ...Object.keys(newProjects)])) {
          const name = projectNames[projectId] || 'Project';
          if (!(projectId in oldProjects)) changes.push(`Assigned project: ${name}.`);
          if (!(projectId in newProjects)) changes.push(`Removed project: ${name}.`);
          if (projectId in newProjects) compare(objectValue(oldProjects[projectId]), objectValue(newProjects[projectId]), [name]);
        }
      } else if (['global_permissions', 'users_permissions', 'audit_permissions'].includes(key)) {
        compare(objectValue(oldValue), objectValue(newValue), [key === 'global_permissions' ? 'Global permissions' : key === 'audit_permissions' ? 'Audit Log' : 'Users page']);
      } else if (oldValue && typeof oldValue === 'object' || newValue && typeof newValue === 'object') {
        compare(objectValue(oldValue), objectValue(newValue), ['read', 'write', 'actions'].includes(key) ? path : [...path, fieldNames[key] || key]);
      } else if (oldValue !== newValue && !(created && (newValue === null || newValue === undefined || newValue === ''))) {
        if (oldValue === null || oldValue === undefined || oldValue === '') changes.push(`Added ${label}: ${displayValue(newValue, key)}.`);
        else if (newValue === null || newValue === undefined || newValue === '') changes.push(`Removed ${label} (previously ${displayValue(oldValue, key)}).`);
        else changes.push(`${label} changed from ${displayValue(oldValue, key)} to ${displayValue(newValue, key)}.`);
      }
    }
  };
  compare(before, after);
  if (!changes.length) {
    if (action === 'user_activated') return ['Account activated.'];
    if (action === 'user_deactivated') return ['Account deactivated. Existing sessions were signed out.'];
    if (action === 'user_permissions_updated' && details?.all_users_actions) return ['Global access enabled with all Users page permissions.'];
    return [created ? 'User account created.' : 'No detailed field changes were recorded for this event.'];
  }
  return changes;
}