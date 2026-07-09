import { useCallback, useMemo, useRef, useState } from "react";
import {
  clearSection,
  fingerprint,
  loadSection,
  saveSection,
  type CockpitSectionId,
} from "@/lib/cockpitPersist";

export type CockpitDraftApi<T extends object> = {
  draft: T;
  setDraft: React.Dispatch<React.SetStateAction<T>>;
  update: (patch: Partial<T>) => void;
  dirty: boolean;
  lastSavedAt: string | null;
  save: () => void;
  discard: () => void;
  resetDefaults: () => void;
};

function stripSavedAt<T extends object>(data: T & { savedAt?: string }): T {
  const { savedAt: _s, ...rest } = data as T & { savedAt?: string };
  return rest as T;
}

/**
 * Draft/saved pattern for cockpit UI prefs.
 * Mount loads last saved (or defaults). Edits dirty the draft until Save.
 */
export function useCockpitDraft<T extends object>(
  sectionId: CockpitSectionId,
  defaults: T,
): CockpitDraftApi<T> {
  const defaultsRef = useRef(defaults);
  defaultsRef.current = defaults;

  const [draft, setDraft] = useState<T>(() => {
    const saved = loadSection<T & { savedAt?: string }>(sectionId);
    if (!saved) return defaults;
    return { ...defaults, ...stripSavedAt(saved) };
  });

  const [savedFingerprint, setSavedFingerprint] = useState(() => {
    const saved = loadSection<T & { savedAt?: string }>(sectionId);
    if (!saved) return fingerprint(defaults);
    return fingerprint(stripSavedAt(saved));
  });

  const [lastSavedAt, setLastSavedAt] = useState<string | null>(() => {
    const saved = loadSection<{ savedAt?: string }>(sectionId);
    return typeof saved?.savedAt === "string" ? saved.savedAt : null;
  });

  const dirty = useMemo(
    () => fingerprint(draft) !== savedFingerprint,
    [draft, savedFingerprint],
  );

  const update = useCallback((patch: Partial<T>) => {
    setDraft((d) => ({ ...d, ...patch }));
  }, []);

  const save = useCallback(() => {
    const savedAt = saveSection(sectionId, draft);
    setSavedFingerprint(fingerprint(draft));
    setLastSavedAt(savedAt);
  }, [draft, sectionId]);

  const discard = useCallback(() => {
    const base = defaultsRef.current;
    const saved = loadSection<T & { savedAt?: string }>(sectionId);
    if (!saved) {
      setDraft(base);
      return;
    }
    setDraft({ ...base, ...stripSavedAt(saved) });
  }, [sectionId]);

  const resetDefaults = useCallback(() => {
    const base = defaultsRef.current;
    clearSection(sectionId);
    setDraft(base);
    setSavedFingerprint(fingerprint(base));
    setLastSavedAt(null);
  }, [sectionId]);

  return {
    draft,
    setDraft,
    update,
    dirty,
    lastSavedAt,
    save,
    discard,
    resetDefaults,
  };
}
