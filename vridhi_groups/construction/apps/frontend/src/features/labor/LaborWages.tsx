import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Banknote,
  BriefcaseBusiness,
  ChevronDown,
  Check,
  ClipboardCheck,
  Download,
  FilePenLine,
  FileText,
  History,
  Pencil,
  Plus,
  Search,
  UserX,
  Users,
} from "lucide-react";
import {
  api,
  type LaborContractRecord,
  type LaborLedger,
  type Project,
  type ProjectModulePermission,
} from "../../lib/api";
import { currency, dateLabel, todayISO } from "../../lib/format";
import {
  EmptyState,
  FormActions,
  Kpi,
  MutationError,
  PageTitle,
  PanelHeading,
  QueryError,
} from "../../components/ui";
import { ModalFrame } from "../../components/ModalFrame";
import { ExportHeader } from "../../components/ExportHeader";

export function LaborWages({
  project,
  projectId,
  csrf,
  canWrite = true,
  projectPermissions,
}: {
  project?: Project;
  projectId: string;
  csrf: string;
  canWrite?: boolean;
  projectPermissions?: ProjectModulePermission;
}) {
  const canAction = (action: string) =>
    canWrite &&
    (!projectPermissions ||
      projectPermissions.write.mode === "all" ||
      projectPermissions.write.actions[action] === true);
  const canExport =
    !projectPermissions || projectPermissions.read.export_report;
  const canDownload = (action: string) =>
    !projectPermissions ||
    (projectPermissions.access === "allow" &&
      projectPermissions.write.actions[action] === true);
  const queryClient = useQueryClient();
  const ledger = useQuery({
    queryKey: ["project", projectId, "labor"],
    queryFn: () => api.laborLedger(projectId),
  });
  const contractsQuery = useQuery({
    queryKey: ["project", projectId, "labor", "contracts"],
    queryFn: () => api.laborContracts(projectId),
  });
  const contractDocuments = useQuery({
    queryKey: ["project", projectId, "labor", "documents"],
    queryFn: () => api.laborContractDocuments(projectId),
  });
  const [dialog, setDialog] = useState<
    | "worker"
    | "worker-edit"
    | "work"
    | "payment"
    | "contract"
    | "addendum"
    | "claim"
    | "claim-payment"
    | null
  >(null);
  const [editingWorkerId, setEditingWorkerId] = useState<string | null>(null);
  const [workerStatusError, setWorkerStatusError] = useState<string | null>(
    null,
  );
  useEffect(() => {
    if (!workerStatusError) return;
    const timer = window.setTimeout(() => setWorkerStatusError(null), 5000);
    return () => window.clearTimeout(timer);
  }, [workerStatusError]);
  const [selectedContractId, setSelectedContractId] = useState("");
  const [selectedClaimId, setSelectedClaimId] = useState("");
  const [historyClaimId, setHistoryClaimId] = useState<string | null>(null);
  const [contractsExpanded, setContractsExpanded] = useState(true);
  const [workersExpanded, setWorkersExpanded] = useState(true);
  const [search, setSearch] = useState("");
  const [contractPage, setContractPage] = useState(1);
  const [contractPageSize, setContractPageSize] = useState(5);
  const [reviewPage, setReviewPage] = useState(1);
  const [reviewPageSize, setReviewPageSize] = useState(5);
  const [addendumPage, setAddendumPage] = useState(1);
  const [addendumPageSize, setAddendumPageSize] = useState(5);
  const [contractDocumentPage, setContractDocumentPage] = useState(1);
  const [contractDocumentPageSize, setContractDocumentPageSize] = useState(5);
  const [workerPage, setWorkerPage] = useState(1);
  const [workerPageSize, setWorkerPageSize] = useState(10);
  const [workPage, setWorkPage] = useState(1);
  const [workPageSize, setWorkPageSize] = useState(10);
  const [workSearch, setWorkSearch] = useState("");
  const [wagePage, setWagePage] = useState(1);
  const [wagePageSize, setWagePageSize] = useState(10);
  const [wageSearch, setWageSearch] = useState("");
  const [wageModeFilter, setWageModeFilter] = useState("");
  const workers = ledger.data?.workers || [];
  const matchingWorkers = workers.filter((worker) =>
    `${worker.name} ${worker.trade}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  const hasActiveWorkers = workers.some((worker) => worker.active);
  const contractClaims =
    contractsQuery.data?.contracts.flatMap((contract) =>
      contract.claims.map((claim) => ({ contract, claim })),
    ) || [];
  const addendumHistory =
    contractsQuery.data?.contracts.flatMap((contract) =>
      contract.addenda.map((addendum) => ({ contract, addendum })),
    ) || [];
  const historyClaim = contractClaims.find(
    ({ claim }) => claim.id === historyClaimId,
  );
  const contractAuthorized =
    contractsQuery.data?.contracts.reduce(
      (sum, contract) => sum + Number(contract.contract_value),
      0,
    ) || 0;
  const contractCertified =
    contractsQuery.data?.contracts.reduce(
      (sum, contract) => sum + Number(contract.certified),
      0,
    ) || 0;
  const contractPaid =
    contractsQuery.data?.contracts.reduce(
      (sum, contract) => sum + Number(contract.paid),
      0,
    ) || 0;
  const contractPayable =
    contractsQuery.data?.contracts.reduce(
      (sum, contract) => sum + Number(contract.payable),
      0,
    ) || 0;
  const workerEarned = Number(ledger.data?.summary.total_earned || 0);
  const workerPaid = Number(ledger.data?.summary.total_paid || 0);
  const workerPayable = Number(ledger.data?.summary.payable || 0);
  const workUnitsNote =
    (ledger.data?.summary.work_units || [])
      .map(({ unit, quantity }) => {
        const label =
          unit === "day"
            ? "Days"
            : unit === "hour"
              ? "Hours"
              : unit === "piece"
                ? "Pieces"
                : `${unit}s`;
        return `${Number(Number(quantity).toFixed(2))} ${label}`;
      })
      .join(" · ") || "No individual work logged";
  const laborCurrency =
    contractsQuery.data?.currency || ledger.data?.currency || "INR";
  const matchingWorkerTotals = matchingWorkers.reduce(
    (totals, worker) => {
      totals.earned += Number(worker.earned);
      totals.paid += Number(worker.paid);
      totals.payable += Number(worker.payable);
      totals.workEntries += worker.work_entry_count;
      for (const workUnit of worker.work_units)
        totals.units[workUnit.unit] =
          (totals.units[workUnit.unit] || 0) + Number(workUnit.quantity);
      return totals;
    },
    {
      earned: 0,
      paid: 0,
      payable: 0,
      workEntries: 0,
      units: {} as Record<string, number>,
    },
  );
  const workerUnitSummary = (units: { unit: string; quantity: string }[]) =>
    units
      .map(
        ({ unit, quantity }) =>
          `${Number(Number(quantity).toFixed(2))} ${unit}${Number(quantity) === 1 ? "" : "s"}`,
      )
      .join(" · ") || "—";
  const matchingWorkerUnits =
    Object.entries(matchingWorkerTotals.units)
      .map(
        ([unit, quantity]) =>
          `${Number(quantity.toFixed(2))} ${unit}${quantity === 1 ? "" : "s"}`,
      )
      .join(" · ") || "—";
  const contracts = contractsQuery.data?.contracts || [];
  const reviewItems = contracts.flatMap((contract) => [
    ...contract.addenda
      .filter((item) => item.status === "Pending approval")
      .map((item) => ({
        id: item.id,
        type: "Contract change",
        reference: contract.contract_number,
        details: `${item.reason} · revised value ${currency(item.revised_value, contract.currency)}`,
        decisionType: "addendum" as const,
      })),
    ...contract.claims
      .filter((item) => item.status === "Pending certification")
      .map((item) => ({
        id: item.id,
        type: "Progress claim",
        reference: item.claim_number,
        details: `${contract.subcontractor_name} · ${item.work_description} · ${currency(item.amount, contract.currency)}`,
        decisionType: "claim" as const,
      })),
  ]);
  const workEntries = ledger.data?.work_entries || [];
  const wagePayments = ledger.data?.payments || [];
  const matchingWorkEntries = workEntries.filter((entry) =>
    `${entry.worker_name} ${entry.trade} ${entry.description}`
      .toLowerCase()
      .includes(workSearch.trim().toLowerCase()),
  );
  const matchingWagePayments = wagePayments.filter(
    (payment) =>
      `${payment.worker_name} ${payment.reference || ""} ${payment.comment || ""}`
        .toLowerCase()
        .includes(wageSearch.trim().toLowerCase()) &&
      (!wageModeFilter || payment.payment_mode === wageModeFilter),
  );
  const wagePaymentModes = Array.from(
    new Set(wagePayments.map((payment) => payment.payment_mode)),
  ).sort();
  const workAmountTotal = matchingWorkEntries.reduce(
    (sum, entry) => sum + Number(entry.amount),
    0,
  );
  const workUnitsTotal = matchingWorkEntries.reduce<Record<string, number>>(
    (totals, entry) => {
      totals[entry.unit] = (totals[entry.unit] || 0) + Number(entry.quantity);
      return totals;
    },
    {},
  );
  const workUnitsSummary = Object.entries(workUnitsTotal)
    .map(
      ([unit, quantity]) =>
        `${Number(quantity.toFixed(2))} ${unit}${quantity === 1 ? "" : "s"}`,
    )
    .join(" · ");
  const wageAmountTotal = matchingWagePayments.reduce(
    (sum, payment) => sum + Number(payment.amount),
    0,
  );
  const pagedContracts = contracts.slice(
    (contractPage - 1) * contractPageSize,
    contractPage * contractPageSize,
  );
  const pagedReviewItems = reviewItems.slice(
    (reviewPage - 1) * reviewPageSize,
    reviewPage * reviewPageSize,
  );
  const pagedAddenda = addendumHistory.slice(
    (addendumPage - 1) * addendumPageSize,
    addendumPage * addendumPageSize,
  );
  const contractDocumentsList = contractDocuments.data?.items || [];
  const pagedContractDocuments = contractDocumentsList.slice(
    (contractDocumentPage - 1) * contractDocumentPageSize,
    contractDocumentPage * contractDocumentPageSize,
  );
  const pagedWorkers = matchingWorkers.slice(
    (workerPage - 1) * workerPageSize,
    workerPage * workerPageSize,
  );
  const pagedWorkEntries = matchingWorkEntries.slice(
    (workPage - 1) * workPageSize,
    workPage * workPageSize,
  );
  const pagedWagePayments = matchingWagePayments.slice(
    (wagePage - 1) * wagePageSize,
    wagePage * wagePageSize,
  );
  const invalidate = async () => {
    await queryClient.invalidateQueries({
      queryKey: ["project", projectId, "labor"],
    });
    await queryClient.invalidateQueries({
      queryKey: ["project", projectId, "labor", "contracts"],
    });
    await queryClient.invalidateQueries({
      queryKey: ["project", projectId, "labor", "documents"],
    });
    setDialog(null);
  };
  const decide = async (
    kind: "addendum" | "claim",
    id: string,
    decision: "approve" | "reject",
  ) => {
    const input = {
      decision,
      comment:
        decision === "approve"
          ? "Reviewed and approved"
          : "Rejected after review",
    };
    if (kind === "addendum")
      await api.decideLaborAddendum(projectId, id, input, csrf);
    else await api.decideLaborClaim(projectId, id, input, csrf);
    await queryClient.invalidateQueries({
      queryKey: ["project", projectId, "labor", "contracts"],
    });
  };
  const toggleWorkerActive = async (workerId: string, active: boolean) => {
    setWorkerStatusError(null);
    try {
      await api.setLaborWorkerActive(projectId, workerId, active, csrf);
      await queryClient.invalidateQueries({
        queryKey: ["project", projectId, "labor"],
      });
    } catch (error) {
      setWorkerStatusError(
        error instanceof Error
          ? error.message
          : "Could not update worker status.",
      );
    }
  };
  const exportReport = async () => {
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    await document.fonts.ready;
    const originalTitle = document.title;
    document.title = `${project?.name || "Project"} - Labor & Wages`;
    window.addEventListener(
      "afterprint",
      () => {
        document.title = originalTitle;
      },
      { once: true },
    );
    await api.recordActivity(projectId, 'labor', 'export');
    window.print();
  };
  const renderPagination = (
    total: number,
    page: number,
    pageSize: number,
    sizes: number[],
    setPage: (page: number) => void,
    setPageSize: (size: number) => void,
    label: string,
  ) =>
    total > 0 && (
      <div className="register-pagination">
        <label>
          Rows per page
          <select
            aria-label={`${label} rows per page`}
            value={pageSize}
            onChange={(event) => {
              setPageSize(Number(event.target.value));
              setPage(1);
            }}
          >
            {sizes.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
        <span>
          {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of{" "}
          {total}
        </span>
        {total > pageSize && (
          <div className="register-page-controls">
            <button
              className="icon-button"
              title={`Previous ${label}`}
              aria-label={`Previous ${label}`}
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              ‹
            </button>
            <span>
              Page {page} of {Math.ceil(total / pageSize)}
            </span>
            <button
              className="icon-button"
              title={`Next ${label}`}
              aria-label={`Next ${label}`}
              disabled={page >= Math.ceil(total / pageSize)}
              onClick={() => setPage(page + 1)}
            >
              ›
            </button>
          </div>
        )}
      </div>
    );
  return (
    <div className="labor-wages-sections">
      <ExportHeader reportTitle="Labor and Wages Report" projectName={project?.name} projectLocation={project?.location} />
      <PageTitle
        eyebrow="FIELD OPERATIONS"
        title="Labor and Wages"
        subtitle="Subcontract labor, individual worker earnings, and wage payments"
        action={
          <div className="overview-actions">
            {canExport && (
              <button
                className="button-secondary export-report-action"
                onClick={exportReport}
                disabled={
                  ledger.isLoading ||
                  ledger.isError ||
                  contractsQuery.isLoading ||
                  contractsQuery.isError
                }
              >
                <BriefcaseBusiness size={14} />
                Export report
              </button>
            )}
            {canAction("new_labor_contract") && (
              <button
                className="button-primary labor-contract-action"
                onClick={() => setDialog("contract")}
              >
                <FileText size={15} />
                New labor contract
              </button>
            )}
            {canAction("add_worker") && (
              <button
                className="button-primary labor-register-action"
                onClick={() => setDialog("worker")}
              >
                <Users size={15} />
                Add worker
              </button>
            )}
            {canAction("log_weekly_work") && (
              <button
                className="button-primary labor-work-action"
                onClick={() => setDialog("work")}
                disabled={!hasActiveWorkers}
              >
                <Plus size={15} />
                Log weekly work
              </button>
            )}
            {canAction("pay_weekly_work") && (
              <button
                className="button-primary labor-payment-action"
                onClick={() => setDialog("payment")}
                disabled={
                  !workers.some(
                    (worker) => worker.active && Number(worker.payable) > 0,
                  )
                }
              >
                <Banknote size={15} />
                Pay weekly labor
              </button>
            )}
          </div>
        }
      />
      <div className="kpi-grid five">
        <Kpi
          label="Hours logged"
          value={String(ledger.data?.summary.total_work_entries ?? 0)}
          note={workUnitsNote}
          icon={<BriefcaseBusiness size={17} />}
          loading={ledger.isLoading}
        />
        <Kpi
          label="Total labor cost"
          value={currency(contractCertified + workerEarned, laborCurrency)}
          note={`Contract certified ${currency(contractCertified, laborCurrency)} · individual work ${currency(workerEarned, laborCurrency)}`}
          icon={<BriefcaseBusiness size={17} />}
          loading={contractsQuery.isLoading || ledger.isLoading}
        />
        <Kpi
          label="Total labor payments"
          value={currency(contractPaid + workerPaid, laborCurrency)}
          note={`Contract paid ${currency(contractPaid, laborCurrency)} · individual paid ${currency(workerPaid, laborCurrency)}`}
          icon={<Banknote size={17} />}
          loading={contractsQuery.isLoading || ledger.isLoading}
        />
        <Kpi
          label="Contract labor"
          value={currency(contractAuthorized, laborCurrency)}
          note={`Authorized · certified ${currency(contractCertified, laborCurrency)} · paid ${currency(contractPaid, laborCurrency)} · due ${currency(contractPayable, laborCurrency)}`}
          icon={<FileText size={17} />}
          loading={contractsQuery.isLoading}
        />
        <Kpi
          label="Direct worker labor"
          value={currency(workerEarned, laborCurrency)}
          note={`Work accrued · paid ${currency(workerPaid, laborCurrency)} · due ${currency(workerPayable, laborCurrency)}`}
          icon={<Users size={17} />}
          loading={ledger.isLoading}
        />
      </div>
      <QueryError error={ledger.error} onRetry={() => void ledger.refetch()} />
      <QueryError
        error={contractsQuery.error}
        onRetry={() => void contractsQuery.refetch()}
      />
      <QueryError
        error={contractDocuments.error}
        onRetry={() => void contractDocuments.refetch()}
      />
      <div className="labor-workstream-group contract-workstream-group">
        <button
          className="labor-workstream-heading"
          type="button"
          aria-expanded={contractsExpanded}
          onClick={() => setContractsExpanded((expanded) => !expanded)}
        >
          <FileText size={18} />
          <span className="labor-workstream-copy">
            <strong>Labor contracts</strong>
            <small>
              Subcontract agreements, progress claims, plan changes, approvals,
              and contract documents
            </small>
          </span>
          <ChevronDown
            className={contractsExpanded ? "" : "collapsed"}
            size={18}
          />
        </button>
        {contractsExpanded && (
          <div className="labor-workstream-content">
            <section className="panel table-panel labor-contract-panel">
              <PanelHeading
                title="Subcontract agreements"
                meta="Unit-rate or lump-sum agreements with authorized values and payment totals"
              />
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Contract / subcontractor</th>
                      <th>Pricing basis</th>
                      <th>Plan baseline</th>
                      <th className="numeric">Authorized value</th>
                      <th className="numeric">Certified</th>
                      <th className="numeric">Paid</th>
                      <th className="numeric">Payable</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contractsQuery.isLoading ? (
                      <tr>
                        <td colSpan={8}>
                          <div className="loading-line" />
                        </td>
                      </tr>
                    ) : contracts.length ? (
                      pagedContracts.map((contract) => {
                        const latestApprovedAddendum = contract.addenda.find(
                          (addendum) => addendum.status === "Approved",
                        );
                        return (
                          <tr key={contract.id}>
                            <td>
                              <strong className="strong-cell">
                                {contract.contract_number}
                              </strong>
                              <small className="labor-contract-subtitle">
                                {contract.subcontractor_name} · {contract.scope}
                              </small>
                            </td>
                            <td>
                              {contract.pricing_type === "unit_rate"
                                ? `${currency(contract.unit_rate || "0", contract.currency)} / ${contract.unit || "unit"}`
                                : "Lump sum"}
                            </td>
                            <td>
                              {contract.baseline_document || "Not linked"}
                            </td>
                            <td className="numeric">
                              <strong>
                                {currency(
                                  contract.contract_value,
                                  contract.currency,
                                )}
                              </strong>
                              {latestApprovedAddendum && (
                                <small className="labor-contract-subtitle">
                                  Updated from{" "}
                                  {currency(
                                    latestApprovedAddendum.previous_value,
                                    contract.currency,
                                  )}{" "}
                                  by approved addendum
                                </small>
                              )}
                            </td>
                            <td className="numeric">
                              {currency(contract.certified, contract.currency)}
                            </td>
                            <td className="numeric">
                              {currency(contract.paid, contract.currency)}
                            </td>
                            <td className="numeric labor-payable-cell">
                              {currency(contract.payable, contract.currency)}
                            </td>
                            <td>
                              <div className="labor-row-actions">
                                {canAction("log_weekly_work") && (
                                  <span
                                    className="row-action-tooltip"
                                    data-tooltip="Submit progress claim"
                                  >
                                    <button
                                      type="button"
                                      className="icon-button labor-contract-row-action labor-submit-claim-action"
                                      aria-label="Submit progress claim"
                                      title="Submit progress claim"
                                      onClick={() => {
                                        setSelectedContractId(contract.id);
                                        setDialog("claim");
                                      }}
                                      disabled={contract.status !== "Active"}
                                    >
                                      <ClipboardCheck size={16} />
                                    </button>
                                  </span>
                                )}
                                {canAction("new_labor_contract") && (
                                  <span
                                    className="row-action-tooltip"
                                    data-tooltip="Submit contract change"
                                  >
                                    <button
                                      type="button"
                                      className="icon-button labor-contract-row-action labor-submit-addendum-action"
                                      aria-label="Submit contract change"
                                      title="Submit contract change"
                                      onClick={() => {
                                        setSelectedContractId(contract.id);
                                        setDialog("addendum");
                                      }}
                                      disabled={contract.status !== "Active"}
                                    >
                                      <FilePenLine size={16} />
                                    </button>
                                  </span>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan={8}>
                          <EmptyState
                            title="No subcontract agreements"
                            note="Create a labor contract to start tracking subcontract work."
                          />
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {renderPagination(
                contracts.length,
                contractPage,
                contractPageSize,
                [5, 10, 20],
                setContractPage,
                setContractPageSize,
                "subcontract agreements",
              )}
              {contractClaims.length > 0 && (
                <div className="table-scroll labor-claims-table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Claim</th>
                        <th>Contract / subcontractor</th>
                        <th>Work period</th>
                        <th>Work certified for</th>
                        <th>Status</th>
                        <th className="numeric">Amount</th>
                        <th className="numeric">Paid</th>
                        <th className="numeric">Due</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {contractClaims.map(({ contract, claim }) => (
                        <tr key={claim.id}>
                          <td className="strong-cell">{claim.claim_number}</td>
                          <td>
                            {contract.contract_number} ·{" "}
                            {contract.subcontractor_name}
                          </td>
                          <td>
                            {dateLabel(claim.period_start)} –{" "}
                            {dateLabel(claim.period_end)}
                          </td>
                          <td>{claim.work_description}</td>
                          <td>
                            <span
                              className={`status-pill ${claim.status === "Certified" ? "complete" : claim.status === "Rejected" ? "hold" : "planning"}`}
                            >
                              {claim.status}
                            </span>
                          </td>
                          <td className="numeric">
                            {currency(claim.amount, contract.currency)}
                          </td>
                          <td className="numeric">
                            {currency(claim.paid, contract.currency)}
                          </td>
                          <td className="numeric labor-payable-cell">
                            {currency(claim.payable, contract.currency)}
                          </td>
                          <td>
                            <div className="labor-row-actions">
                              {canAction("pay_weekly_work") && claim.status === "Certified" &&
                                Number(claim.payable) > 0 && (
                                  <span
                                    className="row-action-tooltip"
                                    data-tooltip="Record payment"
                                  >
                                    <button
                                      type="button"
                                      className="icon-button labor-contract-row-action labor-record-payment-action"
                                      aria-label="Record payment"
                                      title="Record payment"
                                      onClick={() => {
                                        setSelectedClaimId(claim.id);
                                        setDialog("claim-payment");
                                      }}
                                    >
                                      <Banknote size={16} />
                                    </button>
                                  </span>
                                )}
                              <span
                                className="row-action-tooltip"
                                data-tooltip="History"
                              >
                                <button
                                  type="button"
                                  className="icon-button labor-contract-row-action labor-payment-history-action"
                                  aria-label="History"
                                  title="History"
                                  onClick={() => setHistoryClaimId(claim.id)}
                                >
                                  <History size={16} />
                                </button>
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
            <section className="panel table-panel labor-approvals-panel">
              <PanelHeading
                title="Items waiting for review"
                meta="Pending contract changes and weekly claim certifications"
              />
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Contract / reference</th>
                      <th>Details</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contractsQuery.isLoading ? (
                      <tr>
                        <td colSpan={5}>
                          <div className="loading-line" />
                        </td>
                      </tr>
                    ) : reviewItems.length ? (
                      pagedReviewItems.map((item) => (
                        <tr key={`${item.decisionType}-${item.id}`}>
                          <td>{item.type}</td>
                          <td className="strong-cell">{item.reference}</td>
                          <td>{item.details}</td>
                          <td>
                            <span className="status-pill planning">
                              Pending
                            </span>
                          </td>
                          <td>
                            <div className="labor-row-actions">
                              {canAction(item.decisionType === "addendum" ? "new_labor_contract" : "log_weekly_work") && <button
                                className="button-secondary labor-approve-action"
                                onClick={() =>
                                  void decide(
                                    item.decisionType,
                                    item.id,
                                    "approve",
                                  )
                                }
                              >
                                Approve
                              </button>}
                              {canAction(item.decisionType === "addendum" ? "new_labor_contract" : "log_weekly_work") && <button
                                className="button-secondary labor-reject-action"
                                onClick={() =>
                                  void decide(
                                    item.decisionType,
                                    item.id,
                                    "reject",
                                  )
                                }
                              >
                                Reject
                              </button>}
                            </div>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5}>
                          <EmptyState
                            title="No items waiting for review"
                            note="Submitted changes and claims awaiting review will appear here."
                          />
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {renderPagination(
                reviewItems.length,
                reviewPage,
                reviewPageSize,
                [5, 10, 20],
                setReviewPage,
                setReviewPageSize,
                "review items",
              )}
            </section>
            <section className="panel table-panel labor-addenda-history-panel">
              <PanelHeading
                title="Contract change history"
                meta="Submitted contract changes, including rejected and approved revisions · newest first"
              />
              <div className="table-scroll labor-addenda-history-table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Submitted</th>
                      <th>Contract / subcontractor</th>
                      <th>Plan revision</th>
                      <th>Reason / scope change</th>
                      <th className="numeric">Previous value</th>
                      <th className="numeric">Revised value</th>
                      <th>Status / review</th>
                      <th>Supporting file</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contractsQuery.isLoading ? (
                      <tr>
                        <td colSpan={8}>
                          <div className="loading-line" />
                        </td>
                      </tr>
                    ) : addendumHistory.length ? (
                      pagedAddenda.map(({ contract, addendum }) => (
                        <tr key={addendum.id}>
                          <td>
                            <strong>
                              {new Date(addendum.submitted_at).toLocaleString(
                                "en-IN",
                              )}
                            </strong>
                            <div className="muted-cell">
                              by {addendum.submitted_by || "Unknown"}
                            </div>
                          </td>
                          <td>
                            <strong className="strong-cell">
                              {contract.contract_number}
                            </strong>
                            <div className="muted-cell">
                              {contract.subcontractor_name}
                            </div>
                          </td>
                          <td>{addendum.plan_filename}</td>
                          <td className="overview-comment">
                            {addendum.reason}
                          </td>
                          <td className="numeric">
                            {currency(
                              addendum.previous_value,
                              contract.currency,
                            )}
                          </td>
                          <td className="numeric">
                            {currency(
                              addendum.revised_value,
                              contract.currency,
                            )}
                          </td>
                          <td>
                            <span
                              className={`status-pill ${addendum.status === "Approved" ? "complete" : addendum.status === "Rejected" ? "hold" : "planning"}`}
                            >
                              {addendum.status}
                            </span>
                            {addendum.decided_at && (
                              <div className="muted-cell">
                                {new Date(addendum.decided_at).toLocaleString(
                                  "en-IN",
                                )}{" "}
                                · {addendum.decided_by || "Unknown"}
                              </div>
                            )}
                            {addendum.decision_comment && (
                              <div className="overview-comment">
                                {addendum.decision_comment}
                              </div>
                            )}
                          </td>
                          <td>
                            {addendum.document_url &&
                            addendum.document_filename &&
                            canDownload("download_history_files") ? (
                              <a
                                className="button-secondary"
                                href={addendum.document_url}
                                download
                                title={addendum.document_filename}
                              >
                                <Download size={14} />
                                {addendum.document_filename}
                              </a>
                            ) : (
                              "No attachment"
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={8}>
                          <EmptyState
                            title="No contract changes submitted"
                            note="Submitted addenda will remain listed here after they are reviewed."
                          />
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {renderPagination(
                addendumHistory.length,
                addendumPage,
                addendumPageSize,
                [5, 10, 20],
                setAddendumPage,
                setAddendumPageSize,
                "contract changes",
              )}
            </section>
            <section className="panel table-panel labor-documents-panel">
              <PanelHeading
                title="Contract files"
                meta="Supporting agreements and attachments · newest first"
              />
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Document</th>
                      <th>Contract</th>
                      <th>Subcontractor</th>
                      <th>Uploaded</th>
                      <th>Uploaded by</th>
                      <th>File</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contractDocuments.isLoading ? (
                      <tr>
                        <td colSpan={6}>
                          <div className="loading-line" />
                        </td>
                      </tr>
                    ) : contractDocumentsList.length ? (
                      pagedContractDocuments.map((file) => (
                        <tr key={file.id}>
                          <td>
                            <strong>{file.filename}</strong>
                            <div className="muted-cell">
                              {file.content_type} ·{" "}
                              {(file.byte_size / (1024 * 1024)).toFixed(2)} MB
                            </div>
                          </td>
                          <td className="strong-cell">
                            {file.contract_number}
                          </td>
                          <td>{file.subcontractor_name}</td>
                          <td>
                            {new Date(file.uploaded_at).toLocaleString("en-IN")}
                          </td>
                          <td>{file.uploaded_by}</td>
                          <td>
                            {canDownload("download_contract_files") && (
                              <a
                                className="button-secondary"
                                href={file.url}
                                download
                              >
                                <Download size={14} />
                                Download
                              </a>
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6}>
                          <EmptyState
                            title="No contract files"
                            note="Attach a signed agreement or supporting document when creating a labor contract."
                          />
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {renderPagination(
                contractDocumentsList.length,
                contractDocumentPage,
                contractDocumentPageSize,
                [5, 10, 20],
                setContractDocumentPage,
                setContractDocumentPageSize,
                "contract files",
              )}
            </section>
          </div>
        )}
      </div>
      <div className="labor-workstream-group worker-workstream-group">
        <button
          className="labor-workstream-heading"
          type="button"
          aria-expanded={workersExpanded}
          onClick={() => setWorkersExpanded((expanded) => !expanded)}
        >
          <Users size={18} />
          <span className="labor-workstream-copy">
            <strong>Individual workers</strong>
            <small>
              Direct weekly work records, worker balances, and wage payments
              without a labor contract
            </small>
          </span>
          <ChevronDown
            className={workersExpanded ? "" : "collapsed"}
            size={18}
          />
        </button>
        {workersExpanded && (
          <div className="labor-workstream-content">
            <section className="panel table-panel labor-worker-panel">
              <PanelHeading
                title="Worker payment balances"
                meta="Direct payments to individuals outside subcontract agreements"
                action={
                  <div className="search-wrap">
                    <Search size={16} />
                    <input
                      aria-label="Search workers"
                      placeholder="Search worker or trade"
                      value={search}
                      onChange={(event) => {
                        setSearch(event.target.value);
                        setWorkerPage(1);
                      }}
                    />
                  </div>
                }
              />
              {workerStatusError && (
                <div className="labor-worker-action-error" role="alert">
                  {workerStatusError}
                </div>
              )}
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Worker</th>
                      <th>Trade</th>
                      <th className="numeric">Work units</th>
                      <th className="numeric">Work accrued</th>
                      <th className="numeric">Paid</th>
                      <th className="numeric">Payable</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ledger.isLoading ? (
                      <tr>
                        <td colSpan={8}>
                          <div className="loading-line" />
                        </td>
                      </tr>
                    ) : matchingWorkers.length ? (
                      <>
                        {pagedWorkers.map((worker) => (
                          <tr key={worker.id}>
                            <td className="strong-cell">{worker.name}</td>
                            <td>{worker.trade}</td>
                            <td className="numeric">
                              {workerUnitSummary(worker.work_units)}
                            </td>
                            <td className="numeric">
                              {currency(worker.earned, ledger.data?.currency)}
                            </td>
                            <td className="numeric">
                              {currency(worker.paid, ledger.data?.currency)}
                            </td>
                            <td className="numeric labor-payable-cell">
                              {currency(worker.payable, ledger.data?.currency)}
                            </td>
                            <td>
                              <span
                                className={`status-pill ${worker.active ? "active" : "hold"}`}
                              >
                                {worker.active ? "Active" : "Inactive"}
                              </span>
                            </td>
                            <td>
                              <div className="labor-row-actions">
                                {canAction("edit_worker") && (
                                  <span
                                    className="row-action-tooltip"
                                    data-tooltip="Edit worker"
                                  >
                                    <button
                                      type="button"
                                      className="icon-button labor-worker-edit-action"
                                      aria-label={`Edit ${worker.name}`}
                                      title="Edit worker"
                                      onClick={() => {
                                        setEditingWorkerId(worker.id);
                                        setDialog("worker-edit");
                                      }}
                                    >
                                      <Pencil size={15} />
                                    </button>
                                  </span>
                                )}
                                {canAction("deactivate_worker") && (
                                  <span
                                    className="row-action-tooltip"
                                    data-tooltip={
                                      worker.active
                                        ? "Deactivate worker"
                                        : "Activate worker"
                                    }
                                  >
                                    <button
                                      type="button"
                                      className={`icon-button ${worker.active ? "labor-worker-deactivate-action" : "labor-worker-activate-action"}`}
                                      aria-label={`${worker.active ? "Deactivate" : "Activate"} ${worker.name}`}
                                      title={
                                        worker.active
                                          ? "Deactivate worker"
                                          : "Activate worker"
                                      }
                                      onClick={() =>
                                        void toggleWorkerActive(
                                          worker.id,
                                          !worker.active,
                                        )
                                      }
                                    >
                                      {worker.active ? (
                                        <UserX size={15} />
                                      ) : (
                                        <Check size={15} />
                                      )}
                                    </button>
                                  </span>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                        <tr className="labor-worker-total-row">
                          <td colSpan={2}>
                            Filtered totals · {matchingWorkerTotals.workEntries}{" "}
                            work entries
                          </td>
                          <td className="numeric">{matchingWorkerUnits}</td>
                          <td className="numeric">
                            {currency(
                              matchingWorkerTotals.earned,
                              ledger.data?.currency,
                            )}
                          </td>
                          <td className="numeric">
                            {currency(
                              matchingWorkerTotals.paid,
                              ledger.data?.currency,
                            )}
                          </td>
                          <td className="numeric labor-payable-cell">
                            {currency(
                              matchingWorkerTotals.payable,
                              ledger.data?.currency,
                            )}
                          </td>
                          <td colSpan={2}>
                            {search ? "Matching workers" : "All workers"}
                          </td>
                        </tr>
                      </>
                    ) : (
                      <tr>
                        <td colSpan={8}>
                          <EmptyState
                            title={
                              search
                                ? "No matching workers"
                                : "No workers registered"
                            }
                            note={
                              search
                                ? "Try another name or trade."
                                : "Add a worker to begin this independent labor and wage ledger."
                            }
                          />
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {renderPagination(
                matchingWorkers.length,
                workerPage,
                workerPageSize,
                [10, 20, 50],
                setWorkerPage,
                setWorkerPageSize,
                "workers",
              )}
            </section>
            <div className="labor-ledger-grid">
              <section className="panel table-panel">
                <PanelHeading
                  title="Direct weekly work log"
                  meta="Individual work entries · newest work dates first"
                  action={
                    <div className="search-wrap">
                      <Search size={15} />
                      <input
                        aria-label="Search direct work by worker"
                        placeholder="Search worker"
                        value={workSearch}
                        onChange={(event) => {
                          setWorkSearch(event.target.value);
                          setWorkPage(1);
                        }}
                      />
                    </div>
                  }
                />
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Worker</th>
                        <th>Work / trade</th>
                        <th className="numeric">Unit</th>
                        <th className="numeric">Rate</th>
                        <th className="numeric">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ledger.isLoading ? (
                        <tr>
                          <td colSpan={6}>
                            <div className="loading-line" />
                          </td>
                        </tr>
                      ) : matchingWorkEntries.length ? (
                        pagedWorkEntries.map((entry) => (
                          <tr key={entry.id}>
                            <td>{dateLabel(entry.work_date)}</td>
                            <td className="strong-cell">{entry.worker_name}</td>
                            <td>{entry.description}</td>
                            <td className="numeric">
                              {entry.quantity} {entry.unit}
                            </td>
                            <td className="numeric">
                              {currency(entry.rate, ledger.data?.currency)}
                            </td>
                            <td className="numeric">
                              {currency(entry.amount, ledger.data?.currency)}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={6}>
                            <EmptyState
                              title={
                                workSearch
                                  ? "No matching work records"
                                  : "No direct work recorded"
                              }
                              note={
                                workSearch
                                  ? "Try another worker name."
                                  : "Log completed work here; it is independent of Attendance timecards and labor contracts."
                              }
                            />
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="labor-filter-total">
                  <span>
                    {workSearch
                      ? `Matching work total · ${matchingWorkEntries.length} records`
                      : `All direct work · ${matchingWorkEntries.length} records`}
                  </span>
                  <div className="labor-filter-total-breakdown">
                    <span>{workUnitsSummary || "0 units"}</span>
                    <strong>
                      {currency(
                        workAmountTotal,
                        ledger.data?.currency || laborCurrency,
                      )}
                    </strong>
                  </div>
                </div>
                {renderPagination(
                  matchingWorkEntries.length,
                  workPage,
                  workPageSize,
                  [10, 20, 50],
                  setWorkPage,
                  setWorkPageSize,
                  "work records",
                )}
              </section>
              <section className="panel table-panel">
                <PanelHeading
                  title="Direct worker wage payments"
                  meta="Payments to individuals against recorded weekly work · newest first"
                  action={
                    <div className="labor-ledger-filters">
                      <div className="search-wrap">
                        <Search size={15} />
                        <input
                          aria-label="Search wage payments by worker"
                          placeholder="Search worker"
                          value={wageSearch}
                          onChange={(event) => {
                            setWageSearch(event.target.value);
                            setWagePage(1);
                          }}
                        />
                      </div>
                      <label className="labor-mode-filter">
                        <span>Mode</span>
                        <select
                          aria-label="Filter wage payments by mode"
                          value={wageModeFilter}
                          onChange={(event) => {
                            setWageModeFilter(event.target.value);
                            setWagePage(1);
                          }}
                        >
                          <option value="">All</option>
                          {wagePaymentModes.map((mode) => (
                            <option key={mode} value={mode}>
                              {mode}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                  }
                />
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Worker</th>
                        <th className="numeric">Amount</th>
                        <th>Method</th>
                        <th>Reference</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ledger.isLoading ? (
                        <tr>
                          <td colSpan={5}>
                            <div className="loading-line" />
                          </td>
                        </tr>
                      ) : matchingWagePayments.length ? (
                        pagedWagePayments.map((payment) => (
                          <tr key={payment.id}>
                            <td>{dateLabel(payment.payment_date)}</td>
                            <td className="strong-cell">
                              {payment.worker_name}
                            </td>
                            <td className="numeric">
                              {currency(payment.amount, ledger.data?.currency)}
                            </td>
                            <td>{payment.payment_mode}</td>
                            <td>{payment.reference || "—"}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5}>
                            <EmptyState
                              title={
                                wageSearch || wageModeFilter
                                  ? "No matching payments"
                                  : "No direct worker payments"
                              }
                              note={
                                wageSearch || wageModeFilter
                                  ? "Adjust the worker search or payment mode filter."
                                  : "Recorded payments to individual workers will appear here."
                              }
                            />
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="labor-filter-total">
                  <span>
                    {wageSearch || wageModeFilter
                      ? `Matching payments · ${matchingWagePayments.length} records`
                      : `All direct worker payments · ${matchingWagePayments.length} records`}
                  </span>
                  <strong>
                    {currency(
                      wageAmountTotal,
                      ledger.data?.currency || laborCurrency,
                    )}
                  </strong>
                </div>
                {renderPagination(
                  matchingWagePayments.length,
                  wagePage,
                  wagePageSize,
                  [10, 20, 50],
                  setWagePage,
                  setWagePageSize,
                  "wage payments",
                )}
              </section>
            </div>
          </div>
        )}
      </div>
      {dialog && (
        <ModalFrame
          title={
            {
              worker: "Register weekly labor worker",
              "worker-edit": "Edit worker details",
              work: "Log weekly labor work",
              payment: "Pay weekly labor",
              contract: "Create labor contract",
              addendum: "Submit labor contract addendum",
              claim: "Submit weekly progress claim",
              "claim-payment": "Pay certified contract claim",
            }[dialog]
          }
          onClose={() => setDialog(null)}
        >
          {dialog === "contract" && (
            <LaborContractForm
              projectId={projectId}
              csrf={csrf}
              documents={contractsQuery.data?.plan_documents || []}
              onSaved={invalidate}
              onCancel={() => setDialog(null)}
            />
          )}
          {dialog === "addendum" && (
            <LaborAddendumForm
              projectId={projectId}
              csrf={csrf}
              contractId={selectedContractId}
              documents={contractsQuery.data?.plan_documents || []}
              onSaved={invalidate}
              onCancel={() => setDialog(null)}
            />
          )}
          {dialog === "claim" && (
            <LaborClaimForm
              projectId={projectId}
              csrf={csrf}
              contract={contractsQuery.data?.contracts.find(
                (item) => item.id === selectedContractId,
              )!}
              onSaved={invalidate}
              onCancel={() => setDialog(null)}
            />
          )}
          {dialog === "worker" && (
            <WorkerForm
              projectId={projectId}
              csrf={csrf}
              onSaved={invalidate}
              onCancel={() => setDialog(null)}
            />
          )}
          {dialog === "worker-edit" && (
            <WorkerEditForm
              projectId={projectId}
              csrf={csrf}
              worker={workers.find((item) => item.id === editingWorkerId)!}
              onSaved={invalidate}
              onCancel={() => setDialog(null)}
            />
          )}
          {dialog === "work" && (
            <WorkForm
              projectId={projectId}
              csrf={csrf}
              workers={workers.filter((worker) => worker.active)}
              onSaved={invalidate}
              onCancel={() => setDialog(null)}
            />
          )}
          {dialog === "payment" && (
            <WagePaymentForm
              projectId={projectId}
              csrf={csrf}
              workers={workers.filter(
                (worker) => worker.active && Number(worker.payable) > 0,
              )}
              onSaved={invalidate}
              onCancel={() => setDialog(null)}
            />
          )}
          {dialog === "claim-payment" && (
            <LaborClaimPaymentForm
              projectId={projectId}
              csrf={csrf}
              claim={contractsQuery.data?.contracts
                .flatMap((item) => item.claims)
                .find((item) => item.id === selectedClaimId)!}
              currencyCode={contractsQuery.data?.currency || "INR"}
              onSaved={invalidate}
              onCancel={() => setDialog(null)}
            />
          )}
        </ModalFrame>
      )}
      {historyClaim && (
        <ModalFrame
          title={`${historyClaim.contract.contract_number} · ${historyClaim.claim.claim_number} payment history`}
          onClose={() => setHistoryClaimId(null)}
        >
          <div className="labor-claim-history">
            <div className="payment-summary full">
              <span>
                {historyClaim.contract.subcontractor_name} ·{" "}
                {historyClaim.claim.work_description}
              </span>
              <strong>
                {currency(
                  historyClaim.claim.paid,
                  historyClaim.contract.currency,
                )}{" "}
                paid of{" "}
                {currency(
                  historyClaim.claim.amount,
                  historyClaim.contract.currency,
                )}
              </strong>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Payment date</th>
                    <th className="numeric">Amount</th>
                    <th>Method</th>
                    <th>Reference</th>
                    <th>Comment</th>
                  </tr>
                </thead>
                <tbody>
                  {historyClaim.claim.payments.length ? (
                    historyClaim.claim.payments.map((payment) => (
                      <tr key={payment.id}>
                        <td>{dateLabel(payment.payment_date)}</td>
                        <td className="numeric">
                          {currency(
                            payment.amount,
                            historyClaim.contract.currency,
                          )}
                        </td>
                        <td>{payment.payment_mode}</td>
                        <td>{payment.reference || "—"}</td>
                        <td className="overview-comment">
                          {payment.comment || "—"}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5}>
                        <EmptyState
                          title="No payments recorded"
                          note="Payments made against this certified claim will appear here."
                        />
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </ModalFrame>
      )}
    </div>
  );
}

type ActiveWorker = {
  id: string;
  name: string;
  trade: string;
  payable: string;
};
type LaborWorkerRecord = LaborLedger["workers"][number];

type LaborPlanOption = {
  id: string;
  filename: string;
  category: string;
  uploaded_at: string;
  comment: string;
};

function LaborContractForm({
  projectId,
  csrf,
  documents,
  onSaved,
  onCancel,
}: {
  projectId: string;
  csrf: string;
  documents: LaborPlanOption[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    subcontractor_name: "",
    scope: "",
    pricing_type: "unit_rate" as "unit_rate" | "lump_sum",
    contract_value: "",
    unit: "m²",
    unit_rate: "",
    baseline_document_id: "",
  });
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentError, setDocumentError] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      api.createLaborContract(
        projectId,
        {
          ...form,
          unit: form.pricing_type === "unit_rate" ? form.unit : undefined,
          unit_rate:
            form.pricing_type === "unit_rate" ? form.unit_rate : undefined,
          baseline_document_id: form.baseline_document_id || undefined,
          document: documentFile,
        },
        csrf,
      ),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <label className="field full">
        Subcontractor / crew lead
        <input
          required
          minLength={2}
          maxLength={160}
          value={form.subcontractor_name}
          onChange={(event) =>
            setForm({ ...form, subcontractor_name: event.target.value })
          }
          autoFocus
        />
      </label>
      <label className="field full">
        Contract scope
        <input
          required
          minLength={2}
          maxLength={500}
          value={form.scope}
          onChange={(event) => setForm({ ...form, scope: event.target.value })}
          placeholder="e.g. Block masonry, first and second floor"
        />
      </label>
      <label className="field">
        Pricing basis
        <select
          value={form.pricing_type}
          onChange={(event) =>
            setForm({
              ...form,
              pricing_type: event.target.value as typeof form.pricing_type,
            })
          }
        >
          <option value="unit_rate">Unit rate</option>
          <option value="lump_sum">Fixed lump sum</option>
        </select>
      </label>
      <label className="field">
        {form.pricing_type === "unit_rate"
          ? "Estimated contract value (₹)"
          : "Contract amount (₹)"}
        <input
          required
          type="number"
          min="0.01"
          step="0.01"
          value={form.contract_value}
          onChange={(event) =>
            setForm({ ...form, contract_value: event.target.value })
          }
        />
      </label>
      {form.pricing_type === "unit_rate" && (
        <>
          <label className="field">
            Unit
            <input
              required
              maxLength={24}
              value={form.unit}
              onChange={(event) =>
                setForm({ ...form, unit: event.target.value })
              }
              placeholder="m², m³, piece"
            />
          </label>
          <label className="field">
            Rate per unit (₹)
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={form.unit_rate}
              onChange={(event) =>
                setForm({ ...form, unit_rate: event.target.value })
              }
            />
          </label>
        </>
      )}
      <label className="field full">
        Plan baseline (optional)
        <select
          value={form.baseline_document_id}
          onChange={(event) =>
            setForm({ ...form, baseline_document_id: event.target.value })
          }
        >
          <option value="">No uploaded plan linked</option>
          {documents.map((document) => (
            <option key={document.id} value={document.id}>
              {document.filename} ·{" "}
              {document.category === "initial_approval"
                ? "Initial plan"
                : "Updated plan"}
            </option>
          ))}
        </select>
      </label>
      <label className="field full">
        Contract document (optional)
        <input
          type="file"
          accept="application/pdf,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) {
              setDocumentFile(null);
              setDocumentError("");
              return;
            }
            const allowed = [
              "application/pdf",
              "image/png",
              "image/jpeg",
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ];
            if (!allowed.includes(file.type)) {
              setDocumentFile(null);
              setDocumentError("Choose a PDF, PNG, JPG, or DOCX document.");
              return;
            }
            if (!file.size || file.size > 10 * 1024 * 1024) {
              setDocumentFile(null);
              setDocumentError(
                "Choose a non-empty document no larger than 10 MB.",
              );
              return;
            }
            setDocumentFile(file);
            setDocumentError("");
          }}
        />
        {documentFile && (
          <small className="field-hint">
            {documentFile.name} ·{" "}
            {(documentFile.size / (1024 * 1024)).toFixed(2)} MB
          </small>
        )}
        {documentError && (
          <span className="form-error" role="alert">
            {documentError}
          </span>
        )}
      </label>
      <MutationError error={mutation.error} />
      <FormActions
        onCancel={onCancel}
        busy={mutation.isPending}
        disabled={
          !form.subcontractor_name.trim() ||
          !form.scope.trim() ||
          !form.contract_value ||
          !!documentError ||
          (form.pricing_type === "unit_rate" &&
            (!form.unit.trim() || !form.unit_rate))
        }
        submit="Create contract"
      />
    </form>
  );
}

function LaborAddendumForm({
  projectId,
  csrf,
  contractId,
  documents,
  onSaved,
  onCancel,
}: {
  projectId: string;
  csrf: string;
  contractId: string;
  documents: LaborPlanOption[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    plan_document_id: "",
    reason: "",
    revised_value: "",
  });
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentError, setDocumentError] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      api.createLaborAddendum(
        projectId,
        contractId,
        { ...form, document: documentFile },
        csrf,
      ),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <label className="field full">
        Updated plan revision
        <select
          required
          value={form.plan_document_id}
          onChange={(event) =>
            setForm({ ...form, plan_document_id: event.target.value })
          }
        >
          <option value="">Choose uploaded updated plan</option>
          {documents
            .filter((document) => document.category === "updated_plan")
            .map((document) => (
              <option key={document.id} value={document.id}>
                {document.filename} ·{" "}
                {new Date(document.uploaded_at).toLocaleDateString("en-IN")}
              </option>
            ))}
        </select>
        {!documents.some(
          (document) => document.category === "updated_plan",
        ) && (
          <small className="field-hint">
            Upload an updated project plan before submitting a labor contract
            addendum.
          </small>
        )}
      </label>
      <label className="field full">
        Reason and scope change
        <input
          required
          minLength={2}
          maxLength={500}
          value={form.reason}
          onChange={(event) => setForm({ ...form, reason: event.target.value })}
          placeholder="Describe the plan change and labor scope impact"
        />
      </label>
      <label className="field full">
        Revised authorized contract value (₹)
        <input
          required
          type="number"
          min="0.01"
          step="0.01"
          value={form.revised_value}
          onChange={(event) =>
            setForm({ ...form, revised_value: event.target.value })
          }
        />
      </label>
      <label className="field full">
        Supporting addendum document (optional)
        <input
          type="file"
          accept="application/pdf,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) {
              setDocumentFile(null);
              setDocumentError("");
              return;
            }
            const allowed = [
              "application/pdf",
              "image/png",
              "image/jpeg",
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ];
            if (!allowed.includes(file.type)) {
              setDocumentFile(null);
              setDocumentError("Choose a PDF, PNG, JPG, or DOCX document.");
              return;
            }
            if (!file.size || file.size > 10 * 1024 * 1024) {
              setDocumentFile(null);
              setDocumentError(
                "Choose a non-empty document no larger than 10 MB.",
              );
              return;
            }
            setDocumentFile(file);
            setDocumentError("");
          }}
        />
        {documentFile && (
          <small className="field-hint">
            {documentFile.name} ·{" "}
            {(documentFile.size / (1024 * 1024)).toFixed(2)} MB
          </small>
        )}
        {documentError && (
          <span className="form-error" role="alert">
            {documentError}
          </span>
        )}
      </label>
      <div className="form-note full">
        The existing contract value remains in force until this addendum is
        reviewed and approved.
      </div>
      <MutationError error={mutation.error} />
      <FormActions
        onCancel={onCancel}
        busy={mutation.isPending}
        disabled={
          !form.plan_document_id ||
          !form.reason.trim() ||
          !form.revised_value ||
          !!documentError
        }
        submit="Submit for approval"
      />
    </form>
  );
}

function LaborClaimForm({
  projectId,
  csrf,
  contract,
  onSaved,
  onCancel,
}: {
  projectId: string;
  csrf: string;
  contract: LaborContractRecord;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    period_start: todayISO,
    period_end: todayISO,
    work_description: "",
    quantity: "",
    amount: "",
  });
  const amount =
    contract.pricing_type === "unit_rate" && form.quantity
      ? (Number(form.quantity) * Number(contract.unit_rate)).toFixed(2)
      : form.amount;
  const alreadyCommitted = contract.claims.reduce(
    (total, claim) =>
      total +
      (claim.status === "Certified" || claim.status === "Pending certification"
        ? Number(claim.amount)
        : 0),
    0,
  );
  const remainingValue = Math.max(
    0,
    Number(contract.contract_value) - alreadyCommitted,
  );
  const claimAmountInvalid = !!amount && Number(amount) > remainingValue;
  const mutation = useMutation({
    mutationFn: () =>
      api.createLaborClaim(
        projectId,
        contract.id,
        { ...form, quantity: form.quantity || undefined, amount },
        csrf,
      ),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <div className="payment-summary full">
        <span>
          {contract.contract_number} · {contract.subcontractor_name}
        </span>
        <strong>
          Authorized value{" "}
          {currency(contract.contract_value, contract.currency)} · available for
          claims {currency(remainingValue, contract.currency)}
        </strong>
      </div>
      <label className="field">
        Period start
        <input
          required
          type="date"
          value={form.period_start}
          onChange={(event) =>
            setForm({ ...form, period_start: event.target.value })
          }
        />
      </label>
      <label className="field">
        Period end
        <input
          required
          type="date"
          min={form.period_start}
          value={form.period_end}
          onChange={(event) =>
            setForm({ ...form, period_end: event.target.value })
          }
        />
      </label>
      <label className="field full">
        Work completed this period
        <input
          required
          minLength={2}
          maxLength={500}
          value={form.work_description}
          onChange={(event) =>
            setForm({ ...form, work_description: event.target.value })
          }
          placeholder="e.g. 145 m² first-floor block masonry completed"
        />
      </label>
      {contract.pricing_type === "unit_rate" ? (
        <>
          <label className="field">
            Certified quantity ({contract.unit || "unit"})
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={form.quantity}
              aria-invalid={claimAmountInvalid}
              aria-describedby={
                claimAmountInvalid ? "labor-claim-limit-error" : undefined
              }
              onChange={(event) =>
                setForm({ ...form, quantity: event.target.value })
              }
            />
          </label>
          <label className="field">
            Contract rate
            <input
              readOnly
              value={`${currency(contract.unit_rate || "0", contract.currency)} per ${contract.unit || "unit"}`}
            />
          </label>
        </>
      ) : (
        <label className="field full">
          Claim amount (₹)
          <input
            required
            type="number"
            min="0.01"
            max={remainingValue}
            step="0.01"
            value={form.amount}
            aria-invalid={claimAmountInvalid}
            aria-describedby={
              claimAmountInvalid ? "labor-claim-limit-error" : undefined
            }
            onChange={(event) =>
              setForm({ ...form, amount: event.target.value })
            }
          />
        </label>
      )}
      {claimAmountInvalid && (
        <div
          id="labor-claim-limit-error"
          className="form-error full"
          role="alert"
        >
          Claim amount exceeds the remaining authorized value of{" "}
          {currency(remainingValue, contract.currency)}. Pending and certified
          claims count toward the contract limit.
        </div>
      )}
      <div className="payment-summary full">
        <span>Claim amount</span>
        <strong>{currency(amount || "0", contract.currency)}</strong>
      </div>
      <MutationError error={mutation.error} />
      <FormActions
        onCancel={onCancel}
        busy={mutation.isPending}
        disabled={
          !form.work_description.trim() ||
          !amount ||
          claimAmountInvalid ||
          (contract.pricing_type === "unit_rate" && !form.quantity)
        }
        submit="Submit weekly claim"
      />
    </form>
  );
}

function LaborClaimPaymentForm({
  projectId,
  csrf,
  claim,
  currencyCode,
  onSaved,
  onCancel,
}: {
  projectId: string;
  csrf: string;
  claim: { id: string; claim_number: string; payable: string };
  currencyCode: string;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    payment_date: todayISO,
    amount: claim.payable,
    payment_mode: "Bank transfer" as
      "Cash" | "Bank transfer" | "Gpay" | "Cheque" | "Other",
    reference: "",
    comment: "",
  });
  const invalid =
    !form.amount ||
    Number(form.amount) <= 0 ||
    Number(form.amount) > Number(claim.payable);
  const mutation = useMutation({
    mutationFn: () => api.payLaborClaim(projectId, claim.id, form, csrf),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        if (!invalid) mutation.mutate();
      }}
    >
      <div className="payment-summary full">
        <span>{claim.claim_number} · unpaid certified claim</span>
        <strong>{currency(claim.payable, currencyCode)}</strong>
      </div>
      <label className="field">
        Payment date
        <input
          required
          type="date"
          value={form.payment_date}
          onChange={(event) =>
            setForm({ ...form, payment_date: event.target.value })
          }
        />
      </label>
      <label className="field">
        Amount (₹)
        <input
          required
          type="number"
          min="0.01"
          max={claim.payable}
          step="0.01"
          value={form.amount}
          aria-invalid={invalid}
          onChange={(event) => setForm({ ...form, amount: event.target.value })}
        />
      </label>
      <label className="field full">
        Payment method
        <select
          value={form.payment_mode}
          onChange={(event) =>
            setForm({
              ...form,
              payment_mode: event.target.value as typeof form.payment_mode,
            })
          }
        >
          <option>Bank transfer</option>
          <option>Cheque</option>
          <option>Cash</option>
          <option>Gpay</option>
          <option>Other</option>
        </select>
      </label>
      <label className="field full">
        Reference (optional)
        <input
          maxLength={100}
          value={form.reference}
          onChange={(event) =>
            setForm({ ...form, reference: event.target.value })
          }
        />
      </label>
      <label className="field full">
        Comment (optional)
        <textarea
          maxLength={500}
          value={form.comment}
          onChange={(event) =>
            setForm({ ...form, comment: event.target.value })
          }
        />
      </label>
      <MutationError error={mutation.error} />
      <FormActions
        onCancel={onCancel}
        busy={mutation.isPending}
        disabled={invalid}
        submit="Record claim payment"
      />
    </form>
  );
}

function WorkerForm({
  projectId,
  csrf,
  onSaved,
  onCancel,
}: {
  projectId: string;
  csrf: string;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [trade, setTrade] = useState("General labor");
  const [phone, setPhone] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      api.createLaborWorker(
        projectId,
        { name, trade, phone: phone || undefined },
        csrf,
      ),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <label className="field full">
        Worker name
        <input
          required
          minLength={2}
          maxLength={160}
          value={name}
          onChange={(event) => setName(event.target.value)}
          autoFocus
        />
      </label>
      <label className="field">
        Trade / role
        <input
          required
          minLength={2}
          maxLength={100}
          value={trade}
          onChange={(event) => setTrade(event.target.value)}
          placeholder="Mason, carpenter, helper"
        />
      </label>
      <label className="field">
        Phone (optional)
        <input
          type="tel"
          maxLength={30}
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
        />
      </label>
      <MutationError error={mutation.error} />
      <FormActions
        onCancel={onCancel}
        busy={mutation.isPending}
        submit="Add worker"
      />
    </form>
  );
}

function WorkerEditForm({
  projectId,
  csrf,
  worker,
  onSaved,
  onCancel,
}: {
  projectId: string;
  csrf: string;
  worker: LaborWorkerRecord;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    name: worker.name,
    trade: worker.trade,
    phone: worker.phone || "",
  });
  const mutation = useMutation({
    mutationFn: () =>
      api.updateLaborWorker(
        projectId,
        worker.id,
        {
          ...form,
          phone: form.phone || undefined,
          expected_version: worker.version,
        },
        csrf,
      ),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <label className="field full">
        Worker name
        <input
          required
          minLength={2}
          maxLength={160}
          value={form.name}
          onChange={(event) => setForm({ ...form, name: event.target.value })}
          autoFocus
        />
      </label>
      <label className="field">
        Trade / role
        <input
          required
          minLength={2}
          maxLength={100}
          value={form.trade}
          onChange={(event) => setForm({ ...form, trade: event.target.value })}
        />
      </label>
      <label className="field">
        Phone (optional)
        <input
          type="tel"
          maxLength={30}
          value={form.phone}
          onChange={(event) => setForm({ ...form, phone: event.target.value })}
        />
      </label>
      <MutationError error={mutation.error} />
      <FormActions
        onCancel={onCancel}
        busy={mutation.isPending}
        disabled={!form.name.trim() || !form.trade.trim()}
        submit="Save changes"
      />
    </form>
  );
}

function WorkForm({
  projectId,
  csrf,
  workers,
  onSaved,
  onCancel,
}: {
  projectId: string;
  csrf: string;
  workers: ActiveWorker[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    worker_id: workers[0]?.id || "",
    work_date: todayISO,
    description: "",
    quantity: "1",
    unit: "day" as "day" | "hour" | "piece",
    rate: "",
  });
  const amount = Number(form.quantity) * Number(form.rate);
  const mutation = useMutation({
    mutationFn: () => api.createLaborWorkEntry(projectId, form, csrf),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <label className="field full">
        Worker
        <select
          required
          value={form.worker_id}
          onChange={(event) =>
            setForm({ ...form, worker_id: event.target.value })
          }
        >
          {workers.map((worker) => (
            <option key={worker.id} value={worker.id}>
              {worker.name} · {worker.trade}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        Work date
        <input
          required
          type="date"
          value={form.work_date}
          onChange={(event) =>
            setForm({ ...form, work_date: event.target.value })
          }
        />
      </label>
      <label className="field">
        Work / task
        <input
          required
          minLength={2}
          maxLength={240}
          value={form.description}
          onChange={(event) =>
            setForm({ ...form, description: event.target.value })
          }
          placeholder="e.g. First-floor block masonry"
        />
      </label>
      <label className="field">
        Quantity
        <input
          required
          type="number"
          min="0.01"
          step="0.01"
          value={form.quantity}
          onChange={(event) =>
            setForm({ ...form, quantity: event.target.value })
          }
        />
      </label>
      <label className="field">
        Unit
        <select
          value={form.unit}
          onChange={(event) =>
            setForm({ ...form, unit: event.target.value as typeof form.unit })
          }
        >
          <option value="day">Day</option>
          <option value="hour">Hour</option>
          <option value="piece">Piece</option>
        </select>
      </label>
      <label className="field">
        Rate per unit (₹)
        <input
          required
          type="number"
          min="0"
          step="0.01"
          value={form.rate}
          onChange={(event) => setForm({ ...form, rate: event.target.value })}
        />
      </label>
      <div className="payment-summary full">
        <span>Work amount</span>
        <strong>{currency(Number.isFinite(amount) ? amount : 0)}</strong>
      </div>
      <MutationError error={mutation.error} />
      <FormActions
        onCancel={onCancel}
        busy={mutation.isPending}
        disabled={
          !form.worker_id ||
          !form.description.trim() ||
          !form.rate ||
          !Number.isFinite(amount)
        }
        submit="Save work record"
      />
    </form>
  );
}

function WagePaymentForm({
  projectId,
  csrf,
  workers,
  onSaved,
  onCancel,
}: {
  projectId: string;
  csrf: string;
  workers: ActiveWorker[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    worker_id: workers[0]?.id || "",
    payment_date: todayISO,
    amount: "",
    payment_mode: "Cash" as
      "Cash" | "Bank transfer" | "Gpay" | "Cheque" | "Other",
    reference: "",
    comment: "",
  });
  const worker = workers.find((item) => item.id === form.worker_id);
  const isInvalid =
    !form.amount ||
    Number(form.amount) <= 0 ||
    Number(form.amount) > Number(worker?.payable || 0);
  const mutation = useMutation({
    mutationFn: () => api.createLaborWagePayment(projectId, form, csrf),
    onSuccess: onSaved,
  });
  return (
    <form
      className="form-grid"
      onSubmit={(event) => {
        event.preventDefault();
        if (!isInvalid) mutation.mutate();
      }}
    >
      <label className="field full">
        Worker
        <select
          required
          value={form.worker_id}
          onChange={(event) =>
            setForm({ ...form, worker_id: event.target.value, amount: "" })
          }
        >
          {workers.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name} · payable {currency(item.payable)}
            </option>
          ))}
        </select>
      </label>
      <div className="payment-summary full">
        <span>Unpaid recorded work</span>
        <strong>{currency(worker?.payable)}</strong>
      </div>
      <label className="field">
        Payment date
        <input
          required
          type="date"
          value={form.payment_date}
          onChange={(event) =>
            setForm({ ...form, payment_date: event.target.value })
          }
        />
      </label>
      <label className="field">
        Amount (₹)
        <input
          required
          type="number"
          min="0.01"
          max={worker?.payable || 0}
          step="0.01"
          value={form.amount}
          aria-invalid={!!form.amount && isInvalid}
          onChange={(event) => setForm({ ...form, amount: event.target.value })}
        />
      </label>
      <label className="field full">
        Payment method
        <select
          value={form.payment_mode}
          onChange={(event) =>
            setForm({
              ...form,
              payment_mode: event.target.value as typeof form.payment_mode,
            })
          }
        >
          <option>Cash</option>
          <option>Bank transfer</option>
          <option>Gpay</option>
          <option>Cheque</option>
          <option>Other</option>
        </select>
      </label>
      <label className="field full">
        Reference (optional)
        <input
          maxLength={100}
          value={form.reference}
          onChange={(event) =>
            setForm({ ...form, reference: event.target.value })
          }
          placeholder="Transaction or voucher reference"
        />
      </label>
      <label className="field full">
        Comment (optional)
        <textarea
          maxLength={500}
          value={form.comment}
          onChange={(event) =>
            setForm({ ...form, comment: event.target.value })
          }
        />
      </label>
      {form.amount && isInvalid && (
        <div className="form-error full" role="alert">
          Payment must be greater than zero and cannot exceed unpaid recorded
          work.
        </div>
      )}
      <MutationError error={mutation.error} />
      <FormActions
        onCancel={onCancel}
        busy={mutation.isPending}
        disabled={isInvalid}
        submit="Record wage payment"
      />
    </form>
  );
}
