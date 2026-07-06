import React, { useRef } from "react";
import api, { formatApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { toast } from "sonner";
import { ImagePlus, X } from "lucide-react";
import ConfirmDialog from "@/components/ui/ConfirmDialog";

export default function PhotosPanel({ est, update }) {
  const fileRef = useRef();
  const t = useT();

  const uploadPhoto = async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/uploads", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      update({ photos: [...(est.photos || []), data.url] });
      toast.success(t("est.photoAdded"));
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    }
  };

  return (
    <section className="card p-5 mb-6" data-testid="photos-panel">
      <div className="flex items-center justify-between mb-3">
        <div className="section-tag">{t("est.jobPhotos")}</div>
        <button className="btn-secondary" onClick={() => fileRef.current?.click()} data-testid="add-photo-btn">
          <ImagePlus className="w-4 h-4" /> {t("est.addPhoto")}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => e.target.files?.[0] && uploadPhoto(e.target.files[0])}
        />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        {(est.photos || []).length === 0 && (
          <div className="col-span-full text-sm text-[var(--muted)] py-4">{t("est.noPhotos")}</div>
        )}
        {(est.photos || []).map((p) => {
          const i = est.photos.indexOf(p);
          return (
          <div key={`${p}-${i}`} className="relative aspect-square bg-[var(--surface-muted)] border border-[var(--border)]">
            <img
              src={`${process.env.REACT_APP_BACKEND_URL}${p}`}
              alt=""
              className="w-full h-full object-cover"
            />
            <ConfirmDialog
              trigger={
                <button
                  className="absolute top-1 right-1 bg-[var(--surface)] border border-[var(--border-strong)] p-1"
                  aria-label={t("confirm.removePhoto.title")}
                >
                  <X className="w-3 h-3" />
                </button>
              }
              title={t("confirm.removePhoto.title")}
              description={t("confirm.removePhoto.desc")}
              confirmLabel={t("common.remove")}
              cancelLabel={t("common.cancel")}
              destructive
              onConfirm={() => update({ photos: est.photos.filter((_, j) => j !== i) })}
            />
          </div>
          );
        })}
      </div>
    </section>
  );
}
