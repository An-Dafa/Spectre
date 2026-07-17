// Runtime-policy + privacy-class helpers.
import { DEFAULT_CLASS_CONFIDENCE, PRIVACY_CLASSES } from "./constants";

export function normalizePrivacyClasses(value: unknown, fallback: string[] = PRIVACY_CLASSES): string[] {
  const rawItems = Array.isArray(value)
    ? value.map(String)
    : typeof value === "string"
      ? value.split(",").map((item) => item.trim()).filter(Boolean)
      : fallback;
  return PRIVACY_CLASSES.filter((className) => rawItems.includes(className));
}

export function getDisabledPrivacyClasses(activeClasses: string[]): string[] {
  return PRIVACY_CLASSES.filter((className) => !activeClasses.includes(className));
}

export function normalizeClassConfidence(value: unknown): Record<string, number> {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const result: Record<string, number> = {};
  for (const className of PRIVACY_CLASSES) {
    const candidate = Number(raw[className]);
    result[className] = Number.isFinite(candidate) ? candidate : DEFAULT_CLASS_CONFIDENCE[className];
  }
  return result;
}

export function withDerivedPolicyClasses(policy: Record<string, unknown>): Record<string, unknown> {
  const activeClasses = normalizePrivacyClasses(policy.active_classes);
  return {
    ...policy,
    active_classes: activeClasses,
    disabled_classes: getDisabledPrivacyClasses(activeClasses),
  };
}
