import { ShieldCheck, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import { ClassSelectionGrid } from "../../components/ui/ClassSelectionGrid";
import { Collapsible } from "../../components/ui/Collapsible";
import { Field } from "../../components/ui/Field";
import { JsonBlock } from "../../components/ui/JsonBlock";
import { NumericInput } from "../../components/ui/NumericInput";
import { Panel } from "../../components/ui/Panel";
import {
  ApiResult,
  RedactionConfigResponse,
  getRuntimePolicy,
  resetRuntimePolicy,
  safeRequest,
  updateRuntimePolicy,
} from "../../lib/api";
import { DEFAULT_CLASS_CONFIDENCE, PRIVACY_CLASSES } from "../../lib/constants";
import {
  getDisabledPrivacyClasses,
  normalizeClassConfidence,
  normalizePrivacyClasses,
  withDerivedPolicyClasses,
} from "../../lib/policy";

export function DynamicInjectionView({
  redactionConfig,
  onRefresh,
}: {
  redactionConfig: RedactionConfigResponse | null;
  onRefresh: () => Promise<void>;
}) {
  const [policy, setPolicy] = useState<Record<string, unknown>>({
    policy_name: "Default Government Policy",
    confidence_threshold: 0.35,
    class_confidence_threshold: { ...DEFAULT_CLASS_CONFIDENCE },
    profile: "government",
    redaction_mode: "black_box",
    active_classes: ["KTP", "KK", "SIM", "Paspor", "Teks_Sensitif", "Wajah", "Plat_Nomor", "Resi"],
    disabled_classes: [],
    label_text: "REDACTED",
    injection_note: "Frontend contract draft",
  });
  const [result, setResult] = useState<ApiResult<Record<string, unknown>> | null>(null);

  const availableClasses = PRIVACY_CLASSES;
  const activeClassesList = normalizePrivacyClasses(policy.active_classes);
  const disabledClassesList = getDisabledPrivacyClasses(activeClassesList);
  const classConfidence = normalizeClassConfidence(policy.class_confidence_threshold);

  function updateClassConfidence(className: string, value: number) {
    setPolicy((current) => ({
      ...current,
      class_confidence_threshold: {
        ...normalizeClassConfidence(current.class_confidence_threshold),
        [className]: value,
      },
    }));
  }

  function updateField(key: string, value: unknown) {
    setPolicy((current) => ({ ...current, [key]: value }));
  }

  async function loadPolicy() {
    const response = await safeRequest(getRuntimePolicy);
    setResult(response);
    if (response.ok && response.data?.policy && typeof response.data.policy === "object") {
      setPolicy(withDerivedPolicyClasses(response.data.policy));
    }
  }

  async function savePolicy() {
    const payload = withDerivedPolicyClasses(policy);
    const response = await safeRequest(() => updateRuntimePolicy(payload));
    setResult(response);
    if (response.ok && response.data?.policy && typeof response.data.policy === "object") {
      setPolicy(withDerivedPolicyClasses(response.data.policy));
    }
    await onRefresh();
  }

  async function resetPolicy() {
    const response = await safeRequest(resetRuntimePolicy);
    setResult(response);
    if (response.ok && response.data?.policy && typeof response.data.policy === "object") {
      setPolicy(withDerivedPolicyClasses(response.data.policy));
    }
    await onRefresh();
  }

  return (
    <div className="view-stack">
      <Panel title="Editor Policy" eyebrow="Dynamic Injection" icon={<SlidersHorizontal />}>
        <div className="alert-card warning">
          <ShieldCheck size={24} color="var(--warning)" />
          <div>
            <strong>Validasi Keamanan</strong>
            <p>
              Dynamic Injection di Spectre adalah konfigurasi runtime tervalidasi, bukan eksekusi kode (No eval). Seluruh
              struktur JSON divalidasi oleh backend sebelum diterapkan.
            </p>
          </div>
        </div>

        <div className="form-stack">
          <div className="form-grid">
            <Field label="Nama Policy">
              <input
                value={String(policy.policy_name ?? "")}
                onChange={(e) => updateField("policy_name", e.target.value)}
              />
            </Field>
            <Field label="Target Profile">
              <select
                value={String(policy.profile ?? "government")}
                onChange={(e) => updateField("profile", e.target.value)}
              >
                {Object.keys(redactionConfig?.profiles ?? { government: null, live_webcam: null }).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="Confidence Threshold">
              <NumericInput
                min={0.01}
                max={0.99}
                step={0.01}
                value={Number(policy.confidence_threshold ?? 0.35)}
                fallbackValue={0.35}
                onValueChange={(value) => updateField("confidence_threshold", value)}
              />
            </Field>
            <Field label="Mode Redaksi">
              <select
                value={String(policy.redaction_mode ?? "black_box")}
                onChange={(e) => updateField("redaction_mode", e.target.value)}
              >
                {(redactionConfig?.allowed_modes ?? ["black_box", "blur", "pixelate"]).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
          </div>

          <Field label="Target Kelas Aktif">
            <ClassSelectionGrid
              options={availableClasses}
              selected={activeClassesList}
              onChange={(newSelected) => {
                setPolicy((current) => ({
                  ...current,
                  active_classes: newSelected,
                  disabled_classes: getDisabledPrivacyClasses(newSelected),
                }));
              }}
            />
          </Field>

          <Field label="Confidence Threshold per Kelas">
            <div className="form-grid">
              {activeClassesList.length === 0 ? (
                <div className="empty-state" style={{ gridColumn: "1 / -1" }}>Tidak ada kelas yang diaktifkan.</div>
              ) : (
                activeClassesList.map((className) => (
                  <div key={className} className="animated-threshold-item">
                    <Field label={className}>
                      <NumericInput
                        min={0.01}
                        max={0.99}
                        step={0.01}
                        value={classConfidence[className]}
                        fallbackValue={DEFAULT_CLASS_CONFIDENCE[className]}
                        onValueChange={(value) => updateClassConfidence(className, value)}
                      />
                    </Field>
                  </div>
                ))
              )}
            </div>
            <small className="field-hint">
              Threshold deteksi per kelas, dikalibrasi dari kurva F1/PR. Kelas tanpa nilai pakai Confidence Threshold
              global sebagai fallback.
            </small>
          </Field>

          <Field label="Injection Note">
            <input
              value={String(policy.injection_note ?? "")}
              onChange={(e) => updateField("injection_note", e.target.value)}
            />
          </Field>

          <div className="button-row">
            <button type="button" className="primary-button" onClick={savePolicy}>
              Simpan Policy
            </button>
            <button type="button" className="primary-button secondary-button" onClick={loadPolicy}>
              Muat Policy
            </button>
            <button type="button" className="primary-button secondary-button" onClick={resetPolicy}>
              Reset Default
            </button>
          </div>
        </div>

        {result && (
          <div className={`result-box ${result.ok ? "success-box" : "error-box"}`}>
            {result.ok ? "Operasi policy berhasil." : result.error?.message}
          </div>
        )}

        <Collapsible title="Detail Policy JSON">
          <JsonBlock data={policy} />
        </Collapsible>
      </Panel>
    </div>
  );
}
