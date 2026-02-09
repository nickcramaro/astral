/** PDF import wizard — drag-and-drop + progress. */

import { useCallback } from "react";
import type { ImportProgress } from "../types";

interface Props {
  progress: ImportProgress | null;
  importing: boolean;
  onFileSelect: (file: File) => void;
  onBack: () => void;
}

export function ImportWizard({ progress, importing, onFileSelect, onBack }: Props) {
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file?.type === "application/pdf") {
        onFileSelect(file);
      }
    },
    [onFileSelect],
  );

  return (
    <div className="import-wizard">
      <button className="back-btn" onClick={onBack}>
        Back
      </button>

      {!importing && !progress ? (
        <div
          className="drop-zone"
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
        >
          <p>Drop a PDF here</p>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => e.target.files?.[0] && onFileSelect(e.target.files[0])}
          />
        </div>
      ) : (
        <div className="progress">
          <p>{progress?.stage}</p>
          {progress?.detail && <p className="detail">{progress.detail}</p>}
        </div>
      )}
    </div>
  );
}
