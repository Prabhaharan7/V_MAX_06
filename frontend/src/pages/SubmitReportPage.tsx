import React, { useState, useEffect, useRef } from "react";
import {
  FileSpreadsheet,
  Upload,
  Sparkles,
  ShieldAlert,
  CheckCircle2,
  FileText,
  Layers,
  AlertCircle,
  Clock,
  X,
  RefreshCw,
  Download,
  Check,
  Globe,
  Tag,
  MapPin,
  Building2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  BarChart3,
  PieChart,
  FileDown,
  AlertTriangle,
  Sliders,
  CheckSquare,
  Eye,
  EyeOff,
  Database,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface SiteOption {
  id: number;
  name: string;
  region: string;
  operation_type: string;
}

interface TargetFieldDef {
  key: string;
  label: string;
  required: boolean;
  description: string;
}

interface BulkPreviewResponse {
  filename: string;
  fingerprint: string;
  total_preview_rows: number;
  detected_columns: string[];
  suggested_mappings: Record<string, string | null>;
  target_to_column: Record<string, string | null>;
  mapping_confidence: Record<string, "high" | "medium" | "saved_template" | "unmapped" | string>;
  all_required_matched: boolean;
  matched_template_name?: string | null;
  sample_rows: Array<Record<string, any>>;
  available_target_fields: TargetFieldDef[];
}

interface BulkRowError {
  row: number;
  reason: string;
  data: Record<string, any>;
}

interface BulkErrorGroup {
  reason: string;
  count: number;
  examples: Array<{ row: number; data: Record<string, any> }>;
}

interface BulkUploadSummary {
  total_rows: number;
  accepted_count: number;
  rejected_count: number;
  accepted_report_ids: number[];
  upload_batch_id?: string;
  upload_batch_label?: string;
  has_ground_truth?: boolean;
  ground_truth_count?: number;
  accuracy_report_url?: string;
  download_csv_url?: string;
  report_type_counts?: Record<string, number>;
  sif_label_counts?: Record<string, number>;
  ground_truth_sif_counts?: Record<string, number>;
  rejection_breakdown?: BulkErrorGroup[];
  errors: BulkRowError[];
}

interface SIFMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  specificity: number;
  total_evaluated: number;
  sif_count: number;
  non_sif_count: number;
}

interface ConfusionMatrix {
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  true_negatives: number;
  pending_evaluation: number;
}

interface LSRRuleAccuracy {
  rule: string;
  total_ground_truth: number;
  correct_predictions: number;
  accuracy: number;
}

interface SplitEvaluation {
  split: string;
  sample_count: number;
  sif_metrics: SIFMetrics;
  confusion_matrix: ConfusionMatrix;
  lsr_overall_accuracy: number;
}

interface AccuracyReport {
  batch_id?: string;
  batch_label?: string;
  total_reports: number;
  labeled_reports_count: number;
  unlabeled_reports_count: number;
  overall_sif_accuracy: number;
  sif_metrics: SIFMetrics;
  confusion_matrix: ConfusionMatrix;
  lsr_rule_accuracies: LSRRuleAccuracy[];
  lsr_macro_accuracy: number;
  splits_breakdown: Record<string, SplitEvaluation>;
  evaluated_at: string;
}

interface ReportDetail {
  id: number;
  report_type: string;
  activity: string;
  raw_text: string;
  submitted_at: string;
  status: string;
  sif_label?: "sif_potential" | "non_sif" | null;
  sif_confidence?: number | null;
  primary_lsr?: string | null;
  lsr_tags?: Array<{ lsr_rule: string; confidence: number }>;
  barrier_failures?: Array<{ barrier_type: string; severity: string; evidence_phrase?: string }>;
}

interface ToastMessage {
  id: string;
  type: "success" | "processing" | "error";
  title: string;
  message: string;
  reportId?: number;
}

export const SubmitReportPage: React.FC = () => {
  const { token } = useAuth();

  // Navigation tab: single submission or bulk upload
  const [activeTab, setActiveTab] = useState<"single" | "bulk">("single");

  // Dynamic Site list
  const [sites, setSites] = useState<SiteOption[]>([
    { id: 1, name: "Rig 14 (Drilling, Moran)", region: "Upper Assam", operation_type: "Drilling" },
    { id: 2, name: "Rig 08 (Workover, Digboi)", region: "Upper Assam", operation_type: "Workover" },
    { id: 3, name: "Central Tank Farm (Naharkatia)", region: "Upper Assam", operation_type: "Production" },
    { id: 4, name: "Gas Compressor Station (Duliajan)", region: "Upper Assam", operation_type: "Gas Processing" },
    { id: 5, name: "Exploration Well Pad 3 (Jaisalmer)", region: "Rajasthan", operation_type: "Drilling" },
    { id: 6, name: "Crude Pipeline Pump Station (Barmer)", region: "Rajasthan", operation_type: "Pipeline" },
    { id: 7, name: "KG Basin Offshore Supply Base (Kakinada)", region: "KG Basin", operation_type: "Offshore Logistics" },
    { id: 8, name: "Well Servicing Unit 2 (Dirok)", region: "Upper Assam", operation_type: "Well Services" },
  ]);

  // Single Report Form State
  const [reportType, setReportType] = useState<string>("near_miss");
  const [activity, setActivity] = useState<string>("Workover & Casing Operations");
  const [siteId, setSiteId] = useState<number>(1);
  const [language, setLanguage] = useState<string>("en");
  const [rawText, setRawText] = useState<string>("");
  const [isSubmittingSingle, setIsSubmittingSingle] = useState(false);

  // Background pipeline poller for latest submitted report
  const [activeReportId, setActiveReportId] = useState<number | null>(null);
  const [activeReportData, setActiveReportData] = useState<ReportDetail | null>(null);
  const [isClassifying, setIsClassifying] = useState(false);

  // Bulk Upload State
  const [file, setFile] = useState<File | null>(null);
  const [batchLabel, setBatchLabel] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);
  const [isUploadingBulk, setIsUploadingBulk] = useState(false);
  const [bulkSummary, setBulkSummary] = useState<BulkUploadSummary | null>(null);
  const [accuracyReport, setAccuracyReport] = useState<AccuracyReport | null>(null);
  const [isLoadingAccuracy, setIsLoadingAccuracy] = useState(false);
  const [showFullAccuracy, setShowFullAccuracy] = useState(false);
  const [expandedReasons, setExpandedReasons] = useState<Record<number, boolean>>({});
  const [isDownloadingDataset, setIsDownloadingDataset] = useState(false);

  // Spreadsheet Schema Preview & Column Mapping State
  const [previewData, setPreviewData] = useState<BulkPreviewResponse | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState<boolean>(false);
  const [userMapping, setUserMapping] = useState<Record<string, string>>({});
  const [isMappingConfirmed, setIsMappingConfirmed] = useState<boolean>(false);
  const [showSampleRows, setShowSampleRows] = useState<boolean>(false);
  const [saveTemplate, setSaveTemplate] = useState<boolean>(true);
  const [templateCustomName, setTemplateCustomName] = useState<string>("");

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const toggleReasonExpand = (index: number) => {
    setExpandedReasons((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const fetchAccuracyReport = async (batchId: string) => {
    setIsLoadingAccuracy(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`/api/datasets/${batchId}/accuracy-report`, { headers });
      if (res.ok) {
        const data: AccuracyReport = await res.json();
        setAccuracyReport(data);
      } else {
        addToast("error", "Benchmark Load Failed", "Could not fetch accuracy report for this batch.");
      }
    } catch (err) {
      console.error("Error fetching accuracy report:", err);
      addToast("error", "Network Error", "Failed to load accuracy report.");
    } finally {
      setIsLoadingAccuracy(false);
    }
  };

  // Fetch live sites list if available
  useEffect(() => {
    const fetchSites = async () => {
      try {
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch("/api/patterns/ranked-sites", { headers });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            setSites(
              data.map((s: any) => ({
                id: s.site_id,
                name: s.site_name,
                region: s.region,
                operation_type: s.operation_type,
              }))
            );
          }
        }
      } catch (e) {
        // Fall back to default oilfield sites
      }
    };
    fetchSites();
  }, [token]);

  // Toast Helper
  const addToast = (type: ToastMessage["type"], title: string, message: string, reportId?: number) => {
    const newToast: ToastMessage = {
      id: Math.random().toString(36).substring(2, 9),
      type,
      title,
      message,
      reportId,
    };
    setToasts((prev) => [...prev, newToast]);

    if (type !== "processing") {
      setTimeout(() => {
        removeToast(newToast.id);
      }, 7000);
    }
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Poll background classification result for single report
  useEffect(() => {
    if (!activeReportId) return;

    let attempts = 0;
    const maxAttempts = 15;
    setIsClassifying(true);

    const interval = setInterval(async () => {
      attempts++;
      try {
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`/api/reports/${activeReportId}`, { headers });
        if (res.ok) {
          const data: ReportDetail = await res.json();
          setActiveReportData(data);

          // If classification has populated SIF label or LSR tags, stop polling
          if (data.sif_label || (data.lsr_tags && data.lsr_tags.length > 0) || attempts >= maxAttempts) {
            setIsClassifying(false);
            clearInterval(interval);

            // Update toast
            setToasts((prev) => prev.filter((t) => t.type !== "processing"));
            addToast(
              "success",
              `NLP Pipeline Completed for Report #${activeReportId}`,
              `Classified as ${data.sif_label === "sif_potential" ? "⚠️ SIF-Potential" : "✅ Non-SIF"} (${Math.round(
                (data.sif_confidence || 0) * 100
              )}% confidence)`,
              activeReportId
            );
          }
        }
      } catch (e) {
        console.warn("Polling report status error:", e);
      }

      if (attempts >= maxAttempts) {
        setIsClassifying(false);
        clearInterval(interval);
      }
    }, 1200);

    return () => clearInterval(interval);
  }, [activeReportId, token]);

  // Handle Single Report Submission
  const handleSingleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawText.trim()) return;

    setIsSubmittingSingle(true);
    setActiveReportData(null);

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/reports", {
        method: "POST",
        headers,
        body: JSON.stringify({
          report_type: reportType,
          activity,
          site_id: siteId,
          language,
          raw_text: rawText,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        addToast("error", "Submission Failed", errData.detail || "Server rejected report submission");
        setIsSubmittingSingle(false);
        return;
      }

      const createdReport: ReportDetail = await res.json();
      setActiveReportId(createdReport.id);
      setActiveReportData(createdReport);

      // Show immediate processing toast
      addToast(
        "processing",
        `Report #${createdReport.id} Created`,
        "Processing AI NLP classification in the background...",
        createdReport.id
      );

      // Reset text field
      setRawText("");
    } catch (err) {
      console.error("Error submitting report:", err);
      addToast("error", "Network Error", "Unable to communicate with SIF Sentinel backend");
    } finally {
      setIsSubmittingSingle(false);
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      validateAndSetFile(droppedFile);
    }
  };

  const validateAndSetFile = async (f: File) => {
    const ext = f.name.substring(f.name.lastIndexOf(".")).toLowerCase();
    if (ext !== ".csv" && ext !== ".xlsx" && ext !== ".xls") {
      addToast("error", "Invalid File Format", "Please provide a valid .csv, .xlsx, or .xls file.");
      return;
    }
    setFile(f);
    setBulkSummary(null);
    setAccuracyReport(null);
    setPreviewData(null);
    setIsMappingConfirmed(false);
    setUserMapping({});

    // Trigger preview endpoint to inspect schema & auto-suggest mappings
    setIsPreviewLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", f);
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/reports/bulk-upload/preview", {
        method: "POST",
        headers,
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        addToast("error", "Preview Failed", errData.detail || "Unable to parse headers from uploaded file.");
        setIsPreviewLoading(false);
        return;
      }

      const data: BulkPreviewResponse = await res.json();
      setPreviewData(data);

      // Initialize user mapping state from suggestions
      const initialMap: Record<string, string> = {};
      for (const col of data.detected_columns) {
        initialMap[col] = data.suggested_mappings[col] || "";
      }
      setUserMapping(initialMap);

      if (data.matched_template_name) {
        setTemplateCustomName(data.matched_template_name);
      } else {
        const baseName = f.name.replace(/\.[^/.]+$/, "").replace(/[_\-\s]+/g, " ");
        setTemplateCustomName(`${baseName} Schema`);
      }

      // Check if all 4 required fields are matched with high confidence or saved template
      const reqKeys = ["report_type", "raw_text", "site_id", "activity"];
      const mappedTargets = Object.values(initialMap);
      const hasAllReq = reqKeys.every((k) => mappedTargets.includes(k));
      const hasOnlyHighOrTemplate = reqKeys.every((k) => {
        const col = Object.keys(initialMap).find((c) => initialMap[c] === k);
        if (!col) return false;
        const conf = data.mapping_confidence[col];
        return conf === "high" || conf === "saved_template";
      });

      if (data.all_required_matched && hasAllReq && (data.matched_template_name || hasOnlyHighOrTemplate)) {
        setIsMappingConfirmed(true);
        addToast(
          "success",
          data.matched_template_name ? "Saved Template Applied" : "Auto-Mapped Schema",
          data.matched_template_name
            ? `Applied template "${data.matched_template_name}". Column mappings verified.`
            : `All ${data.detected_columns.length} columns recognized with high confidence. Pre-confirmed mapping.`
        );
      } else {
        setIsMappingConfirmed(false);
        addToast(
          "processing",
          "Schema Preview Ready",
          `Detected ${data.detected_columns.length} columns. Please review and confirm the column mappings.`
        );
      }
    } catch (err) {
      console.error("Error previewing file schema:", err);
      addToast("error", "Preview Error", "Could not analyze file schema.");
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleMappingChange = (sourceCol: string, targetVal: string) => {
    setUserMapping((prev) => ({
      ...prev,
      [sourceCol]: targetVal,
    }));
  };

  // Helper check for required fields
  const requiredFieldKeys = ["raw_text", "report_type", "site_id", "activity"];
  const mappedTargetValues = Object.values(userMapping).filter(Boolean);
  const isAllRequiredMapped = requiredFieldKeys.every((k) => mappedTargetValues.includes(k));
  const missingRequiredFields = requiredFieldKeys.filter((k) => !mappedTargetValues.includes(k));

  // Bulk Upload Handler
  const handleBulkUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !isAllRequiredMapped || !isMappingConfirmed) return;

    setIsUploadingBulk(true);
    setBulkSummary(null);
    setAccuracyReport(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (batchLabel.trim()) {
        formData.append("batch_label", batchLabel.trim());
      }
      formData.append("custom_mapping", JSON.stringify(userMapping));
      formData.append("save_template", saveTemplate ? "true" : "false");
      if (templateCustomName.trim()) {
        formData.append("template_name", templateCustomName.trim());
      }

      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/reports/bulk-upload", {
        method: "POST",
        headers,
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        addToast("error", "Upload Failed", errData.detail || "Bulk upload failed.");
        setIsUploadingBulk(false);
        return;
      }

      const summary: BulkUploadSummary = await res.json();
      setBulkSummary(summary);

      if (summary.has_ground_truth && summary.upload_batch_id) {
        addToast(
          "success",
          "Labeled Dataset Ingested",
          `Detected ${summary.ground_truth_count} ground-truth annotations. Model accuracy evaluation benchmark is active.`
        );
        fetchAccuracyReport(summary.upload_batch_id);
      } else {
        addToast(
          "success",
          "Batch File Processed",
          `Successfully queued ${summary.accepted_count} reports for asynchronous AI classification (${summary.rejected_count} rejected).`
        );
      }
    } catch (err) {
      console.error("Error uploading file:", err);
      addToast("error", "Network Error", "Failed to upload spreadsheet batch.");
    } finally {
      setIsUploadingBulk(false);
    }
  };

  // Sample CSV generator for download
  const downloadSampleCsv = () => {
    const csvContent =
      "report_type,activity,site_id,submitted_at,raw_text\n" +
      "near_miss,Workover Rig Operations,1,2026-09-27,Winch cable showed severe strand fraying while lifting 8-ton drill collar over rotary table. Crew evacuated line of fire.\n" +
      "UA,High Pressure Pipe Fitting,3,2026-09-26,Technician disconnected high pressure hydraulic flange without verifying lock out tag out or bleeding residual line pressure.\n" +
      "UC,Electrical Maintenance,4,2026-09-25,Ex-proof junction box cover missing four bolts in Class 1 Div 1 zone near compressor gas manifold.\n" +
      "incident,Tank Cleaning Operations,3,2026-09-24,Entry made into crude storage tank without continuous atmospheric oxygen and toxic gas monitoring.\n" +
      "UA,General Rig Housekeeping,2,2026-09-27,Empty paint cans left on rig floor gangway creating tripping hazard for floorhands.";

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "oil_india_safety_batch_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Download Processed Enriched Dataset CSV
  const handleDownloadProcessedDataset = async () => {
    if (!bulkSummary?.upload_batch_id) return;
    setIsDownloadingDataset(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`/api/datasets/${bulkSummary.upload_batch_id}/export-csv`, { headers });
      if (!res.ok) {
        addToast("error", "Export Failed", "Could not generate enriched dataset export.");
        return;
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sif_sentinel_processed_${bulkSummary.upload_batch_id}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      addToast(
        "success",
        "Enriched Dataset Exported",
        "Downloaded CSV with original metadata, model predictions, and ground-truth comparisons."
      );
    } catch (err) {
      console.error("Error downloading dataset:", err);
      addToast("error", "Download Error", "Failed to download processed dataset.");
    } finally {
      setIsDownloadingDataset(false);
    }
  };

  return (
    <div className="space-y-6 relative">
      {/* ================= TOAST NOTIFICATION CONTAINER ================= */}
      <div className="fixed bottom-5 right-5 z-50 space-y-2.5 max-w-md w-full pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto p-4 rounded-xl border shadow-2xl backdrop-blur-xl flex items-start space-x-3 transition-all animate-in slide-in-from-bottom-5 ${
              toast.type === "success"
                ? "bg-[#0c1f17]/95 border-emerald-500/50 text-emerald-100"
                : toast.type === "processing"
                ? "bg-[#1f190c]/95 border-amber-500/50 text-amber-100"
                : "bg-[#240e0e]/95 border-red-500/50 text-red-100"
            }`}
          >
            <div className="mt-0.5 shrink-0">
              {toast.type === "success" ? (
                <div className="w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                  <Check className="w-3.5 h-3.5 stroke-[3]" />
                </div>
              ) : toast.type === "processing" ? (
                <div className="w-6 h-6 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                </div>
              ) : (
                <div className="w-6 h-6 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center text-red-400">
                  <AlertCircle className="w-3.5 h-3.5" />
                </div>
              )}
            </div>

            <div className="flex-1 text-xs">
              <div className="font-bold font-mono tracking-tight text-white mb-0.5">
                {toast.title}
              </div>
              <p className="text-slate-300 font-sans leading-relaxed">{toast.message}</p>
              {toast.type === "processing" && (
                <div className="mt-2 flex items-center space-x-2 text-[10px] font-mono text-amber-300">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                  </span>
                  <span>Executing spaCy rules + 384-dim semantic embeddings...</span>
                </div>
              )}
            </div>

            <button
              onClick={() => removeToast(toast.id)}
              className="text-slate-400 hover:text-white p-1 rounded transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* ================= PAGE HEADER ================= */}
      <div className="border-b border-slate-800/80 pb-2">
        <div className="flex items-center space-x-2">
          <h1 className="text-2xl font-black tracking-tight text-white">
            Safety Report Ingestion
          </h1>
          <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded">
            SIF SENTINEL INTAKE
          </span>
        </div>
        <p className="text-xs text-slate-400 font-normal mt-0.5">
          Submit unstructured field observations or ingest bulk batches for instant SIF precursor classification and barrier mapping
        </p>
      </div>

      {/* ================= NAVIGATION TABS ================= */}
      <div className="flex space-x-2 border-b border-slate-800 pb-px">
        <button
          onClick={() => setActiveTab("single")}
          className={`px-4 py-2.5 text-xs font-mono font-bold rounded-t-lg transition border-t-2 flex items-center space-x-2 ${
            activeTab === "single"
              ? "bg-[#0c1322] text-amber-300 border-amber-500 border-x border-slate-800"
              : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900/40"
          }`}
        >
          <FileText className="w-3.5 h-3.5 text-amber-400" />
          <span>Single Observation Intake</span>
        </button>

        <button
          onClick={() => setActiveTab("bulk")}
          className={`px-4 py-2.5 text-xs font-mono font-bold rounded-t-lg transition border-t-2 flex items-center space-x-2 ${
            activeTab === "bulk"
              ? "bg-[#0c1322] text-amber-300 border-amber-500 border-x border-slate-800"
              : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900/40"
          }`}
        >
          <FileSpreadsheet className="w-3.5 h-3.5 text-cyan-400" />
          <span>Bulk Spreadsheet Upload (CSV/XLSX)</span>
        </button>
      </div>

      {/* ================= TAB 1: SINGLE REPORT INGESTION ================= */}
      {activeTab === "single" && (
        <div className="grid lg:grid-cols-12 gap-6">
          {/* Form Side */}
          <div className="lg:col-span-7 bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-6 shadow-xl backdrop-blur-md space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
              <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
                <FileText className="w-4 h-4 text-amber-400" />
                <span>Field Observation Entry</span>
              </h3>
              <span className="text-[11px] font-mono text-slate-400">
                POST /api/reports
              </span>
            </div>

            <form onSubmit={handleSingleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Report Type Select */}
                <div>
                  <label className="block text-xs font-mono font-medium text-slate-300 uppercase mb-1.5 flex items-center space-x-1.5">
                    <Tag className="w-3.5 h-3.5 text-amber-400" />
                    <span>Report Type *</span>
                  </label>
                  <select
                    value={reportType}
                    onChange={(e) => setReportType(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs font-mono text-white outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition cursor-pointer"
                  >
                    <option value="UA">UA — Unsafe Act</option>
                    <option value="UC">UC — Unsafe Condition</option>
                    <option value="near_miss">Near Miss (High-Potential Observation)</option>
                    <option value="incident">Incident / Dangerous Occurrence</option>
                  </select>
                </div>

                {/* Site Select */}
                <div>
                  <label className="block text-xs font-mono font-medium text-slate-300 uppercase mb-1.5 flex items-center space-x-1.5">
                    <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Operating Asset / Rig *</span>
                  </label>
                  <select
                    value={siteId}
                    onChange={(e) => setSiteId(Number(e.target.value))}
                    className="w-full px-3 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs font-mono text-white outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition cursor-pointer"
                  >
                    {sites.map((site) => (
                      <option key={site.id} value={site.id}>
                        {site.name} ({site.region})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Activity Text Input */}
                <div>
                  <label className="block text-xs font-mono font-medium text-slate-300 uppercase mb-1.5 flex items-center space-x-1.5">
                    <Building2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Activity Context *</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={activity}
                    onChange={(e) => setActivity(e.target.value)}
                    placeholder="e.g. Mud circulation & tripping, Hot work on manifold"
                    className="w-full px-3 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs font-mono text-white outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition"
                  />
                </div>

                {/* Language Select */}
                <div>
                  <label className="block text-xs font-mono font-medium text-slate-300 uppercase mb-1.5 flex items-center space-x-1.5">
                    <Globe className="w-3.5 h-3.5 text-amber-400" />
                    <span>Report Language</span>
                  </label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs font-mono text-white outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition cursor-pointer"
                  >
                    <option value="en">English (Standard Field Jargon)</option>
                    <option value="as">Assamese (অসমীয়া)</option>
                    <option value="hi">Hindi (हिन्दी)</option>
                    <option value="bn">Bengali (বাংলা)</option>
                  </select>
                </div>
              </div>

              {/* Free-Text Description Textarea */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-mono font-medium text-slate-300 uppercase tracking-wider">
                    Free-Text Narrative Description *
                  </label>
                  <span className="text-[10px] text-slate-400 font-mono">
                    Auto-analyzed by spaCy + Vector Classifier
                  </span>
                </div>
                <textarea
                  rows={5}
                  required
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Describe the unsafe condition, barrier failure, near miss or equipment anomaly in realistic field terminology (e.g. During valve replacement on high-pressure manifold, technician broke flange bolts without lock out tag out verification or bleeding line pressure...)"
                  className="w-full p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-600 outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition font-sans leading-relaxed"
                />
              </div>

              {/* Quick Preset Buttons for Evaluation */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                  Test Presets:
                </span>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setReportType("near_miss");
                      setActivity("Well Servicing & Rig Floor Work");
                      setRawText(
                        "While tripping drill string, winch operator hoisted 12-ton BHA without inspecting secondary brake latch. Casing elevator slipped 4 feet over active rotary table while floor crew was in line of fire."
                      );
                    }}
                    className="px-2.5 py-1 text-[11px] font-mono rounded bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/30 transition text-left"
                  >
                    ⚡ Line of Fire & Mechanical Lifting (SIF)
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setReportType("UA");
                      setActivity("Compressor Station Maintenance");
                      setRawText(
                        "Technician bypassed lockout tagout on discharge header electrical drive to expedite seal replacement before shift change without notifying control room engineer."
                      );
                    }}
                    className="px-2.5 py-1 text-[11px] font-mono rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition text-left"
                  >
                    ⚡ Energy Isolation Bypass (SIF)
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setReportType("UC");
                      setActivity("General Camp Housekeeping");
                      setRawText(
                        "Found empty solvent cans stored without primary safety lids in yard storage shed. Minor housekeeping issue, no active ignition sources nearby."
                      );
                    }}
                    className="px-2.5 py-1 text-[11px] font-mono rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition text-left"
                  >
                    🛡️ Routine Housekeeping (Non-SIF)
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmittingSingle || !rawText.trim()}
                className="w-full py-3 px-4 bg-gradient-to-r from-amber-500 hover:from-amber-400 to-amber-600 text-slate-950 font-bold text-xs rounded-lg shadow-lg shadow-amber-950/40 hover:shadow-amber-500/20 transition flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer font-mono uppercase tracking-wider"
              >
                {isSubmittingSingle ? (
                  <div className="flex items-center space-x-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                    <span>Transmitting to API Gateway...</span>
                  </div>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Submit & Execute SIF AI NLP Pipeline</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Right Side: Live Classification Output & Processing State */}
          <div className="lg:col-span-5 bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-6 shadow-xl backdrop-blur-md flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
                  <ShieldAlert className="w-4 h-4 text-cyan-400" />
                  <span>Real-Time AI Pipeline Telemetry</span>
                </h3>
                {isClassifying && (
                  <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px] font-mono">
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    <span>PROCESSING</span>
                  </span>
                )}
              </div>

              {activeReportData ? (
                <div className="space-y-4">
                  {/* Status Banner */}
                  <div
                    className={`p-3.5 rounded-xl border flex items-center justify-between ${
                      activeReportData.sif_label === "sif_potential"
                        ? "bg-red-950/40 border-red-500/50 text-red-200"
                        : activeReportData.sif_label === "non_sif"
                        ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-200"
                        : "bg-amber-950/40 border-amber-500/50 text-amber-200"
                    }`}
                  >
                    <div className="flex items-center space-x-2.5">
                      {activeReportData.sif_label === "sif_potential" ? (
                        <ShieldAlert className="w-5 h-5 text-red-400" />
                      ) : activeReportData.sif_label === "non_sif" ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <Clock className="w-5 h-5 text-amber-400 animate-pulse" />
                      )}
                      <div>
                        <div className="text-xs font-mono font-bold uppercase tracking-wide">
                          {activeReportData.sif_label === "sif_potential"
                            ? "SIF-POTENTIAL PRECURSOR DETECTED"
                            : activeReportData.sif_label === "non_sif"
                            ? "ROUTINE / NON-SIF OBSERVATION"
                            : "ANALYZING OBSERVATION NARRATIVE..."}
                        </div>
                        <div className="text-[11px] text-slate-300 font-sans">
                          Report #{activeReportData.id} • Status: {activeReportData.status}
                        </div>
                      </div>
                    </div>

                    {activeReportData.sif_confidence !== undefined &&
                      activeReportData.sif_confidence !== null && (
                        <span className="text-base font-black font-mono">
                          {(activeReportData.sif_confidence * 100).toFixed(0)}%
                        </span>
                      )}
                  </div>

                  {/* Classification Metrics Grid */}
                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
                      <div className="text-slate-400 text-[10px] uppercase">Primary IOGP LSR</div>
                      <div className="text-sm font-bold text-amber-400 mt-1">
                        {activeReportData.primary_lsr || (isClassifying ? "Tagging..." : "None Detected")}
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
                      <div className="text-slate-400 text-[10px] uppercase">Vector Embedding</div>
                      <div className="text-sm font-bold text-cyan-400 mt-1">
                        {isClassifying ? "Indexing..." : "384-dim Stored"}
                      </div>
                    </div>
                  </div>

                  {/* LSR Tags */}
                  {activeReportData.lsr_tags && activeReportData.lsr_tags.length > 0 && (
                    <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
                      <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                        Identified Life-Saving Rule Tags:
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {activeReportData.lsr_tags.map((tag, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 text-[11px] font-mono"
                          >
                            {tag.lsr_rule} ({Math.round(tag.confidence * 100)}%)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Barrier Failures */}
                  {activeReportData.barrier_failures && activeReportData.barrier_failures.length > 0 && (
                    <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
                      <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                        Extracted Barrier Failures:
                      </div>
                      <div className="space-y-1.5">
                        {activeReportData.barrier_failures.map((bf, idx) => (
                          <div
                            key={idx}
                            className="text-[11px] font-mono flex items-center justify-between text-slate-300"
                          >
                            <span className="text-amber-300">{bf.barrier_type}</span>
                            <span
                              className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-bold ${
                                bf.severity === "high"
                                  ? "bg-red-500/20 text-red-300 border border-red-500/40"
                                  : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                              }`}
                            >
                              {bf.severity}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Link to Full Report Detail */}
                  <a
                    href={`/reports/${activeReportData.id}`}
                    className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-amber-500/20 to-red-500/20 hover:from-amber-500/30 hover:to-red-500/30 text-white border border-amber-500/40 text-xs font-mono font-bold transition flex items-center justify-center space-x-2"
                  >
                    <span>View Complete Report Spans & Similar Cases</span>
                    <span>→</span>
                  </a>
                </div>
              ) : (
                <div className="py-20 text-center space-y-3">
                  <Layers className="w-10 h-10 mx-auto text-slate-700" />
                  <div className="text-xs font-mono text-slate-400">
                    Awaiting observation submission.
                  </div>
                  <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
                    Fill the form and submit to see live NLP pipeline classification, IOGP tagging, and Safety Memory matching.
                  </p>
                </div>
              )}
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-[11px] font-mono text-slate-400 flex items-center justify-between">
              <span>Classifier Engine:</span>
              <span className="text-slate-300">Hybrid Rule + Semantic (all-MiniLM-L6-v2)</span>
            </div>
          </div>
        </div>
      )}

      {/* ================= TAB 2: BULK SPREADSHEET UPLOAD ================= */}
      {activeTab === "bulk" && (
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="bg-[#0c1322]/90 border border-slate-800/90 rounded-xl p-6 sm:p-8 shadow-xl backdrop-blur-md space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
              <div>
                <h3 className="text-base font-bold text-white font-mono uppercase tracking-wider flex items-center space-x-2">
                  <FileSpreadsheet className="w-5 h-5 text-cyan-400" />
                  <span>Bulk Safety Log Batch Intake</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Ingest historical safety datasets (CSV / XLSX) into PostgreSQL + pgvector
                </p>
              </div>

              <button
                type="button"
                onClick={downloadSampleCsv}
                className="px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-mono flex items-center space-x-2 transition shrink-0"
              >
                <Download className="w-3.5 h-3.5 text-amber-400" />
                <span>Download Sample CSV</span>
              </button>
            </div>

            {/* Drag and Drop Zone */}
            <form onSubmit={handleBulkUpload} className="space-y-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv, .xlsx, .xls"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    validateAndSetFile(e.target.files[0]);
                  }
                }}
                className="hidden"
                id="bulk-spreadsheet-input"
              />

              {/* Optional Batch Label Input */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-300 flex items-center justify-between">
                  <span>Evaluation Batch Label (Optional)</span>
                  <span className="text-[10px] text-slate-500">Used to track accuracy & historical benchmarks</span>
                </label>
                <input
                  type="text"
                  value={batchLabel}
                  onChange={(e) => setBatchLabel(e.target.value)}
                  placeholder="e.g. OIL SIF Benchmark Dataset v2 (Oct 2026)"
                  className="w-full px-3 py-2 bg-slate-950/80 border border-slate-800 rounded-lg text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/60"
                />
              </div>

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition cursor-pointer flex flex-col items-center justify-center space-y-3 ${
                  isDragging
                    ? "border-amber-500 bg-amber-500/10"
                    : file
                    ? "border-cyan-500/60 bg-cyan-950/20"
                    : "border-slate-700/80 hover:border-amber-500/60 bg-slate-950/50"
                }`}
              >
                <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-amber-400 shadow-lg">
                  <Upload className="w-6 h-6" />
                </div>

                <div className="space-y-1">
                  <div className="text-sm font-bold text-white">
                    {file ? file.name : "Drag & Drop CSV or XLSX file here"}
                  </div>
                  <p className="text-xs text-slate-400 font-mono">
                    {file
                      ? `${(file.size / 1024).toFixed(1)} KB • Click to choose a different spreadsheet`
                      : "or browse file from your local workstation (Max 10 MB)"}
                  </p>
                </div>

                <div className="pt-1 flex flex-wrap items-center justify-center gap-1.5 text-[11px] font-mono text-slate-400">
                  <span>Required Fields:</span>
                  <code className="text-amber-300">report_type</code>
                  <code className="text-amber-300">raw_text</code>
                  <code className="text-amber-300">site_id</code>
                  <code className="text-amber-300">activity</code>
                  <span className="text-slate-600">•</span>
                  <span>Ground-truth:</span>
                  <code className="text-cyan-400">SIF_Label</code>
                  <code className="text-cyan-400">Life_Saving_Rule</code>
                  <code className="text-cyan-400">Split</code>
                </div>
              </div>

              {/* Preview Loading State */}
              {isPreviewLoading && (
                <div className="p-6 rounded-xl bg-[#0b1627]/90 border border-cyan-500/30 text-center space-y-3 animate-pulse">
                  <RefreshCw className="w-6 h-6 animate-spin text-cyan-400 mx-auto" />
                  <div className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-wider">
                    Analyzing Spreadsheet Schema & Column Headers...
                  </div>
                  <p className="text-[11px] text-slate-400 max-w-md mx-auto font-sans">
                    Inspecting header row, matching known OIL HSSE aliases, and checking database for saved mapping templates.
                  </p>
                </div>
              )}

              {/* ================= STEP 2: COLUMN MAPPING & CONFIRMATION PANEL ================= */}
              {previewData && !isPreviewLoading && (
                <div className="p-5 sm:p-6 rounded-xl bg-gradient-to-b from-[#0e172a] to-[#0a1120] border border-cyan-500/40 shadow-2xl space-y-5 animate-in fade-in">
                  {/* Panel Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <Sliders className="w-4 h-4 text-cyan-400" />
                        <h4 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
                          Schema Mapping Confirmation
                        </h4>
                      </div>
                      <p className="text-xs text-slate-400">
                        We detected <span className="text-cyan-300 font-mono font-bold">{previewData.detected_columns.length} columns</span>. Confirm or adjust how they map to SIF Sentinel database fields.
                      </p>
                    </div>

                    {/* Template Match or Auto-Map Badge */}
                    <div className="shrink-0">
                      {previewData.matched_template_name ? (
                        <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-mono font-bold flex items-center space-x-1.5 shadow-sm">
                          <Database className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Saved Template: {previewData.matched_template_name}</span>
                        </span>
                      ) : previewData.all_required_matched ? (
                        <span className="px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 text-xs font-mono font-bold flex items-center space-x-1.5 shadow-sm">
                          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                          <span>Auto-Matched via HSSE Aliases</span>
                        </span>
                      ) : (
                        <span className="px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-mono font-bold flex items-center space-x-1.5 shadow-sm">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                          <span>Manual Mapping Required</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Required Fields Status Badges */}
                  <div className="space-y-1.5">
                    <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center justify-between">
                      <span>Required Database Fields Status (Must Map All 4):</span>
                      <span className={`text-[11px] font-bold ${isAllRequiredMapped ? "text-emerald-400" : "text-amber-400"}`}>
                        {isAllRequiredMapped ? "✓ All 4 Mapped" : `⚠️ Missing: ${missingRequiredFields.join(", ")}`}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {[
                        { key: "raw_text", label: "Observation Narrative" },
                        { key: "report_type", label: "Report Type" },
                        { key: "site_id", label: "Site Location / ID" },
                        { key: "activity", label: "Activity Context" },
                      ].map((field) => {
                        const isMapped = mappedTargetValues.includes(field.key);
                        const assignedCol = Object.keys(userMapping).find((c) => userMapping[c] === field.key);
                        return (
                          <div
                            key={field.key}
                            className={`p-2 rounded-lg border text-xs font-mono transition flex items-center justify-between ${
                              isMapped
                                ? "bg-emerald-950/30 border-emerald-500/40 text-emerald-200"
                                : "bg-red-950/30 border-red-500/40 text-red-300"
                            }`}
                          >
                            <div className="truncate pr-1">
                              <div className="font-bold flex items-center space-x-1">
                                <span>{field.key}</span>
                                <span className="text-[10px] opacity-75">*</span>
                              </div>
                              <div className="text-[10px] text-slate-400 truncate">
                                {assignedCol ? `← "${assignedCol}"` : "Not assigned"}
                              </div>
                            </div>
                            {isMapped ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                            ) : (
                              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Mapping Table */}
                  <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/70 shadow-inner">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-slate-900/90 border-b border-slate-800 text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                            <th className="py-2.5 px-3.5">Detected Source Column</th>
                            <th className="py-2.5 px-3.5">First Row Sample</th>
                            <th className="py-2.5 px-3.5">Target System Field</th>
                            <th className="py-2.5 px-3.5 text-right">Confidence</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {previewData.detected_columns.map((col) => {
                            const currentTarget = userMapping[col] || "";
                            const confidence = previewData.mapping_confidence[col] || "unmapped";
                            const firstRowVal =
                              previewData.sample_rows && previewData.sample_rows.length > 0
                                ? String(previewData.sample_rows[0][col] ?? "")
                                : "";

                            return (
                              <tr key={col} className="hover:bg-slate-900/40 transition">
                                {/* Source Column */}
                                <td className="py-2.5 px-3.5 font-bold text-white flex items-center space-x-2">
                                  <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200">
                                    {col}
                                  </span>
                                </td>

                                {/* Sample Value */}
                                <td className="py-2.5 px-3.5 text-slate-400 max-w-[200px] truncate" title={firstRowVal}>
                                  {firstRowVal ? (
                                    <span className="text-slate-300 italic truncate block">"{firstRowVal}"</span>
                                  ) : (
                                    <span className="text-slate-600">—</span>
                                  )}
                                </td>

                                {/* Target Field Dropdown */}
                                <td className="py-2.5 px-3.5">
                                  <select
                                    value={currentTarget}
                                    onChange={(e) => handleMappingChange(col, e.target.value)}
                                    className={`w-full max-w-xs px-2.5 py-1.5 rounded-lg border text-xs font-mono outline-none transition cursor-pointer ${
                                      currentTarget === "raw_text" ||
                                      currentTarget === "report_type" ||
                                      currentTarget === "site_id" ||
                                      currentTarget === "activity"
                                        ? "bg-amber-950/40 border-amber-500/60 text-amber-200"
                                        : currentTarget
                                        ? "bg-cyan-950/40 border-cyan-500/60 text-cyan-200"
                                        : "bg-slate-900 border-slate-700 text-slate-400"
                                    }`}
                                  >
                                    <option value="">-- Do Not Import (Ignore) --</option>
                                    <optgroup label="Required Safety Fields (4)">
                                      <option value="raw_text">raw_text (Narrative / Description) *</option>
                                      <option value="report_type">report_type (UA / UC / Near Miss) *</option>
                                      <option value="site_id">site_id (Site Code or Location Name) *</option>
                                      <option value="activity">activity (Activity / Task Description) *</option>
                                    </optgroup>
                                    <optgroup label="Ground-Truth Benchmark Labels">
                                      <option value="SIF_Label">SIF_Label (Historical SIF Precursor)</option>
                                      <option value="Life_Saving_Rule">Life_Saving_Rule (IOGP 9 Rule)</option>
                                      <option value="Barrier_Status">Barrier_Status (Barrier Condition)</option>
                                      <option value="Actual_Outcome">Actual_Outcome (Incident Severity)</option>
                                      <option value="Split">Split (train / test / val)</option>
                                    </optgroup>
                                    <optgroup label="Optional Metadata">
                                      <option value="submitted_at">submitted_at (Observation Date)</option>
                                      <option value="language">language (Report Language)</option>
                                      <option value="reporter_id">reporter_id (Observer Identifier)</option>
                                    </optgroup>
                                  </select>
                                </td>

                                {/* Confidence / Match Badge */}
                                <td className="py-2.5 px-3.5 text-right">
                                  {confidence === "saved_template" ? (
                                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px]">
                                      Saved Template
                                    </span>
                                  ) : confidence === "high" ? (
                                    <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-[10px]">
                                      High (Alias)
                                    </span>
                                  ) : confidence === "medium" ? (
                                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px]">
                                      Fuzzy Match
                                    </span>
                                  ) : currentTarget ? (
                                    <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30 text-[10px]">
                                      Manual
                                    </span>
                                  ) : (
                                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-500 text-[10px]">
                                      Ignored
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Sample Rows Toggle Drawer */}
                  <div className="space-y-2">
                    <button
                      type="button"
                      onClick={() => setShowSampleRows(!showSampleRows)}
                      className="text-xs font-mono text-slate-400 hover:text-cyan-300 transition flex items-center space-x-1.5 cursor-pointer"
                    >
                      {showSampleRows ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      <span>{showSampleRows ? "Hide Sample Data Rows" : `Preview First ${previewData.total_preview_rows} Data Rows`}</span>
                    </button>

                    {showSampleRows && previewData.sample_rows && (
                      <div className="border border-slate-800 rounded-lg overflow-x-auto bg-slate-950 p-3 max-h-56 overflow-y-auto">
                        <table className="w-full text-left text-[11px] font-mono border-collapse">
                          <thead>
                            <tr className="border-b border-slate-800 text-slate-400">
                              <th className="py-1 px-2">#</th>
                              {previewData.detected_columns.map((c) => (
                                <th key={c} className="py-1 px-2 whitespace-nowrap">
                                  {c}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/40 text-slate-300">
                            {previewData.sample_rows.map((row, idx) => (
                              <tr key={idx} className="hover:bg-slate-900/50">
                                <td className="py-1 px-2 text-slate-500">{idx + 1}</td>
                                {previewData.detected_columns.map((c) => (
                                  <td key={c} className="py-1 px-2 whitespace-nowrap max-w-xs truncate">
                                    {String(row[c] ?? "")}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  {/* Template Saving & Confirmation Bar */}
                  <div className="pt-3 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    {/* Save Template Option */}
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="save-template-checkbox"
                        checked={saveTemplate}
                        onChange={(e) => setSaveTemplate(e.target.checked)}
                        className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0 cursor-pointer"
                      />
                      <label htmlFor="save-template-checkbox" className="text-xs font-mono text-slate-300 cursor-pointer select-none">
                        Remember mapping template for future uploads with this column schema
                      </label>
                    </div>

                    {/* Confirm Mapping Toggle Button */}
                    <button
                      type="button"
                      disabled={!isAllRequiredMapped}
                      onClick={() => setIsMappingConfirmed(!isMappingConfirmed)}
                      className={`px-4 py-2 rounded-lg font-mono text-xs font-bold transition flex items-center space-x-2 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                        isMappingConfirmed
                          ? "bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-950/40"
                          : "bg-slate-800 hover:bg-slate-700 text-white border border-slate-600"
                      }`}
                    >
                      {isMappingConfirmed ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-slate-950 stroke-[2.5]" />
                          <span>Mapping Confirmed (Click to Edit)</span>
                        </>
                      ) : (
                        <>
                          <CheckSquare className="w-4 h-4 text-cyan-400" />
                          <span>Confirm & Lock Column Mapping</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Upload Trigger Button */}
              <button
                type="submit"
                disabled={isUploadingBulk || !file || !isAllRequiredMapped || !isMappingConfirmed}
                className="w-full py-3.5 px-4 bg-gradient-to-r from-cyan-500 hover:from-cyan-400 to-cyan-600 text-slate-950 font-bold text-xs rounded-lg shadow-lg shadow-cyan-950/40 hover:shadow-cyan-500/20 transition flex items-center justify-center space-x-2 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer font-mono uppercase tracking-wider"
              >
                {isUploadingBulk ? (
                  <div className="flex items-center space-x-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                    <span>Parsing Spreadsheet & Ingesting Rows with Confirmed Schema...</span>
                  </div>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>
                      {file && !isAllRequiredMapped
                        ? "Map Required Fields to Enable Ingestion"
                        : file && !isMappingConfirmed
                        ? "Confirm Mapping Above to Proceed"
                        : "Upload & Trigger Background AI Pipeline"}
                    </span>
                  </>
                )}
              </button>
            </form>

            {/* ================= BATCH INGESTION SUMMARY ================= */}
            {bulkSummary && (
              <div className="space-y-6 pt-6 border-t border-slate-800/80 animate-in fade-in">
                {/* Header & Export Action Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                      <h4 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
                        Batch Ingestion Summary
                      </h4>
                    </div>
                    <p className="text-xs text-slate-400 font-sans mt-0.5">
                      Batch ID: <span className="text-cyan-400 font-mono">{bulkSummary.upload_batch_id || "batch_ingest"}</span>
                      {bulkSummary.upload_batch_label && (
                        <span> • <span className="text-amber-300 font-mono">{bulkSummary.upload_batch_label}</span></span>
                      )}
                    </p>
                  </div>

                  {/* Download Processed Dataset Button */}
                  <button
                    type="button"
                    onClick={handleDownloadProcessedDataset}
                    disabled={isDownloadingDataset || !bulkSummary.upload_batch_id}
                    className="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 hover:from-emerald-400 to-teal-500 text-slate-950 font-bold font-mono text-xs shadow-lg shadow-emerald-950/40 hover:shadow-emerald-500/20 transition flex items-center space-x-2 disabled:opacity-50 cursor-pointer shrink-0"
                  >
                    {isDownloadingDataset ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-slate-950" />
                        <span>Exporting CSV...</span>
                      </>
                    ) : (
                      <>
                        <FileDown className="w-4 h-4" />
                        <span>Download Processed Dataset</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Top Row of Stat Cards (4 Cards) */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
                  {/* Stat Card 1: Total Rows Scanned */}
                  <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 shadow-md">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="text-[10px] font-mono uppercase tracking-wider">Total Rows Scanned</span>
                      <FileSpreadsheet className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div className="text-2xl font-black font-mono text-white mt-2">
                      {bulkSummary.total_rows.toLocaleString()}
                    </div>
                    <div className="text-[11px] text-slate-400 font-sans mt-1">
                      Raw spreadsheet records parsed
                    </div>
                  </div>

                  {/* Stat Card 2: Accepted */}
                  <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 shadow-md">
                    <div className="flex items-center justify-between text-emerald-400">
                      <span className="text-[10px] font-mono uppercase tracking-wider">Accepted</span>
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    </div>
                    <div className="text-2xl font-black font-mono text-emerald-300 mt-2">
                      {bulkSummary.accepted_count.toLocaleString()}
                    </div>
                    <div className="text-[11px] text-emerald-400/80 font-sans mt-1">
                      {bulkSummary.total_rows > 0
                        ? `${((bulkSummary.accepted_count / bulkSummary.total_rows) * 100).toFixed(1)}%`
                        : "0%"} passing schema validation
                    </div>
                  </div>

                  {/* Stat Card 3: Rejected */}
                  <div className={`p-4 rounded-xl ${bulkSummary.rejected_count > 0 ? "bg-red-950/20 border-red-500/30" : "bg-slate-950/80 border-slate-800"} border shadow-md`}>
                    <div className="flex items-center justify-between text-red-400">
                      <span className="text-[10px] font-mono uppercase tracking-wider">Rejected</span>
                      <AlertCircle className="w-4 h-4 text-red-400" />
                    </div>
                    <div className="text-2xl font-black font-mono text-red-300 mt-2">
                      {bulkSummary.rejected_count.toLocaleString()}
                    </div>
                    <div className="text-[11px] text-red-400/80 font-sans mt-1">
                      {bulkSummary.rejected_count > 0
                        ? `${((bulkSummary.rejected_count / bulkSummary.total_rows) * 100).toFixed(1)}% validation errors`
                        : "Zero validation errors"}
                    </div>
                  </div>

                  {/* Stat Card 4: Queued for AI NLP */}
                  <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 shadow-md">
                    <div className="flex items-center justify-between text-amber-400">
                      <span className="text-[10px] font-mono uppercase tracking-wider">Queued for AI NLP</span>
                      <Sparkles className="w-4 h-4 text-amber-400" />
                    </div>
                    <div className="text-2xl font-black font-mono text-amber-300 mt-2">
                      {bulkSummary.accepted_count.toLocaleString()}
                    </div>
                    <div className="text-[11px] text-amber-400/80 font-sans mt-1">
                      Async spaCy & pgvector indexing
                    </div>
                  </div>
                </div>

                {/* Ground-Truth Dataset Accuracy Preview Card */}
                {bulkSummary.has_ground_truth && (
                  <div className="p-4 sm:p-5 rounded-xl bg-gradient-to-r from-cyan-950/40 via-slate-900/90 to-emerald-950/30 border border-cyan-500/40 shadow-xl space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                          <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                            <span>Dataset Accuracy Preview</span>
                            <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-[10px] border border-cyan-500/30 font-normal">
                              Ground-Truth Labels Detected
                            </span>
                          </h4>
                        </div>
                        <p className="text-xs text-slate-300 font-sans">
                          SIF Classification benchmark evaluated across{" "}
                          <span className="font-bold text-cyan-300">
                            {bulkSummary.ground_truth_count?.toLocaleString() || accuracyReport?.labeled_reports_count?.toLocaleString() || 0}
                          </span>{" "}
                          labeled ground-truth records.
                        </p>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          type="button"
                          onClick={() => setShowFullAccuracy(!showFullAccuracy)}
                          className="px-3 py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 text-cyan-200 text-xs font-mono font-bold flex items-center space-x-1.5 transition cursor-pointer shadow-sm"
                        >
                          <span>{showFullAccuracy ? "Hide Full Report" : "View Full Accuracy Report"}</span>
                          {showFullAccuracy ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>

                        {bulkSummary.upload_batch_id && (
                          <a
                            href={`/api/datasets/${bulkSummary.upload_batch_id}/accuracy-report`}
                            target="_blank"
                            rel="noreferrer"
                            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 hover:text-white transition"
                            title="Open Accuracy Report API Endpoint"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Quick Accuracy Metric Pills */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-center">
                      <div className="p-3 rounded-lg bg-slate-950/80 border border-cyan-500/40">
                        <div className="text-slate-400 text-[10px] uppercase">SIF Classification Accuracy</div>
                        <div className="text-2xl font-black text-cyan-300 mt-1">
                          {accuracyReport ? `${(accuracyReport.overall_sif_accuracy * 100).toFixed(1)}%` : "Evaluating..."}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
                        <div className="text-slate-400 text-[10px] uppercase">Precision (SIF)</div>
                        <div className="text-2xl font-black text-emerald-400 mt-1">
                          {accuracyReport ? `${(accuracyReport.sif_metrics.precision * 100).toFixed(1)}%` : "-"}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
                        <div className="text-slate-400 text-[10px] uppercase">Recall / Sensitivity</div>
                        <div className="text-2xl font-black text-amber-400 mt-1">
                          {accuracyReport ? `${(accuracyReport.sif_metrics.recall * 100).toFixed(1)}%` : "-"}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
                        <div className="text-slate-400 text-[10px] uppercase">LSR Macro Accuracy</div>
                        <div className="text-2xl font-black text-purple-400 mt-1">
                          {accuracyReport ? `${(accuracyReport.lsr_macro_accuracy * 100).toFixed(1)}%` : "-"}
                        </div>
                      </div>
                    </div>

                    {/* Detailed Full Accuracy Report (Expandable) */}
                    {showFullAccuracy && accuracyReport && (
                      <div className="pt-4 border-t border-cyan-500/20 space-y-4 animate-in fade-in">
                        <div className="flex items-center justify-between">
                          <h5 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                            Full Model Benchmark Breakdown
                          </h5>
                          <button
                            type="button"
                            onClick={() => bulkSummary.upload_batch_id && fetchAccuracyReport(bulkSummary.upload_batch_id)}
                            disabled={isLoadingAccuracy}
                            className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-[11px] font-mono flex items-center space-x-1.5 transition cursor-pointer"
                          >
                            <RefreshCw className={`w-3 h-3 ${isLoadingAccuracy ? "animate-spin" : ""}`} />
                            <span>Refresh Benchmark</span>
                          </button>
                        </div>

                        {/* Confusion Matrix & Split Breakdown */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {/* Confusion Matrix */}
                          <div className="p-3.5 rounded-lg bg-slate-950/90 border border-slate-800 space-y-2">
                            <div className="text-xs font-mono font-bold text-slate-300">
                              Confusion Matrix (SIF Potential vs Non-SIF)
                            </div>
                            <div className="overflow-x-auto">
                              <table className="w-full text-center border-collapse text-xs font-mono">
                                <thead>
                                  <tr className="bg-slate-900 text-[10px] text-slate-400 uppercase">
                                    <th className="py-1.5 px-2 border border-slate-800">Actual \ Pred</th>
                                    <th className="py-1.5 px-2 border border-slate-800 text-amber-300">Pred SIF</th>
                                    <th className="py-1.5 px-2 border border-slate-800 text-emerald-300">Pred Non-SIF</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  <tr>
                                    <td className="py-1.5 px-2 border border-slate-800 text-left text-amber-300 font-bold">
                                      Actual SIF
                                    </td>
                                    <td className="py-1.5 px-2 border border-slate-800 bg-emerald-950/30 text-emerald-300 font-bold">
                                      {accuracyReport.confusion_matrix.true_positives} (TP)
                                    </td>
                                    <td className="py-1.5 px-2 border border-slate-800 bg-red-950/30 text-red-400">
                                      {accuracyReport.confusion_matrix.false_negatives} (FN)
                                    </td>
                                  </tr>
                                  <tr>
                                    <td className="py-1.5 px-2 border border-slate-800 text-left text-emerald-300 font-bold">
                                      Actual Non-SIF
                                    </td>
                                    <td className="py-1.5 px-2 border border-slate-800 bg-red-950/30 text-red-400">
                                      {accuracyReport.confusion_matrix.false_positives} (FP)
                                    </td>
                                    <td className="py-1.5 px-2 border border-slate-800 bg-emerald-950/30 text-emerald-300 font-bold">
                                      {accuracyReport.confusion_matrix.true_negatives} (TN)
                                    </td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                            {accuracyReport.confusion_matrix.pending_evaluation > 0 && (
                              <div className="text-[10px] text-cyan-400 font-mono text-center">
                                ⚡ {accuracyReport.confusion_matrix.pending_evaluation} reports currently processing in background pipeline
                              </div>
                            )}
                          </div>

                          {/* Split Breakdown */}
                          <div className="p-3.5 rounded-lg bg-slate-950/90 border border-slate-800 space-y-2">
                            <div className="text-xs font-mono font-bold text-slate-300">
                              Dataset Splits Evaluation (Train / Test / Val)
                            </div>
                            {Object.keys(accuracyReport.splits_breakdown).length > 0 ? (
                              <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse text-xs font-mono">
                                  <thead>
                                    <tr className="bg-slate-900 text-[10px] text-slate-400 uppercase">
                                      <th className="py-1.5 px-2 border border-slate-800">Split</th>
                                      <th className="py-1.5 px-2 border border-slate-800 text-center">Samples</th>
                                      <th className="py-1.5 px-2 border border-slate-800 text-center">SIF Acc</th>
                                      <th className="py-1.5 px-2 border border-slate-800 text-center">F1</th>
                                      <th className="py-1.5 px-2 border border-slate-800 text-center">LSR Acc</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-800">
                                    {Object.entries(accuracyReport.splits_breakdown).map(([splitName, splitData]) => (
                                      <tr key={splitName} className="hover:bg-slate-900/40">
                                        <td className="py-1.5 px-2 uppercase font-bold text-cyan-300">
                                          {splitName}
                                        </td>
                                        <td className="py-1.5 px-2 text-center text-slate-300">
                                          {splitData.sample_count}
                                        </td>
                                        <td className="py-1.5 px-2 text-center text-emerald-400 font-bold">
                                          {(splitData.sif_metrics.accuracy * 100).toFixed(1)}%
                                        </td>
                                        <td className="py-1.5 px-2 text-center text-purple-400">
                                          {(splitData.sif_metrics.f1_score * 100).toFixed(1)}%
                                        </td>
                                        <td className="py-1.5 px-2 text-center text-blue-400">
                                          {(splitData.lsr_overall_accuracy * 100).toFixed(1)}%
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            ) : (
                              <div className="text-[11px] font-mono text-slate-500 py-4 text-center">
                                No split tags detected. Add a 'Split' column (train/test/val) to evaluate subsets separately.
                              </div>
                            )}
                          </div>
                        </div>

                        {/* LSR Tagging Per-Rule Accuracy */}
                        {accuracyReport.lsr_rule_accuracies && accuracyReport.lsr_rule_accuracies.length > 0 && (
                          <div className="space-y-2">
                            <div className="text-xs font-mono font-bold text-slate-300">
                              Life-Saving Rule (LSR) Tagging Accuracy Per Rule
                            </div>
                            <div className="overflow-x-auto border border-slate-800 rounded-lg max-h-48 overflow-y-auto">
                              <table className="w-full text-left border-collapse text-xs font-mono">
                                <thead>
                                  <tr className="bg-slate-900 border-b border-slate-800 text-[10px] text-slate-400 uppercase sticky top-0">
                                    <th className="py-1.5 px-3">Life-Saving Rule</th>
                                    <th className="py-1.5 px-3 text-center">Ground-Truth Count</th>
                                    <th className="py-1.5 px-3 text-center">Correct Predictions</th>
                                    <th className="py-1.5 px-3 text-center">Rule Accuracy</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/60 bg-slate-950/90">
                                  {accuracyReport.lsr_rule_accuracies.map((r, rIdx) => (
                                    <tr key={rIdx} className="hover:bg-slate-900/30">
                                      <td className="py-1.5 px-3 text-slate-200">{r.rule}</td>
                                      <td className="py-1.5 px-3 text-center text-slate-400">{r.total_ground_truth}</td>
                                      <td className="py-1.5 px-3 text-center text-emerald-400">{r.correct_predictions}</td>
                                      <td className="py-1.5 px-3 text-center font-bold text-cyan-300">
                                        {(r.accuracy * 100).toFixed(1)}%
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Accepted Rows Distribution Breakdown Visual Charts */}
                {bulkSummary.accepted_count > 0 && (() => {
                  const totalAcc = bulkSummary.accepted_count;
                  
                  // SIF label counts
                  const sifPotential = (bulkSummary.ground_truth_sif_counts?.sif_potential || 0) + (bulkSummary.sif_label_counts?.sif_potential || 0);
                  const nonSif = (bulkSummary.ground_truth_sif_counts?.non_sif || 0) + (bulkSummary.sif_label_counts?.non_sif || 0);
                  const reviewCount = Math.max(0, totalAcc - sifPotential - nonSif);

                  const sifPct = Math.round((sifPotential / totalAcc) * 100);
                  const nonSifPct = Math.round((nonSif / totalAcc) * 100);
                  const reviewPct = Math.max(0, 100 - sifPct - nonSifPct);

                  // Report Type counts
                  const nearMiss = bulkSummary.report_type_counts?.near_miss || bulkSummary.report_type_counts?.["Near Miss"] || 0;
                  const ua = bulkSummary.report_type_counts?.unsafe_act || bulkSummary.report_type_counts?.UA || bulkSummary.report_type_counts?.["Unsafe Act"] || 0;
                  const uc = bulkSummary.report_type_counts?.unsafe_condition || bulkSummary.report_type_counts?.UC || bulkSummary.report_type_counts?.["Unsafe Condition"] || 0;
                  const incident = bulkSummary.report_type_counts?.incident || bulkSummary.report_type_counts?.Incident || 0;
                  const otherType = Math.max(0, totalAcc - nearMiss - ua - uc - incident);

                  return (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Breakdown Chart 1: SIF Label */}
                      <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 shadow-md space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <PieChart className="w-4 h-4 text-amber-400" />
                            <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                              SIF Severity Distribution
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-slate-400">
                            {totalAcc.toLocaleString()} Accepted Rows
                          </span>
                        </div>

                        {/* Visual Segmented Distribution Bar */}
                        <div className="w-full h-3 rounded-full bg-slate-900 overflow-hidden flex shadow-inner">
                          {sifPct > 0 && (
                            <div
                              style={{ width: `${sifPct}%` }}
                              className="bg-gradient-to-r from-red-600 to-rose-500 h-full transition-all duration-500"
                              title={`SIF-potential: ${sifPotential} (${sifPct}%)`}
                            />
                          )}
                          {nonSifPct > 0 && (
                            <div
                              style={{ width: `${nonSifPct}%` }}
                              className="bg-gradient-to-r from-emerald-600 to-teal-500 h-full transition-all duration-500"
                              title={`Non-SIF: ${nonSif} (${nonSifPct}%)`}
                            />
                          )}
                          {reviewPct > 0 && (
                            <div
                              style={{ width: `${reviewPct}%` }}
                              className="bg-gradient-to-r from-blue-600 to-indigo-500 h-full transition-all duration-500"
                              title={`Pending Review: ${reviewCount} (${reviewPct}%)`}
                            />
                          )}
                        </div>

                        {/* Summary Pill Legend */}
                        <div className="grid grid-cols-3 gap-2 pt-1 font-mono text-center">
                          <div className="p-2 rounded-lg bg-red-950/20 border border-red-500/30">
                            <div className="text-[10px] text-red-400 uppercase flex items-center justify-center space-x-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                              <span>SIF-potential</span>
                            </div>
                            <div className="text-sm font-bold text-red-300 mt-0.5">
                              {sifPotential.toLocaleString()} <span className="text-[10px] text-red-400/80 font-normal">({sifPct}%)</span>
                            </div>
                          </div>

                          <div className="p-2 rounded-lg bg-emerald-950/20 border border-emerald-500/30">
                            <div className="text-[10px] text-emerald-400 uppercase flex items-center justify-center space-x-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                              <span>Non-SIF</span>
                            </div>
                            <div className="text-sm font-bold text-emerald-300 mt-0.5">
                              {nonSif.toLocaleString()} <span className="text-[10px] text-emerald-400/80 font-normal">({nonSifPct}%)</span>
                            </div>
                          </div>

                          <div className="p-2 rounded-lg bg-blue-950/20 border border-blue-500/30">
                            <div className="text-[10px] text-blue-400 uppercase flex items-center justify-center space-x-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                              <span>Pending Review</span>
                            </div>
                            <div className="text-sm font-bold text-blue-300 mt-0.5">
                              {reviewCount.toLocaleString()} <span className="text-[10px] text-blue-400/80 font-normal">({reviewPct}%)</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Breakdown Chart 2: Report Type */}
                      <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 shadow-md space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <BarChart3 className="w-4 h-4 text-cyan-400" />
                            <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                              Report Type Breakdown
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-slate-400">
                            Observation Class
                          </span>
                        </div>

                        {/* Visual Segmented Distribution Bar */}
                        <div className="w-full h-3 rounded-full bg-slate-900 overflow-hidden flex shadow-inner">
                          {nearMiss > 0 && (
                            <div
                              style={{ width: `${(nearMiss / totalAcc) * 100}%` }}
                              className="bg-gradient-to-r from-amber-600 to-amber-500 h-full transition-all duration-500"
                              title={`Near Miss: ${nearMiss}`}
                            />
                          )}
                          {ua > 0 && (
                            <div
                              style={{ width: `${(ua / totalAcc) * 100}%` }}
                              className="bg-gradient-to-r from-purple-600 to-purple-500 h-full transition-all duration-500"
                              title={`Unsafe Act: ${ua}`}
                            />
                          )}
                          {uc > 0 && (
                            <div
                              style={{ width: `${(uc / totalAcc) * 100}%` }}
                              className="bg-gradient-to-r from-cyan-600 to-cyan-500 h-full transition-all duration-500"
                              title={`Unsafe Condition: ${uc}`}
                            />
                          )}
                          {incident > 0 && (
                            <div
                              style={{ width: `${(incident / totalAcc) * 100}%` }}
                              className="bg-gradient-to-r from-rose-600 to-rose-500 h-full transition-all duration-500"
                              title={`Incident: ${incident}`}
                            />
                          )}
                          {otherType > 0 && (
                            <div
                              style={{ width: `${(otherType / totalAcc) * 100}%` }}
                              className="bg-slate-700 h-full transition-all duration-500"
                              title={`Other: ${otherType}`}
                            />
                          )}
                        </div>

                        {/* Summary Pill Legend */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-center">
                          <div className="p-2 rounded-lg bg-amber-950/20 border border-amber-500/30">
                            <div className="text-[9px] text-amber-400 uppercase truncate">Near Miss</div>
                            <div className="text-xs font-bold text-amber-300 mt-0.5">
                              {nearMiss.toLocaleString()} <span className="text-[9px] text-amber-400/80 font-normal">({Math.round((nearMiss / totalAcc) * 100)}%)</span>
                            </div>
                          </div>

                          <div className="p-2 rounded-lg bg-purple-950/20 border border-purple-500/30">
                            <div className="text-[9px] text-purple-400 uppercase truncate">Unsafe Act</div>
                            <div className="text-xs font-bold text-purple-300 mt-0.5">
                              {ua.toLocaleString()} <span className="text-[9px] text-purple-400/80 font-normal">({Math.round((ua / totalAcc) * 100)}%)</span>
                            </div>
                          </div>

                          <div className="p-2 rounded-lg bg-cyan-950/20 border border-cyan-500/30">
                            <div className="text-[9px] text-cyan-400 uppercase truncate">Unsafe Cond</div>
                            <div className="text-xs font-bold text-cyan-300 mt-0.5">
                              {uc.toLocaleString()} <span className="text-[9px] text-cyan-400/80 font-normal">({Math.round((uc / totalAcc) * 100)}%)</span>
                            </div>
                          </div>

                          <div className="p-2 rounded-lg bg-rose-950/20 border border-rose-500/30">
                            <div className="text-[9px] text-rose-400 uppercase truncate">Incident</div>
                            <div className="text-xs font-bold text-rose-300 mt-0.5">
                              {incident.toLocaleString()} <span className="text-[9px] text-rose-400/80 font-normal">({Math.round((incident / totalAcc) * 100)}%)</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* Rejected Rows Breakdown Section (ONLY rendered when rejected_count > 0) */}
                {bulkSummary.rejected_count > 0 && (
                  <div className="space-y-3 pt-2">
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-mono font-bold text-red-400 flex items-center space-x-2">
                        <AlertTriangle className="w-4 h-4 text-red-400" />
                        <span>Rejected Rows Breakdown ({bulkSummary.rejected_count.toLocaleString()} Total Rejected)</span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-500">
                        Click reason to expand sample row snippets
                      </span>
                    </div>

                    {/* Grouped Rejection Accordions */}
                    {bulkSummary.rejection_breakdown && bulkSummary.rejection_breakdown.length > 0 ? (
                      <div className="space-y-2.5">
                        {bulkSummary.rejection_breakdown.map((group, gIdx) => {
                          const isExpanded = !!expandedReasons[gIdx];
                          const groupPct = bulkSummary.rejected_count > 0 ? Math.round((group.count / bulkSummary.rejected_count) * 100) : 0;

                          return (
                            <div
                              key={gIdx}
                              className="border border-red-500/30 rounded-xl overflow-hidden bg-red-950/15 transition shadow-sm hover:border-red-500/50"
                            >
                              <button
                                type="button"
                                onClick={() => toggleReasonExpand(gIdx)}
                                className="w-full p-3.5 text-left flex items-center justify-between text-xs font-mono hover:bg-red-950/30 transition cursor-pointer"
                              >
                                <div className="flex items-center space-x-2.5 pr-2">
                                  <div className="p-1 rounded bg-red-500/20 text-red-400 shrink-0">
                                    <AlertCircle className="w-3.5 h-3.5" />
                                  </div>
                                  <div>
                                    <span className="font-bold text-red-300">{group.reason}</span>
                                    <div className="text-[10px] text-slate-400 font-sans mt-0.5">
                                      {group.examples?.length || 0} sample rows available for debugging
                                    </div>
                                  </div>
                                </div>

                                <div className="flex items-center space-x-2.5 shrink-0">
                                  <span className="px-2.5 py-1 rounded-full bg-red-500/20 text-red-300 font-bold border border-red-500/40 text-[11px]">
                                    {group.count.toLocaleString()} {group.count === 1 ? "row" : "rows"} ({groupPct}%)
                                  </span>
                                  <div className="p-1 rounded bg-slate-900/60 text-slate-400">
                                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                  </div>
                                </div>
                              </button>

                              {/* Expandable Snippet Table */}
                              {isExpanded && group.examples && group.examples.length > 0 && (
                                <div className="p-3 pt-0 animate-in fade-in">
                                  <div className="overflow-x-auto border border-red-500/20 rounded-lg bg-slate-950/85">
                                    <table className="w-full text-left border-collapse text-[11px] font-mono">
                                      <thead>
                                        <tr className="bg-red-950/40 border-b border-red-500/20 text-red-300 uppercase text-[10px]">
                                          <th className="py-2 px-3 w-20">Row #</th>
                                          <th className="py-2 px-3">Parsed Row Data Snippet (Max 20 Samples Shown)</th>
                                        </tr>
                                      </thead>
                                      <tbody className="divide-y divide-red-500/10">
                                        {group.examples.map((ex, exIdx) => (
                                          <tr key={exIdx} className="hover:bg-red-950/20 transition">
                                            <td className="py-2 px-3 font-bold text-red-400 align-top">
                                              Row {ex.row}
                                            </td>
                                            <td className="py-2 px-3 text-slate-300 font-mono text-[11px] break-all">
                                              <div className="bg-slate-900/80 p-2 rounded border border-slate-800 text-[10px] text-slate-300 overflow-x-auto">
                                                {JSON.stringify(ex.data, null, 2)}
                                              </div>
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      /* Fallback flat table if no groups formed */
                      <div className="overflow-x-auto border border-red-500/30 rounded-xl bg-slate-950/80">
                        <table className="w-full text-left border-collapse text-xs font-mono">
                          <thead>
                            <tr className="bg-red-950/40 border-b border-red-500/30 text-[10px] text-red-300 uppercase">
                              <th className="py-2.5 px-3">Row #</th>
                              <th className="py-2.5 px-3">Rejection Reason</th>
                              <th className="py-2.5 px-3">Row Data Snippet</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-red-500/20">
                            {bulkSummary.errors.slice(0, 50).map((err, idx) => (
                              <tr key={idx} className="hover:bg-red-950/20 transition">
                                <td className="py-2.5 px-3 font-bold text-red-400">
                                  Row {err.row}
                                </td>
                                <td className="py-2.5 px-3 text-slate-300">{err.reason}</td>
                                <td className="py-2.5 px-3 text-slate-400 font-mono text-[10px] max-w-xs truncate">
                                  {JSON.stringify(err.data)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* Accepted IDs Preview */}
                {bulkSummary.accepted_report_ids && bulkSummary.accepted_report_ids.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                    <div className="text-[11px] font-mono text-slate-400 flex items-center justify-between">
                      <span>Accepted Report IDs (Asynchronous NLP Queued):</span>
                      <span className="text-emerald-400 font-bold">
                        {bulkSummary.accepted_report_ids.length.toLocaleString()} Jobs
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                      {bulkSummary.accepted_report_ids.map((id) => (
                        <span
                          key={id}
                          className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300 text-[10px] font-mono"
                        >
                          #{id}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
