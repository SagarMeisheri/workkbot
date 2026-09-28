"use client";

import React, { useState } from "react";
import { Shield, Check, Lock, Globe, FileText, ArrowRight } from "lucide-react";
import { BACKEND_URL } from "@/lib/config";

interface ConsentModalProps {
  isOpen: boolean;
  onConsentSuccess: () => void;
  user: any;
}

export function ConsentModal({ isOpen, onConsentSuccess, user }: ConsentModalProps) {
  const [language, setLanguage] = useState<"en" | "hi">("en");
  const [submitting, setSubmitting] = useState(false);
  const [acceptedItems, setAcceptedItems] = useState<number[]>([0, 1, 2, 3]);

  if (!isOpen) return null;

  const disclosuresEn = [
    "Conversations and tool calls will be processed by AI models to assist with your daily workflows.",
    "Connected workspace tools (Google, Zoho, ERPs) will be queried based on your explicit instructions.",
    "Derived facts and work preferences will be stored in semantic memory to personalize responses.",
    "You retain the statutory Right to Access, Correct, and Erase your personal data at any time.",
  ];

  const disclosuresHi = [
    "आपकी बातचीत और टूल कॉल्स को दैनिक कार्यप्रवाह में सहायता के लिए AI मॉडल द्वारा प्रोसेस किया जाएगा।",
    "आपके कार्यक्षेत्र के कनेक्टेड टूल्स (गूगल, ज़ोहो, ERP) को आपके स्पष्ट निर्देशानुसार एक्सेस किया जाएगा।",
    "व्यक्तिगत अनुभव के लिए महत्वपूर्ण तथ्य और प्राथमिकताएं मेमोरी में सुरक्षित रखी जाएंगी।",
    "आपको किसी भी समय अपने व्यक्तिगत डेटा को देखने, सुधारने और पूरी तरह मिटाने का कानूनी अधिकार प्राप्त है।",
  ];

  const items = language === "en" ? disclosuresEn : disclosuresHi;

  const handleToggleItem = (index: number) => {
    if (acceptedItems.includes(index)) {
      setAcceptedItems(acceptedItems.filter((i) => i !== index));
    } else {
      setAcceptedItems([...acceptedItems, index]);
    }
  };

  const handleAccept = async () => {
    setSubmitting(true);
    try {
      const token = user?.access_token || localStorage.getItem("workkbot_token");
      await fetch(`${BACKEND_URL}/api/v1/consent`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          consent_version: "2026.1",
          language,
          accepted_disclosures: items,
        }),
      });
    } catch (e) {
      console.warn("Backend consent API offline, saving consent locally:", e);
    } finally {
      localStorage.setItem("workkbot_consented", "true");
      setSubmitting(false);
      onConsentSuccess();
    }
  };

  const allAccepted = acceptedItems.length === 4;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-lg bg-card border border-border rounded-2xl shadow-2xl p-6 sm:p-8 flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-500 flex items-center justify-center border border-amber-500/20">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">
                {language === "en" ? "DPDP Act 2023 Statutory Consent" : "DPDP अधिनियम 2023 वैधानिक सहमति"}
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {language === "en" ? "Mandatory AI and data processing disclosure" : "अनिवार्य AI और डेटा प्रोसेसिंग प्रकटीकरण"}
              </p>
            </div>
          </div>

          {/* Bilingual Toggle */}
          <div className="flex items-center p-0.5 rounded-lg bg-muted text-xs">
            <button
              onClick={() => setLanguage("en")}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                language === "en" ? "bg-background font-semibold text-foreground shadow-2xs" : "text-muted-foreground"
              }`}
            >
              EN
            </button>
            <button
              onClick={() => setLanguage("hi")}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                language === "hi" ? "bg-background font-semibold text-foreground shadow-2xs" : "text-muted-foreground"
              }`}
            >
              हिंदी
            </button>
          </div>
        </div>

        {/* Itemized Disclosures */}
        <div className="flex flex-col gap-3">
          {items.map((disclosure, idx) => {
            const isChecked = acceptedItems.includes(idx);
            return (
              <div
                key={idx}
                onClick={() => handleToggleItem(idx)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex items-start gap-3 text-xs leading-relaxed ${
                  isChecked
                    ? "bg-amber-50/50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/60 text-foreground"
                    : "bg-muted/40 border-border text-muted-foreground"
                }`}
              >
                <div
                  className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center shrink-0 border transition-colors ${
                    isChecked
                      ? "bg-amber-600 border-amber-600 text-white"
                      : "border-muted-foreground/40 bg-background"
                  }`}
                >
                  {isChecked && <Check className="w-3 h-3 stroke-[3]" />}
                </div>
                <span>{disclosure}</span>
              </div>
            );
          })}
        </div>

        {/* Rights Notice */}
        <div className="flex items-center gap-2 p-3 rounded-xl bg-muted/30 border border-border/80 text-[11px] text-muted-foreground">
          <Lock className="w-3.5 h-3.5 text-amber-600 shrink-0" />
          <span>
            {language === "en"
              ? "All data is localized in Mumbai (asia-south1) and encrypted in Supabase Vault."
              : "समस्त डेटा मुंबई (asia-south1) में स्थानीयकृत और Supabase Vault में एन्क्रिप्टेड है।"}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between gap-3 pt-2">
          <span className="text-[11px] text-muted-foreground">
            {language === "en" ? "Apple Guideline 5.1.2(i) Compliant" : "एप्पल दिशानिर्देश 5.1.2(i) अनुपालक"}
          </span>
          <button
            onClick={handleAccept}
            disabled={!allAccepted || submitting}
            className="h-10 px-5 rounded-xl bg-primary text-primary-foreground text-xs font-medium flex items-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            <span>{language === "en" ? "Accept & Continue" : "स्वीकार करें और आगे बढ़ें"}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
