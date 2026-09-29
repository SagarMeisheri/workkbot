"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn, User, Settings, Shield, Trash2, LogOut, ChevronUp } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { BACKEND_URL } from "@/lib/config";

interface SidebarAuthFooterProps {
  user: {
    id: string;
    email: string;
    first_name: string;
    org_id: string;
    role: string;
    is_demo?: boolean;
    access_token?: string;
  } | null;
  onOpenConnectors: () => void;
  onOpenConsentModal: () => void;
}

export function SidebarAuthFooter({
  user,
  onOpenConnectors,
  onOpenConsentModal,
}: SidebarAuthFooterProps) {
  const router = useRouter();
  const [showMenu, setShowMenu] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleSignOut = async () => {
    try {
      await supabase.auth.signOut();
    } catch (e) {
      // Ignored if offline
    }
    localStorage.removeItem("workkbot_auth");
    localStorage.removeItem("workkbot_token");
    window.location.reload();
  };

  const handleDeleteAccount = async () => {
    if (!user) return;
    setDeleting(true);
    try {
      const token = user?.access_token || localStorage.getItem("workkbot_token");
      await fetch(`${BACKEND_URL}/api/v1/account/delete`, {
        method: "DELETE",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    } catch (e) {
      console.error("Account deletion API error:", e);
    } finally {
      setDeleting(false);
      handleSignOut();
    }
  };

  if (!user) {
    return (
      <div className="p-3 border-t border-sidebar-border">
        <button
          onClick={() => router.push("/login")}
          className="w-full h-9 px-3 rounded-lg border border-border bg-white dark:bg-zinc-900 hover:bg-accent text-foreground text-xs font-medium flex items-center justify-between transition-colors shadow-2xs"
        >
          <span className="flex items-center gap-2">
            <LogIn className="w-3.5 h-3.5 text-muted-foreground" />
            <span>Sign in</span>
          </span>
          <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">Google SSO</span>
        </button>
      </div>
    );
  }

  const initials = (user.first_name || user.email || "U").slice(0, 2).toUpperCase();

  return (
    <div className="relative p-3 border-t border-sidebar-border">
      {/* Dropdown Popover */}
      {showMenu && (
        <div className="absolute bottom-full left-3 right-3 mb-2 bg-popover border border-border rounded-xl shadow-xl p-1.5 flex flex-col gap-0.5 text-xs text-foreground z-50 animate-in fade-in slide-in-from-bottom-2 duration-150">
          <div className="px-2.5 py-2 border-b border-border/60">
            <p className="font-medium text-foreground truncate">{user.email}</p>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{user.role}</p>
          </div>

          <button
            onClick={() => {
              setShowMenu(false);
              onOpenConnectors();
            }}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-accent text-left transition-colors"
          >
            <Settings className="w-3.5 h-3.5 text-muted-foreground" />
            <span>Connected Tools</span>
          </button>

          <button
            onClick={() => {
              setShowMenu(false);
              router.push("/settings/privacy");
            }}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-accent text-left transition-colors"
          >
            <Shield className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span>DPDP Privacy & Erasure</span>
          </button>

          <button
            onClick={() => {
              setShowMenu(false);
              onOpenConsentModal();
            }}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-accent text-left transition-colors"
          >
            <Shield className="w-3.5 h-3.5 text-amber-600 dark:text-amber-500" />
            <span>Statutory Disclosures</span>
          </button>

          <div className="my-1 border-t border-border" />

          {confirmDelete ? (
            <div className="p-2 bg-red-50 dark:bg-red-950/40 rounded-lg flex flex-col gap-1.5 border border-red-200 dark:border-red-900">
              <p className="text-[11px] font-semibold text-red-700 dark:text-red-400">
                Purge all account data & Vault tokens?
              </p>
              <div className="flex items-center gap-2">
                <button
                  disabled={deleting}
                  onClick={handleDeleteAccount}
                  className="flex-1 h-7 rounded bg-red-600 text-white font-medium text-[11px] hover:bg-red-700 transition-colors"
                >
                  {deleting ? "Purging..." : "Confirm Purge"}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="h-7 px-2 rounded bg-muted hover:bg-muted/80 text-[11px]"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/40 text-red-600 dark:text-red-400 text-left transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5 text-red-600" />
              <span>Delete Account & Purge Memory</span>
            </button>
          )}

          <button
            onClick={handleSignOut}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-accent text-left transition-colors text-muted-foreground hover:text-foreground"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign out</span>
          </button>
        </div>
      )}

      {/* Main Profile Trigger */}
      <button
        onClick={() => {
          setShowMenu(!showMenu);
          setConfirmDelete(false);
        }}
        className="w-full h-11 px-2.5 rounded-xl hover:bg-accent flex items-center justify-between transition-colors text-left group"
      >
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-7 h-7 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-900 dark:text-amber-200 flex items-center justify-center font-medium text-xs border border-amber-300 dark:border-amber-800 shrink-0">
            {initials}
          </div>
          <div className="flex flex-col overflow-hidden">
            <span className="text-xs font-medium text-foreground truncate group-hover:text-primary">
              {user.first_name || user.email.split("@")[0]}
            </span>
            <span className="text-[10px] text-muted-foreground truncate">
              {user.is_demo ? "Reviewer Sandbox" : "Workkbot SMB"}
            </span>
          </div>
        </div>
        <ChevronUp className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
      </button>
    </div>
  );
}
