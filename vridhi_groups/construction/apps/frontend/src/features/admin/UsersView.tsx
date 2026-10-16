import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Download, Eye, History, KeyRound, Pencil, Plus, Search, Trash2, UserCheck, UserX } from "lucide-react";
import {
  ApiError,
  api,
  type ProjectPermissions,
  type User,
} from "../../lib/api";
import {
  EmptyState,
  PageTitle,
  PanelHeading,
  QueryError,
} from "../../components/ui";
import { ModalFrame } from "../../components/ModalFrame";
import { ExportHeader } from "../../components/ExportHeader";
import { statusClass } from "../../lib/format";
import { userHistoryChanges } from "./userHistory";

const projectModules = [
  {
    id: "overview",
    label: "Overview",
    actions: [
      { id: "quick_entry", label: "Quick Entry" },
      { id: "upload_plan_document", label: "Upload Plan Document" },
      { id: "update_status", label: "Update Status" },
    ],
  },
  {
    id: "procurement",
    label: "Procurement",
    actions: [
      { id: "new_purchase_order", label: "Create / Edit Purchase Order" },
      { id: "add_payment", label: "Add Payment" },
    ],
  },
  {
    id: "inventory",
    label: "Inventory",
    actions: [
      { id: "receive_stock", label: "Receive Stock" },
      { id: "use_stock", label: "Use Stock" },
    ],
  },
  {
    id: "cashflow",
    label: "Cash Flow",
    actions: [
      { id: "new_application", label: "New Application" },
      { id: "record_receipt", label: "Record Receipt" },
    ],
  },
  {
    id: "labor",
    label: "Labor and Wages",
    actions: [
      { id: "new_labor_contract", label: "New Labor Contract" },
      { id: "add_worker", label: "Add Worker" },
      { id: "log_weekly_work", label: "Log Weekly Work" },
      { id: "pay_weekly_work", label: "Pay Weekly Work" },
      { id: "edit_worker", label: "Edit Worker" },
      { id: "deactivate_worker", label: "Deactivate Worker" },
      { id: "download_contract_files", label: "Download Contract Files" },
      { id: "download_history_files", label: "Download History Files" },
    ],
  },
  {
    id: "users",
    label: "Users",
    actions: [{ id: "add_user", label: "Add User" }],
  },
] as const;

type PermissionModule = keyof ProjectPermissions;
const usersActions = [
  { id: "add_user", label: "Add/Edit users" },
  { id: "reset_password", label: "Reset Password" },
  { id: "activate_deactivate", label: "Activate/Deactivate" },
  { id: "delete_user", label: "Delete" },
  { id: "history", label: "History" },
] as const;

function fullUsersPermissions(): ProjectPermissions["users"] {
  return { access: "allow", read: { export_report: true }, write: { mode: "all", actions: Object.fromEntries(usersActions.map((action) => [action.id, true])) } };
}

function defaultProjectPermissions(sharedAccess = false): ProjectPermissions {
  return Object.fromEntries(
    projectModules.map((module) => [
      module.id,
      {
        access: sharedAccess && module.id !== "users" ? "allow" : "block",
        read: { export_report: sharedAccess && module.id !== "users" },
        write: {
          mode: sharedAccess && module.id !== "users" ? "all" : "partial",
          actions: Object.fromEntries(
            module.actions.map((action) => [action.id, sharedAccess && module.id !== "users"]),
          ),
        },
      },
    ]),
  ) as ProjectPermissions;
}

export function UserDetails({ user, projectNames }: { user: User; projectNames: Record<string, string> }) {
  const assignedIds = user.assigned_project_ids || [];
  const legacyUsersProfiles = [
    ...(user.global_access ? [user.global_permissions?.users] : []),
    ...Object.values(user.project_permissions || {}).map((profile) => profile?.users),
  ].filter((permission) => permission?.access === "allow");
  const usersPermission = user.global_access ? fullUsersPermissions() : user.users_permissions || {
    access: legacyUsersProfiles.length ? "allow" : "block",
    read: { export_report: legacyUsersProfiles.some((permission) => permission?.read.export_report) },
    write: { mode: "partial", actions: Object.fromEntries(usersActions.map((action) => [action.id, legacyUsersProfiles.some((permission) => permission?.write.mode === "all" || permission?.write.actions[action.id])])) },
  };
  const profiles = [
    ...(user.global_access ? [{ name: "Global project permissions", permissions: user.global_permissions }] : []),
    ...assignedIds.map((id, index) => ({
      name: `${projectNames[id] || user.assigned_projects?.[index] || id}${user.global_access ? " · Project override" : ""}`,
      permissions: user.global_access ? { ...user.global_permissions, ...user.project_permissions?.[id] } : user.project_permissions?.[id],
    })),
  ];
  return <div className="user-details-view">
    <dl className="user-details-grid">
      {[['Full name', user.name], ['Username', user.username], ['Email', user.email || 'Not provided'], ['Contact number', user.phone || 'Not provided'], ['Account status', user.active === false ? 'Inactive' : 'Active'], ['Access scope', user.global_access ? 'Global · All projects' : assignedIds.length ? 'Selected projects' : 'Users only'], ['Assigned projects', user.global_access ? 'All available projects' : assignedIds.map((id, index) => projectNames[id] || user.assigned_projects?.[index] || id).join(', ') || 'None']].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
    </dl>
    <h3>Users page permissions</h3>
    <div className="table-scroll"><table className="data-table"><thead><tr><th>Permission</th><th>Access</th></tr></thead><tbody>
      <tr><td>Users page</td><td>{usersPermission.access === "allow" ? "Allowed" : "Blocked"}</td></tr>
      <tr><td>Export user directory</td><td>{usersPermission.access === "allow" && usersPermission.read.export_report ? "Allowed" : "Blocked"}</td></tr>
      {usersActions.map((action) => <tr key={action.id}><td>{action.label}</td><td>{usersPermission.access === "allow" && (usersPermission.write.mode === "all" || usersPermission.write.actions[action.id]) ? "Allowed" : "Blocked"}</td></tr>)}
    </tbody></table></div>
    <h3>Audit Log permissions</h3>
    <div className="table-scroll"><table className="data-table"><thead><tr><th>Permission</th><th>Access</th></tr></thead><tbody><tr><td>Audit Log</td><td>{user.global_access || user.audit_permissions?.access === 'allow' ? 'Allowed' : 'Blocked'}</td></tr><tr><td>Export Report</td><td>{user.global_access || user.audit_permissions?.access === 'allow' && user.audit_permissions.read.export_report ? 'Allowed' : 'Blocked'}</td></tr></tbody></table></div>
    {profiles.map((profile) => <section key={profile.name}>
      <h3>{profile.name}</h3>
      <div className="table-scroll"><table className="data-table"><thead><tr><th>Module</th><th>Access</th><th>Export</th><th>Write actions</th></tr></thead><tbody>
        {projectModules.filter((module) => module.id !== "users").map((module) => {
          const permission = profile.permissions?.[module.id];
          const allowed = permission?.access === "allow";
          return <tr key={module.id}><td>{module.label}</td><td>{allowed ? "Allowed" : "Blocked"}</td><td>{allowed && permission.read.export_report ? "Allowed" : "Blocked"}</td><td>{!allowed ? "None" : permission.write.mode === "all" ? "All" : module.actions.filter((action) => permission.write.actions[action.id]).map((action) => action.label).join(', ') || "None"}</td></tr>;
        })}
      </tbody></table></div>
    </section>)}
  </div>;
}

function UserHistoryTable({ user, projectNames }: { user: User; projectNames: Record<string, string> }) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const history = useQuery({ queryKey: ["users", user.id, "history", page, pageSize, search], queryFn: () => api.userHistory(user.id, page, pageSize, search) });
  const total = history.data?.total || 0;
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return <>
    <div className="register-tools"><div className="search-wrap"><Search size={15} /><input aria-label="Search user history" placeholder="Search history" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></div></div>
    <div className="table-scroll"><table className="data-table"><thead><tr><th>Date</th><th>Action</th><th>Performed by</th><th>Record</th><th>Details</th></tr></thead><tbody>
      {history.isLoading ? <tr><td colSpan={5}><div className="loading-line" /></td></tr> : history.data?.items.length ? history.data.items.map((entry) => <tr key={entry.id}><td>{new Date(entry.occurred_at).toLocaleString("en-IN")}</td><td>{entry.action.replaceAll("_", " ")}</td><td>{entry.actor}</td><td>{entry.entity_type}</td><td><details><summary>View changes</summary><ul className="user-history-details">{userHistoryChanges(entry.action, entry.details, projectNames).map((change, index) => <li key={index}>{change}</li>)}</ul></details></td></tr>) : <tr><td colSpan={5}><EmptyState title={search ? "No matching history" : "No history recorded"} note="" /></td></tr>}
    </tbody></table></div>
    <QueryError error={history.error} onRetry={() => void history.refetch()} />
    <div className="register-pagination"><label>Rows per page <select aria-label="History rows per page" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }}>{[5, 10, 20, 50].map((size) => <option key={size} value={size}>{size}</option>)}</select></label><span>{total} records · Page {page} of {pages}</span><div className="row-actions"><button type="button" className="icon-button" title="Previous history page" aria-label="Previous history page" disabled={page <= 1 || history.isFetching} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /></button><button type="button" className="icon-button" title="Next history page" aria-label="Next history page" disabled={page >= pages || history.isFetching} onClick={() => setPage(page + 1)}><ChevronRight size={16} /></button></div></div>
  </>;
}

export function UsersView({
  currentUser,
  projectId,
  csrf,
}: {
  currentUser: User;
  projectId: string;
  csrf: string;
}) {
  const queryClient = useQueryClient();
  const canManageUsers = currentUser.permissions?.users.write === true;
  const usersGrants = currentUser.permissions?.users;
  const canExportUsers = currentUser.permissions?.users.export_report === true;
  const users = useQuery({
    queryKey: ["users"],
    queryFn: api.users,
  });
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [search, setSearch] = useState("");
  const [historyUser, setHistoryUser] = useState<User | null>(null);
  const [viewingUser, setViewingUser] = useState<User | null>(null);
  const [userAction, setUserAction] = useState<{ user: User; kind: "reset" | "status" | "delete" } | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetPasswordConfirm, setResetPasswordConfirm] = useState("");
  const [actionError, setActionError] = useState("");
  const lifecycleAction = useMutation({
    mutationFn: async () => {
      if (!userAction) return;
      if (userAction.kind === "reset") return api.resetUserPassword(userAction.user.id, resetPassword, csrf);
      if (userAction.kind === "status") return api.setUserActive(userAction.user.id, userAction.user.active === false, csrf);
      return api.deleteUser(userAction.user.id, csrf);
    },
    onSuccess: async () => {
      setUserAction(null);
      setResetPassword("");
      setResetPasswordConfirm("");
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => setActionError(error instanceof Error ? error.message : "Could not update this account."),
  });
  const openUserAction = (user: User, kind: "reset" | "status" | "delete") => {
    setActionError("");
    setResetPassword("");
    setResetPasswordConfirm("");
    setUserAction({ user, kind });
  };
  const [userFormOpen, setUserFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [userName, setUserName] = useState("");
  const [userEmail, setUserEmail] = useState("");
  const [userPhone, setUserPhone] = useState("");
  const [username, setUsername] = useState("");
  const [userPassword, setUserPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [globalAccess, setGlobalAccess] = useState(false);
  const [sharedProjectAccess, setSharedProjectAccess] = useState(false);
  const sharedPermissionEditor = globalAccess || sharedProjectAccess;
  const [usersPermissionDraft, setUsersPermissionDraft] = useState(defaultProjectPermissions().users);
  const [auditPermissionDraft, setAuditPermissionDraft] = useState(defaultProjectPermissions().users);
  const [globalPermissionDraft, setGlobalPermissionDraft] =
    useState<ProjectPermissions>(defaultProjectPermissions());
  const [userProjectIds, setUserProjectIds] = useState<string[]>([]);
  const [activePermissionProjectId, setActivePermissionProjectId] =
    useState("");
  const [projectPermissionDrafts, setProjectPermissionDrafts] = useState<
    Record<string, ProjectPermissions>
  >({});
  const [userFormError, setUserFormError] = useState("");
  const [wizardStep, setWizardStep] = useState<1 | 2>(1);
  const passwordTooShort = userPassword.length > 0 && userPassword.length < 6;
  const passwordsMismatch =
    passwordConfirm.length > 0 && userPassword !== passwordConfirm;
  const allUsers = users.data?.items || [];
  const filteredUsers = allUsers.filter((user) =>
    `${user.name} ${user.username} ${user.email} ${(user.assigned_projects || []).join(" ")}`
      .toLowerCase()
      .includes(search.trim().toLowerCase()),
  );
  const activeCount = filteredUsers.filter(
    (user) => user.active !== false,
  ).length;
  const resetUserForm = () => {
    setUserFormOpen(false);
    setEditingUser(null);
    setUserName("");
    setUserEmail("");
    setUserPhone("");
    setUsername("");
    setUserPassword("");
    setPasswordConfirm("");
    setGlobalAccess(false);
    setSharedProjectAccess(false);
    setUsersPermissionDraft(defaultProjectPermissions().users);
    setAuditPermissionDraft(defaultProjectPermissions().users);
    setGlobalPermissionDraft(defaultProjectPermissions());
    setUserProjectIds([]);
    setProjectPermissionDrafts({});
    setActivePermissionProjectId("");
    setUserFormError("");
  };
  const createUser = useMutation({
    mutationFn: () => {
      const payload = {
        name: userName.trim(),
        email: userEmail.trim() || null,
        phone: userPhone.trim() || null,
        username: username.trim(),
        project_ids: userProjectIds,
        project_permissions: Object.fromEntries(
          userProjectIds
            .filter((id) => sharedProjectAccess || projectPermissionDrafts[id])
            .map((id) => [id, { ...(sharedProjectAccess ? globalPermissionDraft : projectPermissionDrafts[id]), users: usersPermissionDraft }]),
        ),
        global_access: globalAccess,
        audit_permissions: globalAccess ? { access: 'allow' as const, read: { export_report: true }, write: { mode: 'partial' as const, actions: {} } } : auditPermissionDraft,
        users_permissions: globalAccess ? fullUsersPermissions() : usersPermissionDraft,
        global_permissions: globalAccess ? { ...globalPermissionDraft, users: fullUsersPermissions() } : undefined,
      };
      return editingUser
        ? api.updateUser(
            editingUser.id,
            { ...payload, ...(userPassword ? { password: userPassword } : {}) },
            csrf,
          )
        : api.createUser(
            { ...payload, password: userPassword },
            csrf,
          );
    },
    onSuccess: async () => {
      resetUserForm();
      await queryClient.invalidateQueries({
        queryKey: ["users"],
      });
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (error) =>
      setUserFormError(
        error instanceof ApiError ? error.message : "Could not save this user.",
      ),
  });
  const openUserEditor = (target?: User) => {
    const ids = target?.assigned_project_ids || [];
    const firstProfile = target?.project_permissions?.[ids[0]];
    const hasSharedProfile = !target?.global_access && !!firstProfile && ids.every(
      (id) => JSON.stringify(target?.project_permissions?.[id]) === JSON.stringify(firstProfile),
    );
    setEditingUser(target || null);
    setUserFormOpen(true);
    setUserName(target?.name || "");
    setUserEmail(target?.email || "");
    setUserPhone(target?.phone || "");
    setUsername(target?.username || "");
    setUserPassword("");
    setPasswordConfirm("");
    setGlobalAccess(target?.global_access || false);
    setAuditPermissionDraft(target?.global_access ? { access: 'allow', read: { export_report: true }, write: { mode: 'partial', actions: {} } } : target?.audit_permissions || defaultProjectPermissions().users);
    setSharedProjectAccess(hasSharedProfile);
    const usersProfiles = [
      ...(target?.global_access ? [target.global_permissions?.users] : []),
      ...ids.map((id) => target?.project_permissions?.[id]?.users),
    ].filter((permission) => permission?.access === "allow");
    setUsersPermissionDraft(target?.global_access ? fullUsersPermissions() : target?.users_permissions || {
      access: usersProfiles.length ? "allow" : "block",
      read: { export_report: usersProfiles.some((permission) => permission?.read.export_report) },
      write: {
        mode: "partial",
        actions: Object.fromEntries(usersActions.map((action) => [action.id, usersProfiles.some((permission) => permission?.write.mode === "all" || permission?.write.actions[action.id] === true)])),
      },
    });
    setGlobalPermissionDraft(
      target?.global_permissions || (hasSharedProfile ? firstProfile : null) || defaultProjectPermissions(),
    );
    setUserProjectIds(ids);
    setActivePermissionProjectId(ids[0] || projectId);
    setProjectPermissionDrafts(
      Object.fromEntries(
        ids.map((id) => [
          id,
          target?.project_permissions?.[id] || defaultProjectPermissions(),
        ]),
      ),
    );
    setUserFormError("");
    setWizardStep(1);
  };
  const activeProjectPermissions =
    projectPermissionDrafts[activePermissionProjectId] ||
    defaultProjectPermissions();
  const updateProjectPermission = (
    moduleId: PermissionModule,
    update: (
      value: ProjectPermissions[PermissionModule],
    ) => ProjectPermissions[PermissionModule],
  ) => {
    setProjectPermissionDrafts((previous) => ({
      ...previous,
      [activePermissionProjectId]: {
        ...(previous[activePermissionProjectId] || defaultProjectPermissions()),
        [moduleId]: update(
          (previous[activePermissionProjectId] || defaultProjectPermissions())[
            moduleId
          ],
        ),
      },
    }));
  };
  const updateGlobalPermission = (
    moduleId: PermissionModule,
    update: (
      value: ProjectPermissions[PermissionModule],
    ) => ProjectPermissions[PermissionModule],
  ) => {
    setGlobalPermissionDraft((previous) => ({
      ...previous,
      [moduleId]: update(previous[moduleId]),
    }));
  };
  const exportUsers = async () => {
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    await document.fonts.ready;
    const previousTitle = document.title;
    document.title = "User Directory";
    window.addEventListener(
      "afterprint",
      () => {
        document.title = previousTitle;
      },
      { once: true },
    );
    window.print();
  };
  return (
    <div className="users-view">
      <ExportHeader reportTitle="User Directory" />
      {viewingUser && <ModalFrame title={`User details · ${viewingUser.username}`} className="payment-history-modal user-details-modal" onClose={() => setViewingUser(null)}><UserDetails user={viewingUser} projectNames={Object.fromEntries((projects.data?.items || []).map((project) => [project.id, project.name]))} /></ModalFrame>}
      {historyUser && <ModalFrame title={`User history · ${historyUser.username}`} className="payment-history-modal" onClose={() => setHistoryUser(null)}><UserHistoryTable user={historyUser} projectNames={Object.fromEntries((projects.data?.items || []).map((project) => [project.id, project.name]))} /></ModalFrame>}
      {userAction && <ModalFrame title={userAction.kind === "reset" ? "Reset password" : userAction.kind === "delete" ? "Delete user" : userAction.user.active === false ? "Activate user" : "Deactivate user"} onClose={() => { if (!lifecycleAction.isPending) setUserAction(null); }}>
        <form className="form-grid" onSubmit={(event) => {
          event.preventDefault();
          setActionError("");
          if (userAction.kind === "reset" && (resetPassword.length < 6 || resetPassword !== resetPasswordConfirm)) { setActionError("Enter matching passwords with at least 6 characters."); return; }
          lifecycleAction.mutate();
        }}>
          <strong className="full">{userAction.user.name} (@{userAction.user.username})</strong>
          {userAction.kind === "reset" ? <>
            <label className="field full">New password<input type="password" autoComplete="new-password" required minLength={6} maxLength={128} value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} /></label>
            <label className="field full">Confirm new password<input type="password" autoComplete="new-password" required minLength={6} maxLength={128} value={resetPasswordConfirm} onChange={(event) => setResetPasswordConfirm(event.target.value)} /></label>
            <p className="field-hint full">Existing sessions will be signed out.</p>
          </> : <p className="full">{userAction.kind === "delete" ? "Delete this account from the user directory and permanently prevent sign-in? Existing project and audit records will be retained." : userAction.user.active === false ? "Allow this user to sign in again? Existing permissions will be retained." : "Prevent this user from signing in and end their existing sessions?"}</p>}
          {actionError && <div className="form-error full" role="alert">{actionError}</div>}
          <div className="user-wizard-actions full"><button type="button" className="button-secondary" disabled={lifecycleAction.isPending} onClick={() => setUserAction(null)}>Cancel</button><button type="submit" className="button-primary" disabled={lifecycleAction.isPending}>{lifecycleAction.isPending ? "Saving..." : userAction.kind === "reset" ? "Reset password" : userAction.kind === "delete" ? "Delete user" : userAction.user.active === false ? "Activate user" : "Deactivate user"}</button></div>
        </form>
      </ModalFrame>}
      <PageTitle
        eyebrow="ACCESS CONTROL"
        title="Users"
        subtitle="Manage user accounts and project-specific permissions."
        action={
          <div className="overview-actions">
          <button className="button-secondary export-report-action" onClick={exportUsers} disabled={!canExportUsers || users.isFetching || users.isError}><Download size={14} />Export report</button>
          <button className="button-primary" disabled={!canManageUsers} onClick={() => openUserEditor()}>
            <Plus size={15} />
            Add user
          </button>
          </div>
        }
      />
      <section className="panel table-panel users-directory-panel">
        <PanelHeading
          title="All users"
          meta={`${activeCount} active account${activeCount === 1 ? "" : "s"} · ${filteredUsers.length} total`}
          action={
            <div className="register-tools">
              <div className="search-wrap">
                <Search size={15} />
                <input
                  aria-label="Search users"
                  placeholder="Search users"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </div>
            </div>
          }
        />
        <div className="table-scroll">
          <table className="data-table users-directory-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Contact</th>
                <th>Access scope</th>
                <th>Account</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.isLoading ? (
                <tr>
                  <td colSpan={5}>
                    <div className="loading-line" />
                  </td>
                </tr>
              ) : filteredUsers.length ? (
                filteredUsers.map((user) => {
                  const isCurrentUser = user.id === currentUser.id;
                  return (
                    <tr key={user.id}>
                      <td>
                        <strong className="strong-cell">{user.name}</strong>
                        <small className="users-directory-subtitle">
                          @{user.username}
                        </small>
                      </td>
                      <td className="users-project-access">
                        {[user.email, user.phone].filter(Boolean).join(" · ") ||
                          "No contact details"}
                      </td>
                      <td>
                        {user.global_access ? (
                          <span className="status-pill complete">Global</span>
                        ) : (
                          <span className="status-pill planning">{user.assigned_project_ids?.length ? "Project" : "Users only"}</span>
                        )}
                      </td>
                      <td>
                        <span
                          className={`status-pill ${user.active === false ? "hold" : "complete"}`}
                        >
                          {user.active === false ? "Inactive" : "Active"}
                        </span>
                      </td>
                      <td>
                          <div className="row-actions user-account-actions">
                            <span className="row-action-tooltip" data-tooltip="View user"><button type="button" className="icon-button" title="View user" aria-label={`View user ${user.username}`} onClick={() => setViewingUser(user)}><Eye size={15} /></button></span>
                            {!isCurrentUser && canManageUsers && <span className="row-action-tooltip" data-tooltip="Edit user"><button type="button" className="icon-button" title="Edit user" aria-label={`Edit user ${user.username}`} onClick={() => openUserEditor(user)}><Pencil size={15} /></button></span>}
                            {!isCurrentUser && usersGrants?.reset_password && <span className="row-action-tooltip" data-tooltip="Reset password"><button type="button" className="icon-button" title="Reset password" aria-label={`Reset password for ${user.username}`} onClick={() => openUserAction(user, "reset")}><KeyRound size={15} /></button></span>}
                            {!isCurrentUser && usersGrants?.activate_deactivate && <span className="row-action-tooltip" data-tooltip={user.active === false ? "Activate user" : "Deactivate user"}><button type="button" className="icon-button" title={user.active === false ? "Activate user" : "Deactivate user"} aria-label={`${user.active === false ? "Activate" : "Deactivate"} user ${user.username}`} onClick={() => openUserAction(user, "status")}>{user.active === false ? <UserCheck size={15} /> : <UserX size={15} />}</button></span>}
                            {!isCurrentUser && usersGrants?.delete_user && <span className="row-action-tooltip" data-tooltip="Delete user"><button type="button" className="icon-button" title="Delete user" aria-label={`Delete user ${user.username}`} onClick={() => openUserAction(user, "delete")}><Trash2 size={15} /></button></span>}
                            {usersGrants?.history && <span className="row-action-tooltip" data-tooltip="User history"><button type="button" className="icon-button" title="User history" aria-label={`History for ${user.username}`} onClick={() => setHistoryUser(user)}><History size={15} /></button></span>}
                          </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5}>
                    <EmptyState
                      title={
                        search
                          ? "No matching users"
                          : "No users"
                      }
                      note={
                        search
                          ? "Try another name, email, or username."
                          : "Add users and configure their project access."
                      }
                    />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <QueryError error={users.error} onRetry={() => void users.refetch()} />
      </section>
      {userFormOpen && (
        <ModalFrame
          title={editingUser ? "Edit user" : "Add user"}
          className="user-create-modal"
          onClose={resetUserForm}
        >
          <form
            className="user-create-form"
            onSubmit={(event) => {
              event.preventDefault();
              setUserFormError("");
              if (wizardStep === 1) {
                if (!userName.trim() || !username.trim()) {
                  setUserFormError(
                    "Enter the full name and username to continue.",
                  );
                  return;
                }
                if (
                  (!editingUser && userPassword.length < 6) ||
                  (userPassword &&
                    (userPassword.length < 6 ||
                      userPassword !== passwordConfirm))
                ) {
                  setUserFormError(
                    "Enter matching passwords with at least 6 characters.",
                  );
                  return;
                }
                setWizardStep(2);
                return;
              }
              if (!globalAccess && userProjectIds.length === 0 && usersPermissionDraft.access !== "allow") {
                setUserFormError("Assign a project, enable Global access, or allow Users page access.");
                return;
              }
              if (
                !globalAccess && !sharedProjectAccess &&
                userProjectIds.some((id) => !projectPermissionDrafts[id])
              ) {
                setUserFormError("Set permissions for every assigned project.");
                return;
              }
              createUser.mutate();
            }}
          >
            <div className="form-grid">
              <div
                className="user-wizard-progress full"
                aria-label={`Step ${wizardStep} of 2`}
              >
                <span className={wizardStep === 1 ? "current" : "complete"}>
                  1 <b>Account details</b>
                </span>
                <i />
                <span className={wizardStep === 2 ? "current" : ""}>
                  2 <b>Access permissions</b>
                </span>
              </div>
              {wizardStep === 1 && (
                <>
                  <label className="field full">
                    Full name
                    <input
                      required
                      minLength={2}
                      maxLength={160}
                      autoComplete="name"
                      placeholder="Employee name"
                      value={userName}
                      onChange={(event) => setUserName(event.target.value)}
                    />
                  </label>
                  <label className="field full">
                    Work email (optional)
                    <input
                      type="email"
                      maxLength={255}
                      autoComplete="email"
                      placeholder="name@company.com"
                      value={userEmail}
                      onChange={(event) => setUserEmail(event.target.value)}
                    />
                  </label>
                  <label className="field full">
                    Contact number (optional)
                    <input
                      type="tel"
                      maxLength={40}
                      autoComplete="tel"
                      placeholder="+1 555 010 1234"
                      value={userPhone}
                      onChange={(event) => setUserPhone(event.target.value)}
                    />
                  </label>
                  <label className="field full">
                    Username
                    <input
                      required
                      minLength={3}
                      maxLength={80}
                      pattern={String.raw`[A-Za-z0-9._\-]+`}
                      autoComplete="username"
                      placeholder="Letters, numbers, dot, underscore, or hyphen"
                      value={username}
                      readOnly={!!editingUser}
                      onChange={(event) => setUsername(event.target.value)}
                    />
                  </label>
                  <label className="field full">
                    Password
                    {editingUser && (
                      <small>{usersGrants?.reset_password ? "Leave blank to keep current password." : "Reset Password permission is required to change the password."}</small>
                    )}
                    <input
                      required={!editingUser}
                      type="password"
                      disabled={!!editingUser && !usersGrants?.reset_password}
                      minLength={6}
                      maxLength={128}
                      autoComplete="new-password"
                      placeholder="At least 6 characters"
                      aria-invalid={passwordTooShort}
                      value={userPassword}
                      onChange={(event) => {
                        setUserPassword(event.target.value);
                        setUserFormError("");
                      }}
                    />
                    {passwordTooShort && (
                      <small className="user-password-feedback" role="status">
                        Password must be at least 6 characters.
                      </small>
                    )}
                  </label>
                  {(!editingUser || userPassword) && (
                    <label className="field full">
                      Confirm password
                      <input
                        required={!editingUser || !!userPassword}
                        type="password"
                        minLength={6}
                        maxLength={128}
                        autoComplete="new-password"
                        placeholder="Re-enter password"
                        aria-invalid={passwordsMismatch}
                        value={passwordConfirm}
                        onChange={(event) => {
                          setPasswordConfirm(event.target.value);
                          setUserFormError("");
                        }}
                      />
                      {passwordsMismatch && (
                        <small className="user-password-feedback" role="status">
                          Passwords do not match.
                        </small>
                      )}
                    </label>
                  )}
                </>
              )}
              {wizardStep === 2 && (
                <>
                  <label className="global-access-toggle full">
                    <input
                      type="checkbox"
                      checked={globalAccess}
                      onChange={(event) => {
                        setGlobalAccess(event.target.checked);
                        setSharedProjectAccess(false);
                        if (event.target.checked) setUsersPermissionDraft(fullUsersPermissions());
                        if (event.target.checked) setAuditPermissionDraft({ access: 'allow', read: { export_report: true }, write: { mode: 'partial', actions: {} } });
                      }}
                    />
                    <span>
                      <strong>Global access</strong>
                      <small>
                        Apply one permission profile across all available
                        projects, including all Users page permissions.
                      </small>
                    </span>
                  </label>
                  {!globalAccess && (
                    <label className="global-access-toggle full">
                      <input
                        type="checkbox"
                        checked={sharedProjectAccess}
                        onChange={(event) => {
                          const enabled = event.target.checked;
                          if (enabled) {
                            setGlobalPermissionDraft(defaultProjectPermissions(true));
                          } else {
                            setProjectPermissionDrafts((previous) => ({
                              ...previous,
                              ...Object.fromEntries(userProjectIds.map((id) => [id, globalPermissionDraft])),
                            }));
                          }
                          setSharedProjectAccess(enabled);
                        }}
                      />
                      <span>
                        <strong>Shared access for selected projects</strong>
                        <small>Allow all read, write, and export permissions except Users for the selected projects.</small>
                      </span>
                    </label>
                  )}
                  {!!projects.data?.items.length && (
                    <fieldset className="user-project-assignments full">
                      <legend>Assigned projects</legend>
                      {projects.isLoading ? (
                        <div className="loading-line" />
                      ) : (
                        (projects.data?.items || []).map((project) => (
                          <label key={project.id}>
                            <input
                              type="checkbox"
                              checked={userProjectIds.includes(project.id)}
                              onChange={(event) => {
                                const add = event.target.checked;
                                setUserProjectIds((previous) =>
                                  add
                                    ? [...previous, project.id]
                                    : previous.filter(
                                        (id) => id !== project.id,
                                      ),
                                );
                                if (add)
                                  setProjectPermissionDrafts((previous) => ({
                                    ...previous,
                                    [project.id]:
                                      previous[project.id] ||
                                      defaultProjectPermissions(),
                                  }));
                                else if (
                                  activePermissionProjectId === project.id
                                )
                                  setActivePermissionProjectId(
                                    userProjectIds.find(
                                      (id) => id !== project.id,
                                    ) || "",
                                  );
                              }}
                            />
                            <span className="user-assigned-project-name">{project.name}</span>
                            <span className={`status-pill ${statusClass(project.status)}`}>{project.status}</span>
                          </label>
                        ))
                      )}
                    </fieldset>
                  )}
                  {(globalAccess || !!userProjectIds.length) && (
                    <details className="project-permission-editor full">
                      <summary>
                        Configure module permissions{" "}
                        <span>
                          {globalAccess
                            ? "Global"
                            : sharedProjectAccess
                              ? `${userProjectIds.length} selected projects · Shared profile`
                            : `${userProjectIds.length} project${userProjectIds.length === 1 ? "" : "s"} assigned`}
                        </span>
                      </summary>
                      {!sharedPermissionEditor && !!userProjectIds.length && (
                        <label className="field">
                          Project
                          <select
                            aria-label="Project permissions"
                            value={activePermissionProjectId}
                            onChange={(event) =>
                              setActivePermissionProjectId(event.target.value)
                            }
                          >
                            {userProjectIds.map((id) => (
                              <option key={id} value={id}>
                                {projects.data?.items.find(
                                  (project) => project.id === id,
                                )?.name || "Project"}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                      {projectModules.filter((module) => module.id !== "users").map((module) => {
                        const permission = sharedPermissionEditor
                          ? globalPermissionDraft[module.id]
                          : activeProjectPermissions[module.id];
                        const updatePermission = (
                          update: (
                            value: ProjectPermissions[PermissionModule],
                          ) => ProjectPermissions[PermissionModule],
                        ) =>
                          sharedPermissionEditor
                            ? updateGlobalPermission(module.id, update)
                            : updateProjectPermission(module.id, update);
                        return (
                          <details
                            className="project-module-permission"
                            key={module.id}
                          >
                            <summary>
                              {module.label}
                              <span>
                                {permission.access === "allow"
                                  ? "Allowed"
                                  : "Blocked"}
                              </span>
                            </summary>
                            <div className="project-permission-access">
                              <strong>Access</strong>
                              <label>
                                <input
                                  type="radio"
                                  name={`${globalAccess ? "global" : activePermissionProjectId}-${module.id}-access`}
                                  checked={permission.access === "allow"}
                                  onChange={() =>
                                    updatePermission((value) => ({
                                      ...value,
                                      access: "allow",
                                    }))
                                  }
                                />
                                Allow
                              </label>
                              <label>
                                <input
                                  type="radio"
                                  name={`${globalAccess ? "global" : activePermissionProjectId}-${module.id}-access`}
                                  checked={permission.access === "block"}
                                  onChange={() =>
                                    updatePermission((value) => ({
                                      ...value,
                                      access: "block",
                                    }))
                                  }
                                />
                                Block
                              </label>
                            </div>
                            {permission.access === "allow" && (
                              <>
                                <div className="project-permission-subsection">
                                  <strong>Read</strong>
                                  <label>
                                    <input
                                      type="checkbox"
                                      checked={permission.read.export_report}
                                      onChange={(event) =>
                                        updatePermission((value) => ({
                                          ...value,
                                          read: {
                                            ...value.read,
                                            export_report: event.target.checked,
                                          },
                                        }))
                                      }
                                    />
                                    Export Report
                                  </label>
                                </div>
                                <div className="project-permission-subsection">
                                  <strong>Write</strong>
                                  <div className="project-permission-modes">
                                    <label>
                                      <input
                                        type="radio"
                                        name={`${globalAccess ? "global" : activePermissionProjectId}-${module.id}-write`}
                                        checked={
                                          permission.write.mode === "all"
                                        }
                                        onChange={() =>
                                          updatePermission((value) => ({
                                            ...value,
                                            write: {
                                              ...value.write,
                                              mode: "all",
                                            },
                                          }))
                                        }
                                      />
                                      All
                                    </label>
                                    <label>
                                      <input
                                        type="radio"
                                        name={`${globalAccess ? "global" : activePermissionProjectId}-${module.id}-write`}
                                        checked={
                                          permission.write.mode === "partial"
                                        }
                                        onChange={() =>
                                          updatePermission((value) => ({
                                            ...value,
                                            write: {
                                              ...value.write,
                                              mode: "partial",
                                            },
                                          }))
                                        }
                                      />
                                      Partial
                                    </label>
                                  </div>
                                  <div className="project-permission-actions">
                                    {module.actions.map((action) => (
                                      <label key={action.id}>
                                        <input
                                          type="checkbox"
                                          disabled={
                                            permission.write.mode === "all"
                                          }
                                          checked={
                                            permission.write.mode === "all" ||
                                            permission.write.actions[
                                              action.id
                                            ] === true
                                          }
                                          onChange={(event) =>
                                            updatePermission((value) => ({
                                              ...value,
                                              write: {
                                                ...value.write,
                                                actions: {
                                                  ...value.write.actions,
                                                  [action.id]:
                                                    event.target.checked,
                                                },
                                              },
                                            }))
                                          }
                                        />
                                        {action.label}
                                      </label>
                                    ))}
                                  </div>
                                </div>
                              </>
                            )}
                          </details>
                        );
                      })}
                    </details>
                  )}
                  <fieldset className="project-permission-editor full" disabled={globalAccess}>
                    <legend>Audit Log permissions</legend>
                    <p className="field-hint">Review activity only in projects this user can access. Global access includes Audit Log and all-project report exports.</p>
                    <div className="project-permission-access"><strong>Access</strong><label><input type="radio" name="audit-access" checked={auditPermissionDraft.access === 'allow'} onChange={() => setAuditPermissionDraft(previous => ({ ...previous, access: 'allow' }))} />Allow</label><label><input type="radio" name="audit-access" checked={auditPermissionDraft.access === 'block'} onChange={() => setAuditPermissionDraft(previous => ({ ...previous, access: 'block' }))} />Block</label></div>
                    {auditPermissionDraft.access === 'allow' && <div className="project-permission-subsection"><strong>Read</strong><label><input type="checkbox" checked={auditPermissionDraft.read.export_report} onChange={event => setAuditPermissionDraft(previous => ({ ...previous, read: { export_report: event.target.checked } }))} />Export Report</label></div>}
                  </fieldset>
                  <fieldset className="project-permission-editor full" disabled={globalAccess}>
                    <legend>Users page permissions</legend>
                    <p className="field-hint">{globalAccess ? "Global access includes every Users page permission." : "Controls the standalone Users page independently of projects. No project assignment is required. Each action requires its own permission."}</p>
                    <div className="project-permission-access">
                      <strong>Access</strong>
                      <label><input type="radio" name="users-page-access" checked={usersPermissionDraft.access === "allow"} onChange={() => setUsersPermissionDraft((previous) => ({ ...previous, access: "allow" }))} />Allow</label>
                      <label><input type="radio" name="users-page-access" checked={usersPermissionDraft.access === "block"} onChange={() => setUsersPermissionDraft((previous) => ({ ...previous, access: "block" }))} />Block</label>
                    </div>
                    {usersPermissionDraft.access === "allow" && (
                      <div className="project-permission-subsection">
                        <label><input type="checkbox" checked={usersPermissionDraft.read.export_report} onChange={(event) => setUsersPermissionDraft((previous) => ({ ...previous, read: { export_report: event.target.checked } }))} />Export user directory</label>
                        <strong>Actions</strong>
                        {usersActions.map((action) => <label key={action.id}><input type="checkbox" checked={usersPermissionDraft.write.mode === "all" || usersPermissionDraft.write.actions[action.id] === true} onChange={(event) => setUsersPermissionDraft((previous) => ({ ...previous, write: { mode: "partial", actions: { ...Object.fromEntries(usersActions.map((entry) => [entry.id, previous.write.mode === "all" || previous.write.actions[entry.id] === true])), [action.id]: event.target.checked } } }))} />{action.label}</label>)}
                      </div>
                    )}
                  </fieldset>
                </>
              )}
              {userFormError && (
                <div className="form-error full" role="alert">
                  {userFormError}
                </div>
              )}
              <div className="user-wizard-actions full">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={
                    wizardStep === 1
                      ? resetUserForm
                      : () => {
                          setWizardStep(1);
                          setUserFormError("");
                        }
                  }
                >
                  {wizardStep === 1 ? "Cancel" : "Back"}
                </button>
                <button
                  type="submit"
                  className="button-primary"
                  disabled={
                    createUser.isPending ||
                    (wizardStep === 2 && projects.isLoading)
                  }
                >
                  {wizardStep === 1
                    ? "Next"
                    : createUser.isPending
                      ? "Saving…"
                      : editingUser
                        ? "Save user"
                        : "Add user"}
                </button>
              </div>
            </div>
          </form>
        </ModalFrame>
      )}
    </div>
  );
}
