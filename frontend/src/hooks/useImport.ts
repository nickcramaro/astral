/** PDF import progress tracking. */

import { useCallback, useState } from "react";
import type { ImportProgress } from "../types";

export function useImport() {
  const [progress, setProgress] = useState<ImportProgress | null>(null);
  const [importing, setImporting] = useState(false);

  const startImport = useCallback(async (file: File) => {
    setImporting(true);
    setProgress({ stage: "Uploading..." });

    const formData = new FormData();
    formData.append("file", file);

    // TODO: POST to /campaigns/import, then connect to progress WebSocket
    const res = await fetch("http://localhost:8000/campaigns/import", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    // TODO: Connect to /ws/campaigns/{id}/progress for live updates
    setProgress({ stage: "Processing...", detail: data.filename });
    setImporting(false);
  }, []);

  return { progress, importing, startImport };
}
