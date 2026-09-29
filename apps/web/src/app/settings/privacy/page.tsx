"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  Download,
  Trash2,
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Lock,
  ExternalLink,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { BACKEND_URL } from "@/lib/config";

export default function PrivacySettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("workkbot_auth");
      if (stored) {
        setUser(JSON.parse(stored));
      }
    } catch (e) {
      // Ignored
    } finally {
      setLoading(false);
    }
  }, []);

  const getAuthToken = () => {
    return user?.access_token || localStorage.getItem("workkbot_token") || "";
  };

  const handleExportData = async () => {
    setExporting(true);
    setMessage(null);
    try {
      const token = getAuthToken();
      const res = await fetch(`${BACKEND_URL}/api/v1/account/export`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        throw new Error(`Export failed with status ${res.status}`);
      }

      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `workkbot-privacy-export-${user?.id?.slice(0, 8) || "user"}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setMessage({ type: "success", text: "Your data has been exported successfully." });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to export data." });
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmationText !== "DELETE") return;
    setDeleting(true);
    setMessage(null);
    try {
      const token = getAuthToken();
      const res = await fetch(`${BACKEND_URL}/api/v1/account/delete`, {
        method: "DELETE",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        throw new Error("Account deletion failed on server");
      }

      try {
        await supabase.auth.signOut();
      } catch (e) {
        // Offline safe
      }
      localStorage.removeItem("workkbot_auth");
      localStorage.removeItem("workkbot_token");
      router.push("/login?deleted=true");
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to purge account data." });
      setDeleting(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-foreground py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Navigation / Header */}
        <div className="flex items-center justify-between border-b border-border/80 pb-5">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/")}
              className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-2">
                <span>Privacy & DPDP Governance Portal</span>
                <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                  DPDP Act 2023 Compliant
                </span>
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                Manage your statutory data rights, download machine-readable archives, and control memory erasure.
              </p>
            </div>
          </div>
        </div>

        {/* Feedback alert banner */}
        {message && (
          <div
            className={`p-3.5 rounded-xl border text-xs flex items-center gap-2.5 ${
              message.type === "success"
                ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20"
                : "bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/20"
            }`}
          >
            {message.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-500" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-500" />
            )}
            <span>{message.text}</span>
          </div>
        )}

        {/* Section 1: Statutory DPDP Disclosures */}
        <div className="bg-card border border-border rounded-2xl p-6 shadow-2xs space-y-4">
          <div className="flex items-center gap-2.5 text-foreground font-medium text-sm">
            <Shield className="w-4 h-4 text-emerald-500" />
            <h2>Statutory Privacy Notice (DPDP Act 2023 Sec 5 & 6)</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-muted-foreground">
            <div className="p-3 rounded-xl bg-muted/40 border border-border/50">
              <span className="font-semibold text-foreground block mb-1">1. Purpose of Processing</span>
              Operating sovereign AI coworkers, executing authorized tool calls, and formatting business documents.
            </div>
            <div className="p-3 rounded-xl bg-muted/40 border border-border/50">
              <span className="font-semibold text-foreground block mb-1">2. Data Minimization & PII Masking</span>
              All prompts are sanitized using Presidio & Cloud DLP; raw Indian identifiers (Aadhaar, PAN) are never stored in model caches.
            </div>
            <div className="p-3 rounded-xl bg-muted/40 border border-border/50">
              <span className="font-semibold text-foreground block mb-1">3. Storage & Sovereign Boundary</span>
              Conversations and vectors reside in Supabase (Mumbai `ap-south-1`) with hardware encryption via `pgsodium`.
            </div>
            <div className="p-3 rounded-xl bg-muted/40 border border-border/50">
              <span className="font-semibold text-foreground block mb-1">4. Grievance Redressal</span>
              Workkbot Data Protection Officer: <span className="text-foreground">dpo@workkbot.in</span> (statutory response in 72 hours).
            </div>
          </div>
        </div>

        {/* Section 2: Data Portability (DPDP Section 12) */}
        <div className="bg-card border border-border rounded-2xl p-6 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h2 className="text-sm font-medium text-foreground flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-500" />
                <span>Right to Access & Data Portability (Section 12)</span>
              </h2>
              <p className="text-xs text-muted-foreground">
                Download a clean, structured JSON archive containing your full conversation histories, consent audit log, and connected third-party tools.
              </p>
            </div>
            <button
              onClick={handleExportData}
              disabled={exporting}
              className="px-4 py-2 rounded-xl bg-zinc-900 text-white dark:bg-white dark:text-zinc-950 text-xs font-medium hover:opacity-90 transition-opacity flex items-center gap-2 shrink-0 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{exporting ? "Generating Archive..." : "Download My Data (JSON)"}</span>
            </button>
          </div>
        </div>

        {/* Section 3: Right to Erasure & Account Purge (Apple 5.1.1 & DPDP Section 13) */}
        <div className="bg-red-500/5 dark:bg-red-950/20 border border-red-500/20 rounded-2xl p-6 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h2 className="text-sm font-medium text-red-600 dark:text-red-400 flex items-center gap-2">
                <Trash2 className="w-4 h-4" />
                <span>Right to Erasure & Account Deletion (Apple Guideline 5.1.1)</span>
              </h2>
              <p className="text-xs text-muted-foreground max-w-xl">
                Permanently purge your account, conversations, episodic ADK sessions, vector memories, and hardware-encrypted Supabase Vault tokens in a single atomic transaction.
              </p>
            </div>
            <button
              onClick={() => setShowDeleteModal(true)}
              className="px-4 py-2 rounded-xl bg-red-600 text-white text-xs font-medium hover:bg-red-700 transition-colors shrink-0 shadow-xs"
            >
              Delete Account & Purge Data
            </button>
          </div>
        </div>
      </div>

      {/* Double confirmation modal for Account Deletion */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
              <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-foreground">Confirm Irreversible Deletion</h3>
                <p className="text-xs text-muted-foreground">This action cannot be undone.</p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Your profile, all conversation histories, ADK event trees, semantic vector memories, and third-party Vault secrets will be immediately and irrevocably hard-deleted from our databases.
            </p>

            <div className="space-y-2">
              <label className="text-[11px] font-medium text-foreground block">
                Type <span className="font-bold text-red-600">DELETE</span> to confirm:
              </label>
              <input
                type="text"
                value={deleteConfirmationText}
                onChange={(e) => setDeleteConfirmationText(e.target.value)}
                placeholder="DELETE"
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-hidden focus:ring-2 focus:ring-red-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteConfirmationText("");
                }}
                disabled={deleting}
                className="px-3.5 py-1.5 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-accent transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleteConfirmationText !== "DELETE" || deleting}
                className="px-4 py-1.5 rounded-lg bg-red-600 text-white text-xs font-medium hover:bg-red-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-xs"
              >
                {deleting ? "Purging All Records..." : "Permanently Delete Everything"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
